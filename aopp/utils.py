# aopp/utils.py
import pandas as pd
import plotly.graph_objects as go
from aopp.config import MINUTES_PER_DAY, MINUTES_PER_WEEK

def to_py_int(x, default=None):
    try: return int(x) if x is not None else default
    except: return default

def to_py_float(x, default=0.0):
    try: return float(x) if x is not None else default
    except: return default

def to_py_bool(x, default=False):
    try: return bool(x) if x is not None else default
    except: return default

def to_py_str(x): return None if x is None else str(x)

def to_py_datetime(x):
    if x is None: return None
    return pd.to_datetime(str(x), errors="coerce")

def duration_to_hours(duration_obj):
    if duration_obj is None: return 0.0
    try:
        value = float(duration_obj.getDuration())
        units = str(duration_obj.getUnits())
        if units in ("HOURS","HOUR"): return value
        if units in ("MINUTES","MINUTE"): return value/60.0
        if units in ("DAYS","DAY"): return value*(MINUTES_PER_DAY/60.0)
        if units in ("WEEKS","WEEK"): return value*(MINUTES_PER_WEEK/60.0)
        return value
    except: return 0.0

def distribute_by_overlap_daily(index_days, start, finish, total_value: float) -> pd.Series:
    out = pd.Series(0.0, index=index_days)
    if not total_value or pd.isna(total_value) or total_value == 0.0: return out
    if start is None or finish is None or pd.isna(start) or pd.isna(finish): return out
    s = pd.to_datetime(start); f = pd.to_datetime(finish)
    if f <= s: return out
    overlaps, days = [], []
    for d0 in index_days:
        d1 = d0 + pd.Timedelta(days=1)
        a, b = max(s, d0), min(f, d1)
        sec = (b - a).total_seconds()
        if sec > 0: days.append(d0); overlaps.append(sec)
    if not overlaps: return out
    total_sec = sum(overlaps)
    for d0, sec in zip(days, overlaps):
        out.loc[d0] = float(total_value) * (sec / total_sec)
    return out

def add_line_with_labels(fig: go.Figure, curve, col, name, color, text_position,
                         dash="solid", label_every_n=1, always_show_last_label=True):
    x = curve["Data"].tolist()
    y = curve[col].tolist()
    last_valid_i = next((i for i in range(len(y)-1, -1, -1) if y[i] is not None and not (isinstance(y[i], float) and pd.isna(y[i]))), None)
    text=[]
    for i,v in enumerate(y):
        if v is None or (isinstance(v,float) and pd.isna(v)): text.append(""); continue
        must = True
        if label_every_n>1 and (i % label_every_n)!=0: must=False
        if always_show_last_label and last_valid_i is not None and i==last_valid_i: must=True
        text.append(f"{v:.1f}%" if must else "")
    fig.add_trace(go.Scatter(
        x=x, y=y, name=name, mode="lines+markers+text", text=text, textposition=text_position,
        textfont=dict(size=10, color=color), line=dict(color=color, width=2, dash=dash),
        marker=dict(size=5, color=color), hovertemplate="%{x|%d/%m/%Y}<br>%{y:.2f}%<extra>"+name+"</extra>",
        cliponaxis=False
    ))

def normalize_criticidade(series: pd.Series) -> pd.Series:
    s = series.fillna("").astype(str).str.strip().str.upper()
    s = s.str.replace("–","-", regex=False).str.split("-", n=1).str[0]
    s = s.str.split(" ", n=1).str[0].str.strip()
    return s
