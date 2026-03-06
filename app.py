# aopp/app.py
import os, datetime as dt
from datetime import date, datetime, timezone
import numpy as np, pandas as pd, streamlit as st, plotly.graph_objects as go

from aopp.config import (
    LINHAS, CONFIG_DIR, CACHE_TTL_SECONDS, DEFAULT_APUR_TIME,
    DEFAULT_USE_TIMEPHASED, DEFAULT_FORCE_DAILY_TICKS, DEFAULT_SHOW_LABELS,
    DEFAULT_LABEL_EVERY_N, DEFAULT_X_TICK_FONT_SIZE, MESES_PT, HIDE_RESUMO_PAI
)
from aopp.data.loaders import read_areas_config, load_area_records
from aopp.charts.curves import build_base_curve_timephased, build_base_curve_fallback, apply_apuracao
from aopp.utils import add_line_with_labels
from aopp.data.preprocess import attach_columns_and_sort
from aopp.ui.filters import render_filters
from aopp.ui.table import render_table

st.set_page_config(page_title="AOPP", layout="wide")
st.title("📈 AOPP - Acompanhamento Online de Parada Programada")
st.caption(
    "🔬 Desenvolvido por PCM Guararapes Painéis"
    f" | TTL cache: JSON/MPP/Curvas={CACHE_TTL_SECONDS}s"
    f" | Última atualização (do app): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
)

linha = st.radio("Selecione a Linha de produção", LINHAS, horizontal=True, index=0, key="linha_producao")
CONFIG_JSON = os.path.join(CONFIG_DIR, f"{linha}.json")

if "apur_date" not in st.session_state: st.session_state.apur_date = date.today()
if "apur_time" not in st.session_state: st.session_state.apur_time = DEFAULT_APUR_TIME

with st.sidebar:
    st.subheader("Apuração")
    apur_date = st.date_input("Data de apuração", key="apur_date")
    apur_time = st.time_input("Hora de apuração", key="apur_time")
    status_dt = dt.datetime.combine(apur_date, apur_time)

    with st.expander("Ver mais configurações", expanded=False):
        use_timephased   = st.checkbox("Usar timephased do Project (recomendado)", value=DEFAULT_USE_TIMEPHASED)
        force_daily_ticks= st.checkbox("Forçar marcação diária no eixo X", value=DEFAULT_FORCE_DAILY_TICKS)
        show_labels      = st.checkbox("Mostrar rótulos dia a dia", value=DEFAULT_SHOW_LABELS)
        label_every_n    = st.number_input("Mostrar rótulo a cada N dias", min_value=1, value=DEFAULT_LABEL_EVERY_N, step=1)
        x_tick_font_size = st.number_input("Fonte das datas (eixo X)", min_value=6, value=DEFAULT_X_TICK_FONT_SIZE, step=1)

if not os.path.exists(CONFIG_JSON):
    st.warning(f"Não encontrei o arquivo de configuração desta linha: {CONFIG_JSON}")
    st.warning("Crie o arquivo <LINHA>.json na pasta .Config_py para cadastrar as áreas.")
    st.stop()

areas_all = read_areas_config(CONFIG_JSON)

with st.sidebar:
    st.subheader("Áreas (checkbox)")
    enabled_ids=[]
    for a in areas_all:
        ck_key = f"area_enable_{linha}_{a['id']}"
        if ck_key not in st.session_state: st.session_state[ck_key] = True
        if st.checkbox(a["nome"], value=st.session_state[ck_key], key=ck_key):
            enabled_ids.append(a["id"])

areas = [a for a in areas_all if a["id"] in enabled_ids]
if not areas:
    st.warning("Habilite ao menos 1 área na sidebar.")
    st.stop()

