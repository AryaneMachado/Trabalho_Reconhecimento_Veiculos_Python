# backend.py
from datetime import datetime
import database

# Garante que o banco existe ao iniciar
database.inicializar_db()

def registrar_leitura(placa, data_hora_real, tempo_no_video, nome_arquivo):
    """
    Recebe a leitura da IA e manda para o banco de dados.
    """
    print(f"💾 [DB] Processando placa: {placa}...")
    
    # Formata para string compatível com SQLite
    # data_hora_real já vem como objeto datetime do script original
    
    database.salvar_registro(placa, data_hora_real, nome_arquivo)