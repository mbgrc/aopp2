# aopp/charts/curves.py
import pandas as pd, streamlit as st
from aopp.config import CACHE_TTL_SECONDS
from aopp.utils import distribute_by_overlap_daily

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def build_base_curve_timephased(assignment_rows, idx_full_list):
    if not assignment_rows: return None
    idx_full = pd.DatetimeIndex(idx_full_list)
    df = pd.DataFrame.from_records(assignment_rows)
    if df.empty: return None
    planned_daily = pd.Series(0.0, index=idx_full)
    actual_daily  = pd.Series(0.0, index=idx_full)
    for _, r in df.iterrows():
        s, f = r.get("Start"), r.get("Finish")
        if pd.isna(s) or pd.isna(f): continue
        p = float(r.get("Planned_h_total", 0.0) or 0.0)
        a = float(r.get("Actual_h_total", 0.0) or 0.0)
        if p>0: planned_daily = planned_daily.add(distribute_by_overlap_daily(idx_full, s, f, p))
        if a>0: actual_daily  = actual_daily.add(distribute_by_overlap_daily(idx_full, s, f, a))
    total_plan = float(planned_daily.sum())
    if total_plan<=0: return None
    return pd.DataFrame({"Data": idx_full, "PV_daily_h": planned_daily.values,
                         "AC_daily_h": actual_daily.values, "total_plan_h": total_plan})

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def build_base_curve_fallback(tasks_rows, idx_full_list):
    idx_full = pd.DatetimeIndex(idx_full_list)
    d = pd.DataFrame.from_records(tasks_rows)
    d = d[d["IsSummary"] == False].copy()
    total_plan = float(d["Work_h"].fillna(0).sum())
    if total_plan<=0: return None
    pv = pd.Series(0.0, index=idx_full); ev = pd.Series(0.0, index=idx_full)
    for _, r in d.iterrows():
        work = float(r.get("Work_h", 0.0) or 0.0)
        if work<=0: continue
        s, f = r.get("Start"), r.get("Finish")
        if pd.isna(s) or pd.isna(f): continue
        pv = pv.add(distribute_by_overlap_daily(idx_full, s, f, work))
        pctw = float(r.get("PctWorkComplete", 0.0) or 0.0)
        ev = ev.add(distribute_by_overlap_daily(idx_full, s, f, work*(pctw/100.0)))
    return pd.DataFrame({"Data": idx_full, "PV_daily_h": pv.values,
                         "AC_daily_h": ev.values, "total_plan_h": float(pv.sum())})

def apply_apuracao(curve_daily: pd.DataFrame, status_dt: pd.Timestamp):
    status_dt = pd.to_datetime(status_dt)
    status_day = status_dt.normalize()
    df = curve_daily.copy()
    total_plan = float(df["total_plan_h"].iloc[0])
    df["PV_cum_h"] = df["PV_daily_h"].cumsum()
    df["AC_cum_h"] = df["AC_daily_h"].cumsum()
    if (df["Data"] == status_day).any():
        seconds = (status_dt - status_day).total_seconds()
        frac = max(0.0, min(1.0, seconds / 86400.0))
        i = df.index[df["Data"] == status_day][0]
        pv_prev = float(df.loc[i - 1, "PV_cum_h"]) if i - 1 in df.index else 0.0
        pv_today = float(df.loc[i, "PV_daily_h"])
        df.loc[i, "PV_cum_h"] = pv_prev + pv_today * frac
    df["Previsto (%)"]  = (df["PV_cum_h"]/total_plan)*100.0
    df["Realizado (%)"] = (df["AC_cum_h"]/total_plan)*100.0
    df["Previsto (%)"]  = df["Previsto (%)"].clip(0, 100)
    df["Realizado (%)"] = df["Realizado (%)"].clip(0, 100)
    df.loc[df["Data"] > status_day, "Realizado (%)"] = None
    return df[["Data", "Previsto (%)", "Realizado (%)"]]