try:
    all_task_rows={}, {}
    all_task_rows = {}
    all_assignment_rows = {}
    df_tasks_all=[]
    areas_skipped=[]
    macro_start=None; macro_finish=None

    for area in areas:
        mpp_path = area["mpp"]
        if not os.path.exists(mpp_path):
            st.warning(f"Área '{area['nome']}': arquivo .MPP não encontrado. Ignorando esta área.")
            areas_skipped.append(area["nome"]); continue
        try:
            task_rows, assignment_rows = load_area_records(mpp_path)
        except Exception as ex:
            st.warning(f"Área '{area['nome']}': erro ao ler .MPP. Ignorando. Detalhe: {ex}")
            areas_skipped.append(area["nome"]); continue

        all_task_rows[area["id"]] = task_rows
        all_assignment_rows[area["id"]] = assignment_rows
        df_tmp = pd.DataFrame.from_records(task_rows); df_tmp["Area"] = area["nome"]; df_tasks_all.append(df_tmp)

        d_leaf = df_tmp[df_tmp["IsSummary"]==False].copy()
        if d_leaf.empty: continue
        s = pd.to_datetime(d_leaf["Start"].min()).normalize()
        f = pd.to_datetime(d_leaf["Finish"].max()).normalize()
        if pd.isna(s) or pd.isna(f): continue
        macro_start = s if macro_start is None else min(macro_start, s)
        macro_finish = f if macro_finish is None else max(macro_finish, f)

    if areas_skipped: st.warning("Áreas ignoradas: " + ", ".join(areas_skipped))
    if not df_tasks_all:
        st.warning("Nenhuma área pôde ser carregada (arquivos não encontrados ou erro de leitura)."); st.stop()
    df_tasks_all = pd.concat(df_tasks_all, ignore_index=True)

    # ===== Cabeçalho e métricas
    df_ativ = df_tasks_all[df_tasks_all["IsSummary"]==False].copy()
    p_start_dt = pd.to_datetime(df_ativ["Start"].min())
    p_finish_dt= pd.to_datetime(df_ativ["Finish"].max())
    mes_inicio = MESES_PT.get(int(p_start_dt.month), p_start_dt.strftime("%m"))

    st.subheader(f"Parada Programada {linha} | {mes_inicio}")
    st.caption(f"Macro ({p_start_dt.strftime('%d/%m/%Y %H:%M')} a {p_finish_dt.strftime('%d/%m/%Y %H:%M')})")
    st.success("Acompanhe abaixo o andamento macro (somando áreas carregadas com sucesso).")

    qtd_ativ_previstas = int(df_ativ.shape[0])
    horas_planejadas_duration = float(pd.to_numeric(df_ativ["Duration_h"], errors="coerce").fillna(0).sum())
    crit_counts = (df_ativ["Texto13"].fillna("").astype(str)).pipe(lambda s: s)  # para contagens rápidas
    from aopp.utils import normalize_criticidade
    crit_counts = normalize_criticidade(df_ativ["Texto13"]).value_counts()
    qtd_AA, qtd_A, qtd_B, qtd_C = int(crit_counts.get("AA",0)), int(crit_counts.get("A",0)), int(crit_counts.get("B",0)), int(crit_counts.get("C",0))

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Atividades previstas", f"{qtd_ativ_previstas}", border=True)
    c2.metric("Criticidade AA", f"{qtd_AA}", border=True)
    c3.metric("Criticidade A",  f"{qtd_A}",  border=True)
    c4.metric("Criticidade B",  f"{qtd_B}",  border=True)
    c5.metric("Criticidade C",  f"{qtd_C}",  border=True)
    c6.metric("Horas Planejadas (Duration)", f"{horas_planejadas_duration:.1f} h", border=True)

    # ===== Curva S Macro
    idx_full_macro = pd.date_range(macro_start, macro_finish, freq="D")
    idx_full_list = [pd.Timestamp(x) for x in idx_full_macro]
    status_day = pd.to_datetime(status_dt).normalize()

    area_daily_base={}
    bars_rows=[]
    for area in areas:
        aid=area["id"]
        if aid not in all_task_rows: continue
        base=None
        if use_timephased: base = build_base_curve_timephased(all_assignment_rows[aid], idx_full_list)
        if base is None:   base = build_base_curve_fallback(all_task_rows[aid], idx_full_list)
        area_daily_base[aid]=base
        curve_pct = apply_apuracao(base, pd.to_datetime(status_dt))
        prev = float(curve_pct.loc[curve_pct["Data"]==status_day,"Previsto (%)"].fillna(0).iloc[0]) if (curve_pct["Data"]==status_day).any() else 0.0
        real = float(curve_pct.loc[curve_pct["Data"]==status_day,"Realizado (%)"].fillna(0).iloc[0]) if (curve_pct["Data"]==status_day).any() else 0.0
        bars_rows.append({"Área": area["nome"], "Previsto (%)": prev, "Realizado (%)": real})
    df_bars = pd.DataFrame(bars_rows).sort_values("Área")

    macro_pv_daily = pd.Series(0.0, index=idx_full_macro)
    macro_ac_daily = pd.Series(0.0, index=idx_full_macro)
    for aid, base in area_daily_base.items():
        macro_pv_daily = macro_pv_daily.add(pd.Series(base["PV_daily_h"].values, index=idx_full_macro))
        macro_ac_daily = macro_ac_daily.add(pd.Series(base["AC_daily_h"].values, index=idx_full_macro))

    macro_total_plan = float(macro_pv_daily.sum())
    macro_daily = pd.DataFrame({"Data": idx_full_macro, "PV_daily_h": macro_pv_daily.values,
                                "AC_daily_h": macro_ac_daily.values, "total_plan_h": macro_total_plan})
    macro_curve = apply_apuracao(macro_daily, pd.to_datetime(status_dt))

    st.subheader("Curva S - Macro (Previsto x Realizado)")
    fig = go.Figure()
    if show_labels:
        add_line_with_labels(fig, macro_curve, "Previsto (%)", "Previsto (%)", "#1f77b4", "top center", "solid", int(label_every_n))
        add_line_with_labels(fig, macro_curve, "Realizado (%)", "Realizado (%) (até o dia apurado)", "#ff7f0e", "bottom center", "dash", int(label_every_n))
    else:
        fig.add_trace(go.Scatter(x=macro_curve["Data"], y=macro_curve["Previsto (%)"], name="Previsto (%)", mode="lines+markers"))
        fig.add_trace(go.Scatter(x=macro_curve["Data"], y=macro_curve["Realizado (%)"], name="Realizado (%)", mode="lines+markers", line=dict(dash="dash")))
    fig.update_yaxes(range=[0, 105], title="%")
    fig.update_xaxes(title="Data", tickfont=dict(size=int(x_tick_font_size)), automargin=True)
    if force_daily_ticks: fig.update_xaxes(dtick=86400000.0, tickformat="%d/%m", tickangle=0)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader(f"Previsto x Realizado por Área ({apur_date} {apur_time})")
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(x=df_bars["Área"], y=df_bars["Previsto (%)"], name="Previsto (%)",
                             text=[f"{v:.1f}%" for v in df_bars["Previsto (%)"]], textposition="outside"))
    fig_bar.add_trace(go.Bar(x=df_bars["Área"], y=df_bars["Realizado (%)"], name="Realizado (%)",
                             text=[f"{v:.1f}%" for v in df_bars["Realizado (%)"]], textposition="outside"))
    fig_bar.update_layout(barmode="group", yaxis=dict(range=[0, 100], title="%"),
                          uniformtext_minsize=10, uniformtext_mode="hide")
    st.plotly_chart(fig_bar, use_container_width=True)

    # ===== TABELA: preparar, filtrar e renderizar
    st.subheader("Relatório (somente Nível 3) — filtros visíveis e rápidos")
    df_rep = attach_columns_and_sort(df_tasks_all, status_dt)
    cols_out = [
        "Area","ID","Nome","IsSummary","ParentName","Start","Finish","Duration_h",
        "% Previsto (apur.)","% Realizado","Criticidade","Especialidade","Supervisor","Executor"
    ]
    cols_out = [c for c in cols_out if c in df_rep.columns]
    df_view = df_rep[cols_out].rename(columns={
        "Area":"Área","Nome":"Descrição","IsSummary":"Resumo?","ParentName":"Resumo Pai",
        "Start":"Início","Finish":"Fim","Duration_h":"Duração (h)",
    })
    # Ocultar "Resumo Pai"
    if HIDE_RESUMO_PAI and "Resumo Pai" in df_view.columns:
        df_view = df_view.drop(columns=["Resumo Pai"])

    # Filtros nativos e render da tabela
    df_view_filtered = render_filters(df_view)
    render_table(df_view_filtered, max_style_rows=1500)
    st.caption(f"Exibindo {len(df_view_filtered):,} linhas após filtros.")

except Exception as e:
    st.error(f"Erro ao ler/atualizar dados: {e}")