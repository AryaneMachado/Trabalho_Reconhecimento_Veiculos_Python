import cv2
import numpy as np
from ultralytics import YOLO
import easyocr
import re
import os
import urllib.request
from datetime import datetime
from collections import Counter
from backend import registrar_leitura

# --- Configurações ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEOS_DIR = os.path.join(BASE_DIR, 'data', 'inputs', 'videos')

# --- CONFIGURAÇÕES DE ALTA PRECISÃO ---
# Analisa 1 a cada 2 frames (Muito mais dados para o OCR trabalhar)
PULAR_FRAMES = 2 
# Precisa de apenas 3 leituras iguais para confirmar (Registra mais rápido)
AMOSTRAS_PARA_CONFIRMAR = 3
# Tamanho original da imagem para o OCR não perder detalhes
TAMANHO_YOLO = 640 

# Dicionários de Correção (Letra <-> Número)
dict_letra_num = {
    'O': '0', 'Q': '0', 'D': '0', 'U': '0',
    'I': '1', 'J': '1', 'L': '1',
    'Z': '2',
    'A': '4',
    'S': '5', '$': '5',
    'G': '6', 'b': '6',
    'T': '7',
    'B': '8',
    'g': '9'
}
dict_num_letra = {
    '0': 'O',
    '1': 'I',
    '2': 'Z',
    '4': 'A',
    '5': 'S',
    '6': 'G',
    '7': 'T',
    '8': 'B'
}

def corrigir_padrao_brasileiro(texto_bruto):
    """
    Força bruta para transformar o texto no padrão Mercosul ou Antigo.
    """
    texto = re.sub(r'[^a-zA-Z0-9]', '', texto_bruto).upper()
    
    # Tolerância: Às vezes o OCR lê um caractere a mais ou a menos
    if len(texto) < 6 or len(texto) > 8:
        return None
    
    # Pega os primeiros 7 caracteres válidos
    chars = list(texto[:7])
    if len(chars) < 7: return None

    # REGRAS RÍGIDAS DE POSIÇÃO
    
    # 1. Três primeiras = LETRAS (ABC...)
    for i in [0, 1, 2]:
        if chars[i] in dict_num_letra: chars[i] = dict_num_letra[chars[i]]
        if not chars[i].isalpha(): return None # Impossível corrigir

    # 2. Quarta posição = NÚMERO (...1...)
    if chars[3] in dict_letra_num: chars[3] = dict_letra_num[chars[3]]
    if not chars[3].isdigit(): return None

    # 3. Quinta Posição (Define o tipo)
    # Se for letra = Mercosul. Se for número = Antiga.
    # Se for ambíguo, tentamos converter baseado no contexto ou preferência
    if chars[4] in dict_letra_num and chars[4] in dict_num_letra:
        # Caractere ambíguo (ex: 'B' ou '8'). 
        # Preferência para Letra (Mercosul) pois é o padrão atual
        chars[4] = dict_num_letra[chars[4]]

    # 4. Duas últimas = NÚMEROS (...23)
    for i in [5, 6]:
        if chars[i] in dict_letra_num: chars[i] = dict_letra_num[chars[i]]
        if not chars[i].isdigit(): return None

    return "".join(chars)

