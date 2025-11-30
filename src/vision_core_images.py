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

HAAR_FILENAME = 'haarcascade_russian_plate_number.xml'

# LOCALIZAÇÃO DA PASTA RAIZ DO PROJETO
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

IMAGES_DIR = os.path.join(BASE_DIR, 'data', 'inputs', 'images')

XML_PATH = os.path.join(BASE_DIR, HAAR_FILENAME)

def baixar_cascade_silencioso():
    """Baixa o arquivo Haar Cascade se não existir."""
    if not os.path.exists(XML_PATH):
        try:
            url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_russian_plate_number.xml"
            urllib.request.urlretrieve(url, XML_PATH)
        except:
            pass

def limpar_texto(texto):
    return re.sub(r'[^a-zA-Z0-9]', '', texto).upper()

def validar_padrao_placa(texto):
    texto = limpar_texto(texto)
    return 6 <= len(texto) <= 8

def preprocessamento_rapido(img_crop):
    """Aumenta contraste da imagem recortada da placa."""
    if len(img_crop.shape) == 3:
        gray = cv2.cvtColor(img_crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = img_crop

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contraste = clahe.apply(gray)
    return contraste

# IMPRESSÃO DE TABELA
def imprimir_cabecalho_tabela():
    print("\n" + "=" * 105)
    print(f"{'STATUS':<15} | {'PLACA':<10} | {'DATA':<12} | {'HORA':<10} | {'IMAGEM'}")
    print("=" * 105)


def imprimir_linha_tabela(status, placa, data, hora, arquivo):
    cor_status = "✅" if status == "DETECTADA" else "⚠️"
    print(f"{cor_status} {status:<12} | {placa:<10} | {data:<12} | {hora:<10} | {arquivo}")


# PROCESSAMENTO DE IMAGENS
def processar_todas_imagens():
    print(f"--- SISTEMA DE DETECÇÃO: PROCESSAMENTO DE IMAGENS (EM LOTE) ---")

    baixar_cascade_silencioso()

    if not os.path.exists(IMAGES_DIR):
        print(f"❌ ERRO: Pasta não encontrada: {IMAGES_DIR}")
        return

    # LISTA AS IMAGENS DA PASTA
    imagens = [
        f for f in os.listdir(IMAGES_DIR)
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff'))
    ]

    if not imagens:
        print("Nenhuma imagem encontrada.")
        return

    # INICIA MODELOS
    yolo_model = YOLO('yolov8n.pt')
    reader = easyocr.Reader(['pt', 'en'], gpu=False, verbose=False)

    plate_cascade = cv2.CascadeClassifier(XML_PATH)

    imprimir_cabecalho_tabela()

    for nome_img in imagens:
        caminho_img = os.path.join(IMAGES_DIR, nome_img)

        frame = cv2.imread(caminho_img)
        if frame is None:
            imprimir_linha_tabela("ERRO", "---", "---", "---", nome_img)
            continue

        leituras = []

        # REDUZ IMAGEM PARA ENTRAR NO YOLO
        h_orig, w_orig = frame.shape[:2]
        escala = 640 / max(h_orig, w_orig)
        frame_input = cv2.resize(frame, None, fx=escala, fy=escala) if escala < 1 else frame

        # DETECTA VEÍCULOS
        resultados = yolo_model(frame_input, verbose=False)

        for r in resultados:
            for box in r.boxes:
                if int(box.cls[0]) in [2, 3, 5, 7] and box.conf[0] > 0.40:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    if escala < 1:
                        x1, x2 = int(x1 / escala), int(x2 / escala)
                        y1, y2 = int(y1 / escala), int(y2 / escala)

                    veiculo_crop = frame[y1:y2, x1:x2]
                    if veiculo_crop.size == 0:
                        continue

                    veiculo_gray = cv2.cvtColor(veiculo_crop, cv2.COLOR_BGR2GRAY)
                    plates = plate_cascade.detectMultiScale(veiculo_gray, 1.1, 4)

                    # ROI DA PLACA
                    if len(plates) > 0:
                        px, py, pw, ph = max(plates, key=lambda b: b[2] * b[3])
                        mx, my = int(pw * 0.1), int(ph * 0.1)
                        roi = veiculo_crop[max(0, py-my):py+ph+my, max(0, px-mx):px+pw+mx]
                    else:
                        # FALLBACK
                        h, w = veiculo_crop.shape[:2]
                        roi = veiculo_crop[int(h*0.60):, int(w*0.15):int(w*0.85)]

                    if roi is None or roi.size == 0:
                        continue

                    img_proc = preprocessamento_rapido(roi)

                    try:
                        textos = reader.readtext(
                            img_proc,
                            detail=0,
                            allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                        )
                        for txt in textos:
                            limpo = limpar_texto(txt)
                            if validar_padrao_placa(limpo):
                                leituras.append(limpo)
                    except:
                        pass

        # VOTAÇÃO FINAL
        if leituras:
            placa_final, freq = Counter(leituras).most_common(1)[0]
            agora = datetime.now()

            imprimir_linha_tabela(
                status="DETECTADA",
                placa=placa_final,
                data=agora.strftime("%d/%m/%Y"),
                hora=agora.strftime("%H:%M:%S"),
                arquivo=nome_img
            )

            registrar_leitura(placa_final, agora, "---", nome_img)

        else:
            imprimir_linha_tabela("NÃO ENC.", "---", "---", "---", nome_img)

    print("=" * 105)
    print("🏁 PROCESSAMENTO DE IMAGENS FINALIZADO.")

# EXECUÇÃO DIRETA
if __name__ == "__main__":
    processar_todas_imagens()
