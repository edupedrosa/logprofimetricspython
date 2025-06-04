import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, date
import altair as alt

# Utilizar toda a largura da tela
st.set_page_config(layout="wide")

# Logotipo no topo da barra lateral
st.sidebar.image("logo_rd.png", use_container_width=True)

# Opção de ambiente
st.sidebar.header("Ambiente")
ambiente = st.sidebar.selectbox("Selecione o ambiente:", ["Produção","Homologação"])

# Configurações de conexão
#db_path = "C:/epedrosa/Outros/Python/log_profimetrics.db"  # Defina o caminho do seu banco de dados SQLite

# Conectar ao SQLite
connection = sqlite3.connect('log_profimetrics.db')

# Datas padrão
data_minima = date(2025, 1, 1)
data_maxima = datetime.today().date() - timedelta(days=1)

# Interface principal
st.subheader("Dashboard Profimetrics")
st.write("Log de execuções - Interfaces")

# Filtros na barra lateral
st.sidebar.header("Filtros")

# --- Filtro cd_interface com descrição ---
df_interface = pd.read_sql(f"""
    SELECT DISTINCT i.cd_interface, i.ds_interface
    FROM tb_itim_execucao e
    INNER JOIN tb_itim_interface i ON i.cd_interface = e.cd_interface
    WHERE e.dt_execucao BETWEEN '{data_minima.strftime('%Y-%m-%d')}' 
                            AND '{data_maxima.strftime('%Y-%m-%d')}'
      AND I.CD_ITIM = 0
    ORDER BY i.cd_interface
""", connection)

print("Colunas do DataFrame df_interface:", df_interface.columns)

if 'cd_interface' in df_interface.columns and 'ds_interface' in df_interface.columns:
    opcoes_interface_dict = {
        f"{row['cd_interface']} - {row['ds_interface']}": row['cd_interface']
        for _, row in df_interface.iterrows()
    }
else:
    st.warning("As colunas 'cd_interface' e 'ds_interface' não foram encontradas.")

interfaces_selecionadas = st.sidebar.multiselect(
    "Selecione a interface por (CD_INTERFACE)",
    options=list(opcoes_interface_dict.keys()),
    default=[]
)

cd_interface_filtradas = [opcoes_interface_dict[nome] for nome in interfaces_selecionadas]
filtro_interface_sql = ""
if cd_interface_filtradas:
    interface_str = ",".join(map(str, cd_interface_filtradas))
    filtro_interface_sql = f"i.cd_interface IN ({interface_str})"

# --- Filtro cd_itim com descrição ---
df_itim = pd.read_sql(f"""
    SELECT DISTINCT i.cd_itim, i.ds_interface
    FROM tb_itim_execucao e
    INNER JOIN tb_itim_interface i ON i.cd_interface = e.cd_interface
    WHERE e.dt_execucao BETWEEN '{data_minima.strftime('%Y-%m-%d')}' 
                            AND '{data_maxima.strftime('%Y-%m-%d')}'
      AND I.CD_ITIM > 0                      
      AND i.cd_itim NOT IN (150,152,154,155,156,157,158,396,397,408,512,1008,1203,520)
      AND i.cd_itim < 9000
    ORDER BY i.cd_itim
""", connection)

print("Colunas do DataFrame df_itim:", df_itim.columns)

if 'cd_itim' in df_itim.columns and 'ds_interface' in df_itim.columns:
    opcoes_itim_dict = {
        f"{row['cd_itim']} - {row['ds_interface']}": row['cd_itim']
        for _, row in df_itim.iterrows()
    }
else:
    st.warning("As colunas 'cd_itim' e 'ds_interface' não foram encontradas.")

itims_selecionados = st.sidebar.multiselect(
    "Selecione a interface por (CD_ITIM)",
    options=list(opcoes_itim_dict.keys()),
    default=[]
)

cd_itim_filtrados = [opcoes_itim_dict[nome] for nome in itims_selecionados]
filtro_itim_sql = ""
if cd_itim_filtrados:
    itim_str = ",".join(map(str, cd_itim_filtrados))
    filtro_itim_sql = f"i.cd_itim IN ({itim_str})"

# Combinar filtros com OR
filtro_extra = ""
if filtro_itim_sql and filtro_interface_sql:
    filtro_extra = f"AND ({filtro_itim_sql} OR {filtro_interface_sql})"
elif filtro_itim_sql:
    filtro_extra = f"AND {filtro_itim_sql}"
elif filtro_interface_sql:
    filtro_extra = f"AND {filtro_interface_sql}"

# Verificar se há execução em andamento para hoje
hoje = datetime.today().date()
filtros_exec = []
if cd_itim_filtrados:
    filtros_exec.append(f"i.cd_itim IN ({', '.join(map(str, cd_itim_filtrados))})")
if cd_interface_filtradas:
    filtros_exec.append(f"e.cd_interface IN ({', '.join(map(str, cd_interface_filtradas))})")

