# aopp/ui/filters.py
import pandas as pd, streamlit as st
from aopp.config import CACHE_TTL_SECONDS
from aopp.data.preprocess import build_executor_index

def render_filters(df_view: pd.DataFrame):
    # Opções completas
    esp_all = sorted(df_view.get("Especialidade", pd.Series([], dtype=str)).dropna().astype(str).str.strip().unique())
    sup_all = sorted(df_view.get("Supervisor",    pd.Series([], dtype=str)).dropna().astype(str).str.strip().unique())
    cri_all = sorted(df_view.get("Criticidade",   pd.Series([], dtype=str)).dropna().astype(str).str.strip().unique())

    exec_index, exec_all = build_executor_index(df_view[["Executor"]])

    # Defaults (estado anterior)
    esp_sel_prev = st.session_state.get("f_esp", esp_all)
    sup_sel_prev = st.session_state.get("f_sup", sup_all)
    exe_sel_prev = st.session_state.get("f_exec", exec_all)
    cri_sel_prev = st.session_state.get("f_cri", cri_all)

    # Subconjunto relevante (para montar opções “apenas relevantes”)
    mask = pd.Series(True, index=df_view.index)
    if esp_sel_prev and len(esp_sel_prev) < len(esp_all):
        mask &= df_view["Especialidade"].fillna("").astype(str).str.strip().isin(esp_sel_prev)
    if sup_sel_prev and len(sup_sel_prev) < len(sup_all):
        mask &= df_view["Supervisor"].fillna("").astype(str).str.strip().isin(sup_sel_prev)
    if cri_sel_prev and len(cri_sel_prev) < len(cri_all):
        mask &= df_view["Criticidade"].fillna("").astype(str).str.strip().isin(cri_sel_prev)
    if exe_sel_prev and len(exe_sel_prev) < len(exec_all):
        idx_sel=set()
        for name in exe_sel_prev:
            idx_sel |= exec_index.get(name, set())
        mask &= df_view.index.isin(idx_sel)

    df_rel = df_view[mask]

    # Opções relevantes
    esp_opts = sorted(df_rel.get("Especialidade", pd.Series([], dtype=str)).dropna().astype(str).str.strip().unique())
    sup_opts = sorted(df_rel.get("Supervisor", pd.Series([], dtype=str)).dropna().astype(str).str.strip().unique())
    cri_opts = sorted(df_rel.get("Criticidade", pd.Series([], dtype=str)).dropna().astype(str).str.strip().unique())
    exec_rel_set=set()
    for v in df_rel.get("Executor", pd.Series([], dtype=str)).fillna("").astype(str):
        for p in [p.strip() for p in v.split(",") if p.strip()]:
            exec_rel_set.add(p)
    exe_opts = sorted(exec_rel_set) if exec_rel_set else exec_all

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        esp_sel = st.multiselect("Especialidade", options=esp_opts,
                                 default=[x for x in esp_sel_prev if x in esp_opts], key="f_esp")
    with c2:
        sup_sel = st.multiselect("Supervisor", options=sup_opts,
                                 default=[x for x in sup_sel_prev if x in sup_opts], key="f_sup")
    with c3:
        exe_sel = st.multiselect("Executor", options=exe_opts,
                                 default=[x for x in exe_sel_prev if x in exe_opts], key="f_exec")
    with c4:
        cri_sel = st.multiselect("Criticidade", options=cri_opts,
                                 default=[x for x in cri_sel_prev if x in cri_opts], key="f_cri")

    # Aplicar filtros finais
    mask_final = pd.Series(True, index=df_view.index)
    if esp_sel: mask_final &= df_view["Especialidade"].fillna("").astype(str).str.strip().isin(esp_sel)
    if sup_sel: mask_final &= df_view["Supervisor"].fillna("").astype(str).str.strip().isin(sup_sel)
    if cri_sel: mask_final &= df_view["Criticidade"].fillna("").astype(str).str.strip().isin(cri_sel)
    if exe_sel:
        idx_sel=set()
        for name in exe_sel:
            idx_sel |= exec_index.get(name, set())
        mask_final &= df_view.index.isin(idx_sel)

    df_filtered = df_view[mask_final].copy()
    return df_filtered