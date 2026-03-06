# aopp/data/preprocess.py
import numpy as np, pandas as pd, streamlit as st
from aopp.config import CACHE_TTL_SECONDS
from aopp.utils import normalize_criticidade

def compute_previsto_pct(df_rep: pd.DataFrame, status_ts) -> pd.Series:
    s = pd.to_datetime(df_rep["Start"], errors="coerce")
    f = pd.to_datetime(df_rep["Finish"], errors="coerce")
    # end = min(Finish, status_ts)
    end = pd.Series(pd.to_datetime(np.minimum(f.astype("int64"), np.int64(pd.Timestamp(status_ts).value))),
                    index=df_rep.index)
    num = (end - s).dt.total_seconds().clip(lower=0)
    den = (f - s).dt.total_seconds()
    pct_prev = (num/den*100).replace([np.inf,-np.inf], np.nan).clip(0, 100)
    return pct_prev.where(den > 0)

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def build_executor_index(df_idx: pd.DataFrame):
    mapping = {}
    for idx, val in df_idx["Executor"].fillna("").astype(str).items():
        parts = [p.strip() for p in val.split(",") if p.strip()]
        for name in parts:
            mapping.setdefault(name, set()).add(idx)
    return mapping, sorted(mapping.keys())

def attach_columns_and_sort(df_tasks_all: pd.DataFrame, status_ts) -> pd.DataFrame:
    df_rep = df_tasks_all.copy()
    df_rep["OutlineLevel"] = pd.to_numeric(df_rep.get("OutlineLevel"), errors="coerce")
    df_rep = df_rep[df_rep["OutlineLevel"] == 3].copy()
    df_rep["% Previsto (apur.)"] = compute_previsto_pct(df_rep, status_ts)
    df_rep["Criticidade"] = normalize_criticidade(df_rep.get("Texto13", pd.Series([], dtype=str)))
    df_rep["% Realizado"] = pd.to_numeric(df_rep.get("PctWorkComplete"), errors="coerce").fillna(0.0)
    df_rep["Duration_h"] = pd.to_numeric(df_rep.get("Duration_h"), errors="coerce").fillna(0.0)
    df_rep = df_rep.sort_values(["Duration_h", "% Realizado"], ascending=[False, False])
    return df_rep