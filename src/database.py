# database.py
import sqlite3
from datetime import datetime

DB_NAME = "controle_acesso.db"

def inicializar_db():
    """Cria as tabelas se não existirem."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Tabela de Veículos (Para Gestão - Requisito 2 e 3)
    c.execute('''CREATE TABLE IF NOT EXISTS veiculos (
        placa TEXT PRIMARY KEY,
        tipo TEXT,          -- 'OFICIAL' ou 'PARTICULAR'
        status TEXT,        -- 'AUTORIZADO', 'NAO_AUTORIZADO', 'OCORRENCIA'
        proprietario TEXT,
        observacao TEXT
    )''')

    # Tabela de Registros de Acesso (Histórico - Requisito 4)
    c.execute('''CREATE TABLE IF NOT EXISTS registros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        placa TEXT,
        entrada DATETIME,
        saida DATETIME,
        arquivo_origem TEXT
    )''')
    
    conn.commit()
    conn.close()

def salvar_registro(placa, data_hora, arquivo):
    """Registra uma entrada. Se o carro já estiver dentro (sem saída), registra saída."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Verifica se o carro está no campus (tem entrada mas não tem saída)
    c.execute("SELECT id FROM registros WHERE placa = ? AND saida IS NULL", (placa,))
    registro_aberto = c.fetchone()
    
    if registro_aberto:
        # Se já está dentro, registra a SAÍDA (Fecha o ciclo)
        c.execute("UPDATE registros SET saida = ? WHERE id = ?", (data_hora, registro_aberto[0]))
    else:
        # Se não está dentro, registra ENTRADA
        c.execute("INSERT INTO registros (placa, entrada, arquivo_origem) VALUES (?, ?, ?)", 
                  (placa, data_hora, arquivo))
        
    conn.commit()
    conn.close()

def buscar_carros_no_campus():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Pega carros que entraram e o campo saída ainda é nulo
    c.execute("SELECT placa, entrada, arquivo_origem FROM registros WHERE saida IS NULL")
    dados = c.fetchall()
    conn.close()
    return dados

def buscar_historico():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT placa, entrada, saida, arquivo_origem FROM registros ORDER BY entrada DESC")
    dados = c.fetchall()
    conn.close()
    return dados

# Funções de Gestão de Veículos
def atualizar_veiculo(placa, tipo, status, proprietario):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO veiculos (placa, tipo, status, proprietario)
                 VALUES (?, ?, ?, ?)''', (placa, tipo, status, proprietario))
    conn.commit()
    conn.close()

def buscar_info_veiculo(placa):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT tipo, status, proprietario FROM veiculos WHERE placa = ?", (placa,))
    dado = c.fetchone()
    conn.close()
    return dado