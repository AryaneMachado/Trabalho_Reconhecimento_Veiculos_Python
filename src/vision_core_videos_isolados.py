import cv2
import numpy as np
from ultralytics import YOLO
import easyocr
import re
import os
import urllib.request
import time
from datetime import datetime
from collections import Counter
from backend import registrar_leitura

HAAR_FILENAME = 'haarcascade_russian_plate_number.xml'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEOS_DIR = os.path.join(BASE_DIR, 'data', 'inputs', 'videos')
XML_PATH = os.path.join(BASE_DIR, HAAR_FILENAME)

# CONFIGURAÇÕES DE PERFORMANCE
PULAR_FRAMES = 3           
AMOSTRAS_PARA_CONFIRMAR = 5 
TAMANHO_YOLO = 640         

def baixar_cascade_silencioso():
    if not os.path.exists(XML_PATH):
        try:
            url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_russian_plate_number.xml"
            urllib.request.urlretrieve(url, XML_PATH)
        except: pass

def limpar_texto(texto):
    return re.sub(r'[^a-zA-Z0-9]', '', texto).upper()

def validar_padrao_placa(texto):
    texto = limpar_texto(texto)
    if 6 <= len(texto) <= 8:
        return True
    return False

def preprocessamento_rapido(img_crop):
    if len(img_crop.shape) == 3:
        gray = cv2.cvtColor(img_crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = img_crop
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    contraste = clahe.apply(gray)
    return contraste

def imprimir_cabecalho_tabela():
    print("\n" + "="*105)
    print(f"{'STATUS':<15} | {'PLACA':<10} | {'DATA':<12} | {'HORA':<10} | {'TEMPO VÍDEO':<12} | {'ARQUIVO'}")
    print("="*105)

def imprimir_linha_tabela(status, placa, data, hora, tempo_vid, arquivo):

    cor_status = "✅" if status == "DETECTADA" else "⚠️"
    print(f"{cor_status} {status:<12} | {placa:<10} | {data:<12} | {hora:<10} | {tempo_vid:<12} | {arquivo}")

def processar_todos_videos():
    print(f"--- SISTEMA DE DETECÇÃO: PROCESSAMENTO SOBRE VÍDEOS AVULSOS (EM LOTE) ---")
    
    baixar_cascade_silencioso()
    original_cwd = os.getcwd()
    try:
        os.chdir(BASE_DIR)
        plate_cascade = cv2.CascadeClassifier(HAAR_FILENAME)
        os.chdir(original_cwd)
    except: return

    if not os.path.exists(VIDEOS_DIR):
        print(f"❌ ERRO: Pasta não encontrada: {VIDEOS_DIR}")
        return

    arquivos_video = [f for f in os.listdir(VIDEOS_DIR) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]
    
    if not arquivos_video:
        print("Nenhum vídeo encontrado.")
        return

    yolo_model = YOLO('yolov8n.pt') 
    reader = easyocr.Reader(['pt', 'en'], gpu=False, verbose=False) 

    # IMPRESSÃO DO CABEÇALHO DA TABELA:
    imprimir_cabecalho_tabela()

    for nome_video in arquivos_video:
        caminho_video = os.path.join(VIDEOS_DIR, nome_video)
        cap = cv2.VideoCapture(caminho_video)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0: fps = 30

        leituras_do_video = []
        frame_count = 0
        video_resolvido = False # FLAG PARA SABER SE JÁ ENCONTRAMOS A PLACA DESSE VÍDEO

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break 
            
            frame_count += 1
            if frame_count % PULAR_FRAMES != 0: continue

            # OTIMIZAÇÃO YOLO
            h_orig, w_orig = frame.shape[:2]
            scale = TAMANHO_YOLO / max(h_orig, w_orig)
            if scale < 1:
                frame_input = cv2.resize(frame, None, fx=scale, fy=scale)
            else:
                frame_input = frame

            resultados = yolo_model(frame_input, verbose=False)
            
            for r in resultados:
                for box in r.boxes:
                    if int(box.cls[0]) in [2, 3, 5, 7] and box.conf[0] > 0.4:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        
                        # MAPEIA COORDENADAS DE VOLTA PARA HD
                        if scale < 1:
                            x1, x2 = int(x1/scale), int(x2/scale)
                            y1, y2 = int(y1/scale), int(y2/scale)
                        
                        veiculo_crop = frame[y1:y2, x1:x2]
                        if veiculo_crop.size == 0: continue
                        
                        # HAAR CASCADE
                        veiculo_gray = cv2.cvtColor(veiculo_crop, cv2.COLOR_BGR2GRAY)
                        plates = plate_cascade.detectMultiScale(veiculo_gray, 1.1, 4)
                        
                        roi_placa = None
                        if len(plates) > 0:
                            px, py, pw, ph = max(plates, key=lambda b: b[2] * b[3])
                            mx, my = int(pw*0.1), int(ph*0.1) # Margem
                            roi_placa = veiculo_crop[max(0, py-my):py+ph+my, max(0, px-mx):px+pw+mx]
                        else:
                            # FALLBACK
                            h, w = veiculo_crop.shape[:2]
                            roi_placa = veiculo_crop[int(h*0.60):, int(w*0.15):int(w*0.85)]

                        if roi_placa is not None and roi_placa.size > 0:
                            img_proc = preprocessamento_rapido(roi_placa)
                            try:
                                res = reader.readtext(img_proc, detail=0, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                                for txt in res:
                                    limpo = limpar_texto(txt)
                                    if validar_padrao_placa(limpo):
                                        leituras_do_video.append(limpo)
                            except: pass

            # --- VOTAÇÃO E DECISÃO ---
            if len(leituras_do_video) >= AMOSTRAS_PARA_CONFIRMAR:
                contagem = Counter(leituras_do_video)
                placa_vencedora, frequencia = contagem.most_common(1)[0]
                
                # SE TEMOS UM VENCEDOR CLARO (3 OU MAIS)
                if frequencia >= 3:
                    agora = datetime.now()
                    
                    # CALCULA TEMPO EXATO NO VÍDEO ONDE A PLACA FOI CONFIRMADA
                    segundos_totais = int(frame_count / fps)
                    tempo_video = f"{segundos_totais//60:02d}:{segundos_totais%60:02d}"
                    
                    # IMPRIME NA TABELA
                    imprimir_linha_tabela(
                        status="DETECTADA",
                        placa=placa_vencedora,
                        data=agora.strftime("%d/%m/%Y"),
                        hora=agora.strftime("%H:%M:%S"),
                        tempo_vid=tempo_video,
                        arquivo=nome_video
                    )
                    
                    # MANDA PARA O BANCO (RAIA 2)
                    registrar_leitura(placa_vencedora, agora, tempo_video, nome_video)
                    
                    video_resolvido = True
                    break # SAI DO LOOP DESTE VÍDEO

        cap.release()
        
        # SE ACABOU O VÍDEO E NÃO CONFIRMAMOS NADA
        if not video_resolvido:
             imprimir_linha_tabela("NÃO ENC.", "---", "---", "---", "---", nome_video)

    print("="*105)
    print("🏁 PROCESSAMENTO FINALIZADO.")

# EXECUÇÃO DIRETA
if __name__ == "__main__":
    processar_todos_videos()