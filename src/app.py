# app.py - VERSÃO FINAL E CORRIGIDA
import streamlit as st
import pandas as pd
import sqlite3 # Necessário para a conexão com o banco na tela de Gestão
from datetime import datetime
import database # Importa nosso módulo de conexão com o banco
import time

# --- Configuração Inicial ---
st.set_page_config(
    page_title="Controle de Acesso - Campus Machado",
    page_icon="🎓",
    layout="wide"
)

# Inicializa banco se não existir (Garante que todas as tabelas existem)
database.inicializar_db()

# --- BARRA LATERAL (MENU) ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/2/22/IFSULDEMINAS_vertical.png", caption="Campus Machado", width=150)
st.sidebar.title("Menu Principal")
opcao = st.sidebar.radio("Navegação", [
    "📡 Monitoramento Real", 
    "📝 Histórico de Acesso", 
    "🚗 Gestão de Veículos"
])

st.sidebar.markdown("---")
st.sidebar.info("Trabalho de Computação Gráfica\nProf. Michael Tadeu")

# --- LÓGICA DAS TELAS ---

# 1. TELA: CARROS NO CAMPUS NO MOMENTO (Fluxograma: Tela Central)
if opcao == "📡 Monitoramento Real":
    st.title("📡 Veículos no Campus Agora")
    st.caption("Monitoramento em tempo real de entradas sem saída registrada.")
    
    if st.button("🔄 Atualizar Lista"):
        st.rerun()

    dados_campus = database.buscar_carros_no_campus()
    
    if not dados_campus:
        st.info("Nenhum veículo detectado dentro do campus no momento.")
    else:
        lista_exibicao = []
        for placa, entrada_str, arquivo in dados_campus:
            
            # --- CORREÇÃO DE BUG (Data Parsing Robusto) ---
            try:
                # Tenta formato completo (com milissegundos)
                entrada_dt = datetime.strptime(entrada_str, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                # Se falhar, tenta formato padrão sem milissegundos
                try:
                    entrada_dt = datetime.strptime(entrada_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    # Se ainda falhar, pula o registro para não quebrar o app
                    st.warning(f"Erro de formato de data no registro da placa {placa}. Pulando cálculo de permanência.")
                    continue 

            agora = datetime.now()
            permanencia = agora - entrada_dt
            minutos_dentro = int(permanencia.total_seconds() / 60)
            # --- FIM DA CORREÇÃO DE DATA ---

            # Busca status do veículo (Requisito 7)
            info_veiculo = database.buscar_info_veiculo(placa)
            status = info_veiculo[1] if info_veiculo else "DESCONHECIDO"
            tipo = info_veiculo[0] if info_veiculo else "NÃO CADASTRADO"
            
            # Lógica de Alertas (Cores e Avisos)
            alerta_seguranca = False
            status_icon = "🟢 AUTORIZADO"
            
            # Alerta 1: Veículo não autorizado ou Ocorrência
            if status in ["NAO_AUTORIZADO", "OCORRENCIA"]:
                alerta_seguranca = True
                status_icon = "🔴 ALERTA DE SEGURANÇA"
            
            # Alerta 2: Tempo excedido (Requisito 6 - Ex: > 4 horas)
            obs_tempo = f"{minutos_dentro} min"
            if minutos_dentro > 240: # 4 horas
                obs_tempo += " ⚠️ TEMPO EXCEDIDO"
                
            lista_exibicao.append({
                "Placa": placa,
                "Tipo": tipo,
                "Entrada": entrada_dt.strftime("%d/%m %H:%M"),
                "Tempo no Campus": obs_tempo,
                "Status": status_icon,
                "Origem": arquivo
            })
            
            if alerta_seguranca:
                st.error(f"🚨 AVISO DE SEGURANÇA: Veículo {placa} ({status}) detectado no campus!")

        df = pd.DataFrame(lista_exibicao)
        st.dataframe(df, use_container_width=True)

        # Métricas Rápidas
        col1, col2 = st.columns(2)
        col1.metric("Total de Veículos", len(df))
        
        # CORREÇÃO DE BUG (KeyError 'Status')
        # Acesso seguro à coluna 'Status' (com S maiúsculo)
        veiculos_em_alerta = len(df[df['Status'].astype(str).str.contains("ALERTA")])
        col2.metric("Veículos em Alerta", veiculos_em_alerta)


# 2. TELA: HISTÓRICO DE ENTRADAS (Fluxograma: Tela Esquerda)
elif opcao == "📝 Histórico de Acesso":
    st.title("📝 Histórico Completo de Acessos")
    st.caption("Log de todas as entradas e saídas registradas.")
    
    dados_hist = database.buscar_historico()
    
    if dados_hist:
        # CORREÇÃO DE BUG (KeyError: Definindo explicitamente os nomes das colunas)
        df_hist = pd.DataFrame(dados_hist, columns=["Placa", "Entrada", "Saída", "Arquivo Fonte"])
        
        # Filtros
        filtro_placa = st.text_input("Filtrar por Placa:").upper().strip()
        if filtro_placa:
            df_hist = df_hist[df_hist["Placa"].str.contains(filtro_placa)]
            
        st.dataframe(df_hist, use_container_width=True)
        
        # Botão para exportar relatório (Requisito 5)
        csv = df_hist.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar Relatório (CSV)",
            data=csv,
            file_name='historico_acessos.csv',
            mime='text/csv',
        )
    else:
        st.warning("O banco de dados de histórico está vazio.")

# 3. TELA: GESTÃO DE VEÍCULOS (Fluxograma: Tela Direita + Requisitos 2 e 3)
elif opcao == "🚗 Gestão de Veículos":
    st.title("🚗 Cadastro e Controle de Veículos")
    st.caption("Defina se um veículo é Oficial/Particular e se está Autorizado.")
    
    col_form, col_view = st.columns([1, 2])
    
    with col_form:
        st.subheader("Cadastrar/Editar")
        with st.form("form_veiculo"):
            placa_input = st.text_input("Placa do Veículo").upper().strip()
            proprietario = st.text_input("Nome do Proprietário/Setor")
            
            # Requisito 2: Gerenciamento diferenciado
            tipo_input = st.selectbox("Tipo de Veículo", ["PARTICULAR", "OFICIAL"])
            
            # Requisito 3 e 7: Marcação de Status
            status_input = st.selectbox("Status de Acesso", ["AUTORIZADO", "NAO_AUTORIZADO", "OCORRENCIA"])
            
            submit = st.form_submit_button("💾 Salvar Registro")
            
            if submit and placa_input:
                database.atualizar_veiculo(placa_input, tipo_input, status_input, proprietario)
                st.success(f"Veículo {placa_input} atualizado!")
                st.rerun()

    with col_view:
        st.subheader("Lista de Veículos Cadastrados")
        conn = sqlite3.connect(database.DB_NAME)
        
        # --- CORREÇÃO DE BUG (ValueError: Usando dtype para forçar strings) ---
        df_veiculos = pd.read_sql(
            "SELECT * FROM veiculos", 
            conn, 
            dtype={
                'placa': str, 
                'tipo': str, 
                'status': str, 
                'proprietario': str, 
                'observacao': str
            }
        )
        # -------------------------------------------------------------------
        conn.close()
        
        if df_veiculos.empty:
            st.info("Nenhum veículo cadastrado ainda. Use o formulário ao lado para começar.")
        else:
            st.dataframe(df_veiculos, use_container_width=True)