import oracledb
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, date
import altair as alt

# Utilizar toda a largura da tela
st.set_page_config(layout="wide")

# Logotipo no topo da barra lateral
st.sidebar.image("imagens/logo_rd.png", use_container_width=True)

# Opção de ambiente
st.sidebar.header("Ambiente")
ambiente = st.sidebar.selectbox("Selecione o ambiente:", ["Homologação", "Produção"])

# Configurações de conexão
if ambiente == "Produção":
    dsn = "rds-scan:1521/r102_consulta.raiadrogasil.com.br"
    user = st.secrets["produçao"]["user"]         # Acessando o usuário de Produção
    password = st.secrets["produçao"]["password"] # Acessando a senha de Produção
else:
    dsn = "10.215.4.7:1521/R102HNEW"
    user = st.secrets["homologacao"]["user"]         # Acessando o usuário de Homologação
    password = st.secrets["homologacao"]["password"] # Acessando a senha de Homologação


# Datas padrão
data_minima = date(2024, 1, 1)
data_maxima = datetime.today().date() #- timedelta(days=1)

# Interface principal
st.title("Dashboard Profimetrics")
st.write("Log de execuções - Interfaces")

# Filtros na barra lateral
st.sidebar.header("Filtros")

# --- Filtro cd_interface com descrição ---
df_interface = pd.read_sql(f"""
    SELECT DISTINCT i.cd_interface, i.ds_interface
    FROM tb_itim_execucao e
    INNER JOIN tb_itim_interface i ON i.cd_interface = e.cd_interface
    WHERE e.dt_execucao BETWEEN TO_DATE('{data_minima.strftime('%d/%m/%Y')}', 'DD/MM/YYYY')
                            AND TO_DATE('{data_maxima.strftime('%d/%m/%Y')}', 'DD/MM/YYYY')
      AND I.CD_ITIM = 0
    ORDER BY i.cd_interface
""", connection)

opcoes_interface_dict = {
    f"{row['CD_INTERFACE']} - {row['DS_INTERFACE']}": row['CD_INTERFACE']
    for _, row in df_interface.iterrows()
}

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
    WHERE e.dt_execucao BETWEEN TO_DATE('{data_minima.strftime('%d/%m/%Y')}', 'DD/MM/YYYY')
                            AND TO_DATE('{data_maxima.strftime('%d/%m/%Y')}', 'DD/MM/YYYY')
      AND I.CD_ITIM > 0                      
      AND i.cd_itim NOT IN (150,152,154,155,156,157,158,396,397,408,512,1008,1203,520)
      AND i.cd_itim < 9000
    ORDER BY i.cd_itim
""", connection)

opcoes_itim_dict = {
    f"{row['CD_ITIM']} - {row['DS_INTERFACE']}": row['CD_ITIM']
    for _, row in df_itim.iterrows()
}

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

if filtros_exec:
    cond_execucao = " OR ".join(filtros_exec)
    query_execucao_aberta = f"""
        SELECT e.cd_interface, i.cd_itim, i.ds_interface
        FROM tb_itim_execucao e
        INNER JOIN tb_itim_interface i ON i.cd_interface = e.cd_interface
        WHERE e.dt_execucao = TO_DATE('{hoje.strftime('%d/%m/%Y')}', 'DD/MM/YYYY')
          AND e.dt_fim IS NULL
          AND ({cond_execucao})
    """
    df_em_execucao = pd.read_sql(query_execucao_aberta, connection)
    if not df_em_execucao.empty:
        interfaces_exec = df_em_execucao["CD_INTERFACE"].unique()
        itims_exec = df_em_execucao["CD_ITIM"].unique()
        descricao_interface = df_em_execucao["DS_INTERFACE"].unique()
      
        mensagem = "<br>".join(
            [f"⚠️ Rotina em Execução:<b> {itim} - {desc}</b> - INTERFACE <b>{interface}</b>"
             for itim, desc, interface in zip(itims_exec, descricao_interface, interfaces_exec)]
        )

        st.markdown(
            f"""
            <div style="background-color:#bbf2d6; padding:15px; border-left:6px solid #428c5e; border-radius:5px; font-size:16px;">
                {mensagem}
            </div>
            """,
            unsafe_allow_html=True
        )
    

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
       ROUND (24 * 60 * (NVL (e.dt_fim, SYSDATE) - e.dt_inicio), 2) tempo,
       TO_CHAR(TRUNC(24 * (NVL(e.dt_fim, SYSDATE) - e.dt_inicio)), '00') || 'h' ||
       TRIM(TO_CHAR(TRUNC(MOD(MOD(NVL(e.dt_fim, SYSDATE) - e.dt_inicio, 1) * 24, 1) * 60), '00')) || 'm' AS HrMin,
       i.cd_itim,
       e.nr_sequencia,
       e.qt_registro,
       e.fl_erro,
       ee.ds_erro
  FROM tb_itim_execucao e
       INNER JOIN tb_itim_interface i ON i.cd_interface = e.cd_interface
       LEFT JOIN tb_itim_execucao_erro ee ON ee.id_execucao = e.id_execucao AND ee.nr_erro = 1
 WHERE e.dt_execucao BETWEEN TO_DATE('{data_inicio.strftime('%d/%m/%Y')}', 'DD/MM/YYYY')
                         AND TO_DATE('{data_fim.strftime('%d/%m/%Y')}', 'DD/MM/YYYY')
   AND i.cd_itim NOT IN (150,152,154,155,156,157,158,396,397,408,512,1008,1203,520)
   AND i.cd_itim < 9000
   {filtro_extra}
"""

# Carregar dados
df = pd.read_sql(query, connection)

# Gráfico
if not df.empty:
    df["DT_EXECUCAO"] = pd.to_datetime(df["DT_EXECUCAO"])
    df["TEMPO"] = pd.to_numeric(df["TEMPO"], errors="coerce")
    df["NR_SEQUENCIA"] = pd.to_numeric(df["NR_SEQUENCIA"], errors="coerce")
    df["QT_REGISTRO"] = df["QT_REGISTRO"].apply(
    lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) else ""
)

    # Legenda: CD_ITIM se diferente de 0, senão CD_INTERFACE
    df["LEGENDA"] = df.apply(
        lambda row: f"CD_ITIM {row['CD_ITIM']}" if row['CD_ITIM'] != 0 else f"CD_INTERFACE {row['CD_INTERFACE']}",
        axis=1
    )

    #df_grouped = df.groupby(["DT_EXECUCAO", "LEGENDA"])["TEMPO"].mean().reset_index(name="tempo_medio")
    df_grouped = df[["DT_EXECUCAO", "LEGENDA", "TEMPO", "NR_SEQUENCIA", "QT_REGISTRO"]].copy()


    grafico = alt.Chart(df_grouped).mark_line(point=True).encode(
        x=alt.X('DT_EXECUCAO:T', title='Data de Execução'),
        y=alt.Y('TEMPO:Q', title='Tempo (minutos)'),
        color=alt.Color('LEGENDA:N', title=""),
        tooltip=["DT_EXECUCAO", "LEGENDA", "NR_SEQUENCIA", "TEMPO", "QT_REGISTRO"]
    ).properties(
        width=2500,
        height=420,
        title="Tempo de Execução x Data"
    )

    st.altair_chart(grafico)
else:
    st.warning("Nenhum dado encontrado com os filtros aplicados.")


on = st.toggle("Visualizar dados")

if on:

    # Tabela
    st.subheader("Detalhes das Execuções")
    st.dataframe(df.drop(columns=["LEGENDA"]), use_container_width=True)


# Fechar conexão
connection.close()
