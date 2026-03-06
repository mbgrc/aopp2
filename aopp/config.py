# aopp/config.py
import datetime as dt

# LINHAS / CONFIG
LINHAS = ["MDF02", "MDF03", "BP02", "BP03", "BP04"]
CONFIG_DIR = r"\\grpps012oci\manutencao$\01 - PPCM\02. PARADAS\.Config_py"

# CACHE E PREFERÊNCIAS
CACHE_TTL_SECONDS = 100
DEFAULT_APUR_TIME = dt.time(15, 0)
DEFAULT_USE_TIMEPHASED = True
DEFAULT_FORCE_DAILY_TICKS = True
DEFAULT_SHOW_LABELS = True
DEFAULT_LABEL_EVERY_N = 1
DEFAULT_X_TICK_FONT_SIZE = 14

# VISUAL
HIDE_RESUMO_PAI = True  # oculta "Resumo Pai" na tabela final

# CONSTANTES DE TEMPO
MINUTES_PER_DAY = 1440
MINUTES_PER_WEEK = 10080

# Meses PT
MESES_PT = {
    1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",5:"Maio",6:"Junho",
    7:"Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro"
}