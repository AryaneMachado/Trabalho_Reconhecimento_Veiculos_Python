# backend.py
import database
from datetime import datetime

# Limite para alerta visual no console (apenas informativo)
# O controle real de tempo fica nos relatórios do banco
LIMITE_TEMPO_VISITANTE = 240 

def registrar_leitura(placa, data_hora, tempo_video, arquivo_origem):
    """
    Recebe a leitura da Visão Computacional e delega para o Banco de Dados.
    Removemos a lógica duplicada de entrada/saída conforme solicitado.
    """
    
    # 1. Garante que o banco existe (Auto-cura)
    database.inicializar_db()

    print(f"🔄 Processando: {placa}...")
    
    # 2. Verifica/Cria Cadastro (Regra de Negócio: Auto-cadastro de Visitantes)
    # Usamos as funções do próprio database.py para não duplicar SQL
    info_veiculo = database.buscar_info_veiculo(placa)
    
    if not info_veiculo:
        print(f"🆕 Veículo Inédito. Cadastrando Visitante: {placa}")
        database.atualizar_veiculo(placa, 'VISITANTE', 'NAO_AUTORIZADO', 'Auto-detectado pelo vídeo')
        status = 'NAO_AUTORIZADO'
    else:
        # info_veiculo retorna (tipo, status, proprietario)
        status = info_veiculo[1] 

    # 3. Alerta de Segurança IMEDIATO (Requisito 7)
    # Isso deve acontecer ANTES de salvar, para gerar o log de console
    if status in ['NAO_AUTORIZADO', 'OCORRENCIA']:
        print(f"🚨🚨 ALERTA CRÍTICO: Veículo {status} detectado na portaria: {placa}!")

    # 4. Persistência (Delega a lógica de Entrada/Saída para o database.py)
    # A função salvar_registro já verifica se o carro está dentro ou fora
    database.salvar_registro(placa, data_hora, arquivo_origem)
    
    print(f"✅ Registro computado no banco para {placa}.")