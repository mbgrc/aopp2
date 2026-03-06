# aopp/data/loaders.py
import os
import json
import pandas as pd
import streamlit as st

from aopp.config import CACHE_TTL_SECONDS
from aopp.utils import (
    to_py_int, to_py_float, to_py_bool, to_py_str,
    to_py_datetime, duration_to_hours
)
from aopp.data.mpxj_reader import get_reader  # <-- CORRETO: import absoluto pelo pacote

@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Lendo configuração (JSON)...")
def read_areas_config(json_path: str):
    with open(json_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    areas = cfg.get("areas", [])
    if not isinstance(areas, list) or not areas:
        raise ValueError(f"JSON inválido ou vazio: {json_path} (esperado: 'areas': [ ... ])")
    for a in areas:
        if "id" not in a or "nome" not in a or "mpp" not in a:
            raise ValueError(f"Área inválida no JSON: {a}. Campos obrigatórios: id, nome, mpp.")
    return areas

@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Lendo .MPP (cache)...")
def load_area_records(mpp_path: str):
    reader = get_reader()
    if not os.path.exists(mpp_path):
        raise FileNotFoundError(f".MPP não encontrado: {mpp_path}")
    project = reader.read(mpp_path)

    # Map de executores por Task UniqueID
    executores_por_task_uid = {}
    for a in project.getResourceAssignments():
        if a is None: continue
        task, res = a.getTask(), a.getResource()
        if task is None or res is None: continue
        try:
            task_uid = int(task.getUniqueID()) if task.getUniqueID() is not None else None
        except: task_uid = None
        if task_uid is None: continue
        nome_res = to_py_str(res.getName())
        if not nome_res: continue
        executores_por_task_uid.setdefault(task_uid, set()).add(nome_res)

    # Tasks
    task_rows=[]
    for t in project.getTasks():
        if t is None: continue
        try: task_uid = int(t.getUniqueID()) if t.getUniqueID() is not None else None
        except: task_uid = None
        texto13 = to_py_str(t.getText(13)) # criticidade
        texto2  = to_py_str(t.getText(2))  # especialidade
        texto15 = to_py_str(t.getText(15)) # supervisor
        try:
            outline_level = int(t.getOutlineLevel()) if t.getOutlineLevel() is not None else None
        except: outline_level = None
        try:
            parent = t.getParentTask()
            parent_name = to_py_str(parent.getName()) if parent is not None else None
        except: parent_name = None
        executores = ""
        if task_uid is not None and task_uid in executores_por_task_uid:
            executores = ", ".join(sorted(executores_por_task_uid[task_uid]))
        task_rows.append({
            "UniqueID": task_uid,
            "ID": to_py_int(t.getID()),
            "Nome": to_py_str(t.getName()),
            "IsSummary": to_py_bool(t.getSummary(), False),
            "OutlineLevel": outline_level,
            "ParentName": parent_name,
            "Start": to_py_datetime(t.getStart()),
            "Finish": to_py_datetime(t.getFinish()),
            "Duration_h": float(duration_to_hours(t.getDuration())),
            "Work_h": float(duration_to_hours(t.getWork())),
            "ActualWork_h": float(duration_to_hours(t.getActualWork())),
            "PctWorkComplete": to_py_float(t.getPercentageWorkComplete(), 0.0),
            "Texto13": texto13,
            "Criticidade": texto13,
            "Especialidade": texto2,
            "Supervisor": texto15,
            "Executor": executores,
        })

    # Timephased ranges
    assignment_rows=[]
    for a in project.getResourceAssignments():
        if a is None: continue
        task = a.getTask()
        if task is None: continue
        if task.getSummary() is not None and bool(task.getSummary()): continue

        tpw = a.getTimephasedWork()
        if tpw is not None:
            for item in tpw:
                s0 = to_py_datetime(item.getStart()); f0 = to_py_datetime(item.getFinish())
                if s0 is None or f0 is None or pd.isna(s0) or pd.isna(f0): continue
                planned_h_total = duration_to_hours(item.getTotalAmount())
                if planned_h_total and planned_h_total>0:
                    assignment_rows.append({"Start": pd.to_datetime(s0), "Finish": pd.to_datetime(f0),
                                            "Planned_h_total": float(planned_h_total), "Actual_h_total": 0.0})
        try: tpa = a.getTimephasedActualWork()
        except: tpa = None
        if tpa is not None:
            for item in tpa:
                s0 = to_py_datetime(item.getStart()); f0 = to_py_datetime(item.getFinish())
                if s0 is None or f0 is None or pd.isna(s0) or pd.isna(f0): continue
                actual_h_total = duration_to_hours(item.getTotalAmount())
                if actual_h_total and actual_h_total>0:
                    assignment_rows.append({"Start": pd.to_datetime(s0), "Finish": pd.to_datetime(f0),
                                            "Planned_h_total": 0.0, "Actual_h_total": float(actual_h_total)})
    return task_rows, assignment_rows
