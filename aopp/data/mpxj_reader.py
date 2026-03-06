# aopp/data/mpxj_reader.py
import importlib
import jpype
import jpype.imports
import streamlit as st
import mpxj  # <-- IMPORTANTE: garante que os JARs do MPXJ entrem no classpath antes de startJVM

@st.cache_resource
def get_reader():
    """
    Sobe a JVM 1x por sessão e devolve UniversalProjectReader (org.mpxj).
    Requisitos:
      - pip install mpxj jpype1
      - Java (JDK/JRE) instalado e compatível (x64)
    """
    if not jpype.isJVMStarted():
        # Localiza a JVM instalada
        jvmpath = jpype.getDefaultJVMPath()

        # Argumentos úteis para JDK 17+ (evitam problemas de acesso/reflection)
        jvm_args = [
            "--enable-native-access=ALL-UNNAMED",
            "--add-opens=java.base/java.lang=ALL-UNNAMED",
        ]

        # Inicia a JVM. Não usar kwargs inexistentes como jvmOptions=...
        # Não precisamos passar classpath aqui porque o 'import mpxj' já cuidou disso.
        jpype.startJVM(jvmpath, *jvm_args)

        # Garante plugin de imports do JPype carregado
        importlib.import_module("jpype.imports")

    # Namespace CORRETO nas versões atuais do MPXJ é 'org.mpxj'
    from org.mpxj.reader import UniversalProjectReader
    return UniversalProjectReader()