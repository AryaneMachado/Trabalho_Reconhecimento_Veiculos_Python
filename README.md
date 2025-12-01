# Sistema de Controle de Acesso - IFSULDEMINAS (Campus Machado)

Automação de controle de acesso por reconhecimento de placas veiculares usando Visão Computacional e IA.

> Projeto desenvolvido como trabalho da disciplina de Computação Gráfica no IFSULDEMINAS (Campus Machado).

---

## 🧾 Sumário

- [Sobre](#-sobre)
- [Funcionalidades](#-funcionalidades)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação](#-instalação)
- [Uso](#-uso)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Como Testar com Novos Vídeos](#-como-testar-com-novos-vídeos)
- [Como Funciona (Resumo Técnico)](#-como-funciona-resumo-técnico)
- [Contribuição](#-contribuição)
- [Autores](#-autores)
- [Licença](#-licença)

---

## 📋 Sobre

Este sistema utiliza o Ultralytics YOLOv8 para detectar veículos em vídeos, EasyOCR para leitura de placas e um conjunto de regras e banco SQLite para gerenciar entradas/saídas, gerando alertas, histórico e um dashboard em tempo real com Streamlit.

O objetivo é automatizar o controle de acesso de veículos para o campus, facilitando a triagem entre veículos autorizados, não autorizados e ocorrências.

---

## ✅ Funcionalidades

- Detecção automática de placas em vídeos (YOLOv8 + EasyOCR + Haar Cascade como fallback);
- Dashboard em tempo real (Streamlit) com monitoramento, histórico e gestão de veículos;
- Armazenamento de histórico em SQLite (arquivo `controle_acesso.db`);
- Auto-cadastro de visitantes não conhecidos (marca como NAO_AUTORIZADO);
- Exportação de histórico (CSV);
- Logs de console com alertas de segurança para veículos NAO_AUTORIZADO e OCORRENCIA.

---

## ⚙️ Pré-requisitos

- Python 3.9 ou superior
- Git (opcional)
- Arquivos de modelo na raiz:
  - `yolov8n.pt` (modelo YOLOv8)
  - `haarcascade_russian_plate_number.xml` (usado se disponível — o script baixa automaticamente se ausente)

Bibliotecas (listadas em `requirements.txt`): ultralytics, easyocr, opencv-python, pandas, numpy, streamlit, watchdog.

---

## 🛠️ Instalação

1) Clone o repositório (ou abra a pasta já clonada):

```powershell
git clone <REPO_URL>
cd Trabalho_Reconhecimento_Veiculos_Python
```

2) Crie e ative um ambiente virtual (Windows):

```powershell
python -m venv venv
.\venv\Scripts\activate
```

3) Instale as dependências:

```powershell
pip install -r requirements.txt
```

Observação: Se pretende usar processamento com GPU (PyTorch + CUDA), ajuste os pacotes e a instalação conforme sua GPU/OS.

---

## ▶️ Uso (Executando o sistema)

O sistema possui duas partes que devem ser executadas ao mesmo tempo:

1) Dashboard (Streamlit) — interface web

```powershell
cd src
streamlit run app.py
```

Por padrão, o Streamlit abrirá `http://localhost:8501` no navegador.

2) Processador de Vídeos (Visão Computacional)

Em outro terminal, com o ambiente virtual ativado:

```powershell
cd src
python vision_core_videos.py
```

O script processará todo vídeo presente em `data/inputs/videos/` e registrará leituras no banco (`controle_acesso.db`).

---

## 🧭 Estrutura do Projeto

```
Trabalho_Reconhecimento_Veiculos_Python/
├─ data/
│  ├─ inputs/
│  │  ├─ images/
│  │  └─ videos/
├─ src/
│  ├─ app.py                    # Streamlit dashboard
│  ├─ backend.py                # Regras de negócio e integração com o DB
│  ├─ database.py               # Funções SQLite
│  ├─ vision_core_videos.py     # Pipeline de detecção em lote (vídeo -> OCR -> DB)
│  ├─ vision_core_images.py     # (opcional) processamento específico de imagens
│  └─ ...
├─ requirements.txt
├─ yolov8n.pt                   # Modelo YOLOv8 (nucleo leve)
├─ haarcascade_russian_plate_number.xml
```

---

## 🧪 Como Testar com Novos Vídeos

Cole seus arquivos de vídeo em `data/inputs/videos/` e execute `vision_core_videos.py` (veja a seção *Uso*).

O script tentará detectar placas e gravar eventos no banco. Caso o modelo Haar Cascade não exista, ele será baixado automaticamente.

---

## 🚨 Solução de Problemas (Dicas)

- Erro “No module named 'ultralytics'”: verifique se o `venv` está ativado e `pip install -r requirements.txt` foi executado;
- Ninguém é detectado nos vídeos: verifique os formatos (mp4, avi, mov, mkv) e ajuste `TAMANHO_YOLO` e `PULAR_FRAMES` para tentar detectar com mais frames;
- Placas incorretas: testes de qualidade do vídeo (resolução, iluminação) afetam OCR — use melhores frames para testes.

---

## 👥 Autores

- Luís Gustavo
- Aryane
- João Henrique

Prof.: Michael Tadeu

---

## 💡 Dicas Rápidas

- Rode o Streamlit primeiro para ver as atualizações em tempo real enquanto o script de processamento grava novas leituras;
- Verifique o conteúdo do banco `controle_acesso.db` com qualquer ferramenta SQLite (ex.: DB Browser for SQLite) para depurar dados reais.


