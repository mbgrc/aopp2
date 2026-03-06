# aopp/ui/table.py
import pandas as pd, streamlit as st

def _max_len_iterable(it):
    m=0
    for x in it:
        l = 0 if x is None or (isinstance(x,float) and pd.isna(x)) else len(str(x))
        if l>m: m=l
    return m

def autosize_column_config(df: pd.DataFrame, min_px=90, max_px=520, char_px=8.2, pad_px=32) -> dict:
    cfg={}
    for col in df.columns:
        s=df[col]; header_len=len(str(col))
        is_percent  = col in ["% Previsto (apur.)","% Realizado"]
        is_datetime = pd.api.types.is_datetime64_any_dtype(s) or col in ["Início","Fim"]
        if is_percent: px=int(6*char_px+pad_px)
        elif is_datetime: px=int(17*char_px+pad_px)
        else:
            px=int(max(header_len,_max_len_iterable(s.astype("object")))*char_px+pad_px)
            if col in ["Descrição","Executor","Área","Resumo Pai"]:
                px=int(px*1.15)
        px=max(min_px,min(px,max_px))
        pinned=True if col=="Área" else None
        cfg[col]=st.column_config.Column(col,width=px,pinned=pinned)
    return cfg

def render_table(df_view: pd.DataFrame, max_style_rows=1500):
    CRIT_COLOR={"AA":"#ff4d4d","A":"#ffa64d","B":"#fff176","C":"#c8e6c9"}
    def style_row(row):
        c=str(row.get("Criticidade","")).strip().upper()
        bg=CRIT_COLOR.get(c,"")
        return [f"background-color: {bg};"]*len(row) if bg else [""]*len(row)

    auto_cfg = autosize_column_config(df_view, min_px=90, max_px=520, char_px=8.4, pad_px=36)
    if len(df_view) <= max_style_rows:
        styled = df_view.style.apply(style_row, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True, column_config=auto_cfg)
    else:
        st.dataframe(df_view, use_container_width=True, hide_index=True, column_config=auto_cfg)
        st.info("Colorização por Criticidade desativada para conjuntos grandes (ganho de performance).")
