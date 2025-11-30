from datetime import datetime

def registrar_leitura(placa, data_hora_real, tempo_no_video, nome_arquivo):
    """
    Função Interface para a Raia 2.
    Aqui será inserido o código SQL para salvar no Banco de Dados.
    """
    data_sql = data_hora_real.strftime("%Y-%m-%d")
    hora_sql = data_hora_real.strftime("%H:%M:%S")
    
    # --- ESPAÇO PARA O CÓDIGO DA RAIA 2 ---
    # Exemplo: cursor.execute("INSERT INTO registros ...")
    # print(f"[DEBUG BACKEND] Salvando: {placa} em {data_sql} {hora_sql}")
    pass