def tratamento_imagem_hd(img):
    """
    Prepara o recorte para o OCR com nitidez máxima.
    """
    # 1. Upscaling (3x) com interpolação suave
    img = cv2.resize(img, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    
    # 2. Converte para Cinza
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 3. Bilateral Filter (Remove ruído mas mantém bordas das letras)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    
    # 4. Borda Branca (Padding)
    gray = cv2.copyMakeBorder(gray, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
    
    return gray

def imprimir_cabecalho_tabela():
    print("\n" + "="*105)
    print(f"{'STATUS':<15} | {'PLACA':<10} | {'DATA':<12} | {'HORA':<10} | {'TEMPO VÍDEO':<12} | {'ARQUIVO'}")
    print("="*105)

def imprimir_linha_tabela(status, placa, data, hora, tempo_vid, arquivo):
    cor_status = "✅" if status == "DETECTADA" else "⚠️"
    print(f"{cor_status} {status:<12} | {placa:<10} | {data:<12} | {hora:<10} | {tempo_vid:<12} | {arquivo}")

def processar_todos_videos():
    print(f"--- SISTEMA DE DETECÇÃO: MÚLTIPLOS VEÍCULOS EM VÍDEO ---")
    
    if not os.path.exists(VIDEOS_DIR):
        print(f"❌ ERRO: Pasta não encontrada: {VIDEOS_DIR}")
        return

    arquivos_video = [f for f in os.listdir(VIDEOS_DIR) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]
    
    if not arquivos_video:
        print("Nenhum vídeo encontrado.")
        return

    # YOLO Detector
    yolo_model = YOLO('yolov8n.pt') 
    
    # EasyOCR configurado para precisão (quantize=False usa float32, mais lento mas mais preciso)
    reader = easyocr.Reader(['pt'], gpu=False, verbose=False, quantize=False) 

    imprimir_cabecalho_tabela()

    for nome_video in arquivos_video:
        caminho_video = os.path.join(VIDEOS_DIR, nome_video)
        cap = cv2.VideoCapture(caminho_video)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0: fps = 30

        leituras_buffer = []
        placas_registradas_neste_video = set()
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break 
            
            frame_count += 1
            
            # --- CORREÇÃO DO INÍCIO DO VÍDEO ---
            # Processa frames com mais frequência (PULAR_FRAMES = 2)
            if frame_count % PULAR_FRAMES != 0: continue

            # Prepara imagem para o YOLO
            h_orig, w_orig = frame.shape[:2]
            scale = TAMANHO_YOLO / max(h_orig, w_orig)
            if scale < 1:
                frame_input = cv2.resize(frame, None, fx=scale, fy=scale)
            else:
                frame_input = frame

            resultados = yolo_model(frame_input, verbose=False)
            
            for r in resultados:
                for box in r.boxes:
                    # Filtra apenas carros/motos/caminhões com confiança média
                    if int(box.cls[0]) in [2, 3, 5, 7] and box.conf[0] > 0.4:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        
                        # Mapeia de volta para HD (Imagem Original)
                        if scale < 1:
                            x1, x2 = int(x1/scale), int(x2/scale)
                            y1, y2 = int(y1/scale), int(y2/scale)
                        
                        # Recorte do Veículo
                        veiculo_crop = frame[max(0, y1):min(h_orig, y2), max(0, x1):min(w_orig, x2)]
                        if veiculo_crop.size == 0: continue
                        
                        h_v, w_v = veiculo_crop.shape[:2]
                        
                        # --- TÉCNICA DE VARREDURA FOCAL ---
                        # Em vez de tentar achar a placa ou ler o para-choque inteiro,
                        # vamos focar estritamente no CENTRO INFERIOR, onde 99% das placas estão.
                        
                        # Define área de interesse (ROI) - 40% inferior, centralizado
                        corte_topo = int(h_v * 0.55)
                        corte_base = int(h_v * 0.95)
                        corte_esq = int(w_v * 0.20)
                        corte_dir = int(w_v * 0.80)
                        
                        roi_foco = veiculo_crop[corte_topo:corte_base, corte_esq:corte_dir]
                        
                        if roi_foco.size > 0:
                            # Tratamento HD
                            img_ocr = tratamento_imagem_hd(roi_foco)
                            
                            try:
                                # OCR: detail=0 retorna apenas o texto
                                leituras = reader.readtext(img_ocr, detail=0, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                                
                                for texto_cru in leituras:
                                    # Tenta "consertar" o texto lido
                                    placa_limpa = corrigir_padrao_brasileiro(texto_cru)
                                    
                                    if placa_limpa:
                                        leituras_buffer.append(placa_limpa)
                            except: pass

            # --- SISTEMA DE DECISÃO RÁPIDA ---
            # Se acumulamos 3 leituras (buffer cheio)
            if len(leituras_buffer) >= AMOSTRAS_PARA_CONFIRMAR:
                contagem = Counter(leituras_buffer)
                placa_vencedora, frequencia = contagem.most_common(1)[0]
                
                # Se a placa apareceu na maioria das vezes
                if frequencia >= 2: # Reduzi para 2/3 para ser mais ágil no início do vídeo
                    
                    if placa_vencedora not in placas_registradas_neste_video:
                        agora = datetime.now()
                        segundos_totais = int(frame_count / fps)
                        tempo_video = f"{segundos_totais//60:02d}:{segundos_totais%60:02d}"
                        
                        imprimir_linha_tabela(
                            status="DETECTADA",
                            placa=placa_vencedora,
                            data=agora.strftime("%d/%m/%Y"),
                            hora=agora.strftime("%H:%M:%S"),
                            tempo_vid=tempo_video,
                            arquivo=nome_video
                        )
                        
                        registrar_leitura(placa_vencedora, agora, tempo_video, nome_video)
                        placas_registradas_neste_video.add(placa_vencedora)
                    
                    # Limpa buffer para pegar o próximo carro
                    leituras_buffer = []
                
                # Limpa buffer se ficar muito sujo
                if len(leituras_buffer) > 10:
                    leituras_buffer = []

        cap.release()
        
        if not placas_registradas_neste_video:
             imprimir_linha_tabela("NÃO ENC.", "---", "---", "---", "---", nome_video)

    print("="*105)
    print("🏁 PROCESSAMENTO FINALIZADO.")

if __name__ == "__main__":
    processar_todos_videos()