# Verifica se a rotina selecionada se encontra em execucao
# if filtros_exec:
#     cond_execucao = " OR ".join(filtros_exec)
#     query_execucao_aberta = f"""
#         SELECT e.cd_interface, i.cd_itim, i.ds_interface
#         FROM tb_itim_execucao e
#         INNER JOIN tb_itim_interface i ON i.cd_interface = e.cd_interface
#         WHERE e.dt_execucao = '{hoje.strftime('%Y-%m-%d')}'
#           AND e.dt_fim IS NULL
#           AND ({cond_execucao})
#     """
#     df_em_execucao = pd.read_sql(query_execucao_aberta, connection)
#     if not df_em_execucao.empty:
#         interfaces_exec = df_em_execucao["cd_interface"].unique()
#         itims_exec = df_em_execucao["cd_itim"].unique()
#         descricao_interface = df_em_execucao["ds_interface"].unique()
      
#         mensagem = "<br>".join(
#             [f"⚠️ Rotina em Execução:<b> {itim} - {desc}</b> - INTERFACE <b>{interface}</b>"
#              for itim, desc, interface in zip(itims_exec, descricao_interface, interfaces_exec)]
#         )

#         st.markdown(
#             f"""
#             <div style="background-color:#bbf2d6; padding:15px; border-left:6px solid #428c5e; border-radius:5px; font-size:16px;">
#                 {mensagem}
#             </div>
#             """,
#             unsafe_allow_html=True
#         )

# Slider de data
data_inicio, data_fim = st.sidebar.slider(
    "Selecione o intervalo de datas (DT_EXECUCAO):",
    min_value=data_minima,
    max_value=data_maxima,
    value=(data_maxima - timedelta(days=7), data_maxima),
    format="DD/MM/YYYY"
)

# Consulta principal com filtros
query = f"""
SELECT e.cd_interface,
       i.ds_interface,
       e.dt_execucao,
       e.nm_tabela_itim,
       e.dt_inicio,
       e.dt_fim,
       e.tempo,
       e.hrmin,
       i.cd_itim,
       e.nr_sequencia,
       e.qt_registro,
       e.fl_erro,
       ee.ds_erro
  FROM tb_itim_execucao e
       INNER JOIN tb_itim_interface i ON i.cd_interface = e.cd_interface
       LEFT JOIN tb_itim_execucao_erro ee ON ee.id_execucao = e.id_execucao AND ee.nr_erro = 1
 WHERE e.dt_execucao BETWEEN '{data_inicio.strftime('%Y-%m-%d')}' 
                         AND '{data_fim.strftime('%Y-%m-%d')}'
   AND i.cd_itim NOT IN (150,152,154,155,156,157,158,396,397,408,512,1008,1203,520)
   AND i.cd_itim < 9000
   {filtro_extra}
"""

# Carregar dados
df = pd.read_sql(query, connection)

# Gráfico
if not df.empty:
    df["dt_execucao"] = pd.to_datetime(df["dt_execucao"])  # Altere para o nome correto da coluna
    df["tempo"] = pd.to_numeric(df["tempo"], errors="coerce")
    df["nr_sequencia"] = pd.to_numeric(df["nr_sequencia"], errors="coerce")
    df["qt_registro"] = df["qt_registro"].apply(
        lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) else ""
    )

    # Legenda: CD_ITIM se diferente de 0, senão CD_INTERFACE
    df["LEGENDA"] = df.apply(
        lambda row: f"CD_ITIM {row['cd_itim']}" if row['cd_itim'] != 0 else f"CD_INTERFACE {row['cd_interface']}",
        axis=1
    )

    df_grouped = df[["dt_execucao", "LEGENDA", "tempo", "nr_sequencia", "qt_registro"]].copy()

    grafico = alt.Chart(df_grouped).mark_line(point=True).encode(
        x=alt.X('dt_execucao:T', title='Data de Execução'),
        y=alt.Y('tempo:Q', title='Tempo (minutos)'),
        color=alt.Color('LEGENDA:N', title=""),
        tooltip=["dt_execucao", "LEGENDA", "nr_sequencia", "tempo", "qt_registro"]
    ).properties(
        width=2500,
        height=420,
        title="Tempo de Execução x Data"
    )
    st.altair_chart(grafico)
else:
    st.warning("Nenhum dado encontrado com os filtros aplicados.")

on = st.toggle("Visualizar dados")

# if on:
#     # Tabela
#     st.subheader("Detalhes das Execuções")
#     st.dataframe(df.drop(columns=["LEGENDA"]), use_container_width=True)

# Exibir dados no Streamlit
if on:
    st.subheader("Detalhes dos Dados")
    if not df.empty:
        st.dataframe(df)  # Exibir os dados como um dataframe interativo
    else:
        st.warning("Nenhum dado encontrado com os filtros aplicados.")

# Fechar conexão
connection.close()