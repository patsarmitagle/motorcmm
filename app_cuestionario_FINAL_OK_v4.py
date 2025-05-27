
import subprocess
import sys

# Verificar e instalar fpdf si no está presente
from fpdf import FPDF
import streamlit as st
import json
import sqlite3
from datetime import datetime
import os
import matplotlib.pyplot as plt

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Evaluación de Madurez", layout="wide")

# --- CARGAR DATOS DEL CUESTIONARIO ---
with open("cuestionario_madurez_con_subpreguntas.json", "r", encoding="utf-8") as f:
    preguntas = json.load(f)

# --- CONEXIÓN SQLITE ---
conn = sqlite3.connect("respuestas_madurez.db")
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS respuestas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT,
    nombre TEXT,
    empresa TEXT,
    categoria TEXT,
    variable TEXT,
    promedio REAL,
    nivel INTEGER
)
''')
conn.commit()

# --- AUTENTICACIÓN SIMPLE ---
PASSWORD = "motor2025"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Acceso restringido")
    password_input = st.text_input("Ingresá la contraseña para acceder al cuestionario", type="password")
    if password_input == PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    elif password_input:
        st.error("Contraseña incorrecta.")
    st.stop()

# --- DATOS DEL USUARIO ---
if "usuario_nombre" not in st.session_state:
    st.session_state.usuario_nombre = ""
if "usuario_empresa" not in st.session_state:
    st.session_state.usuario_empresa = ""

if not st.session_state.usuario_nombre or not st.session_state.usuario_empresa:
    st.title("📋 Datos del usuario")
    nombre = st.text_input("Nombre completo")
    empresa = st.text_input("Empresa")
    if nombre and empresa:
        st.session_state.usuario_nombre = nombre
        st.session_state.usuario_empresa = empresa
        st.success("Datos registrados correctamente.")
        st.rerun()
    else:
        st.warning("Por favor completá tus datos.")
        st.stop()

# --- Encabezado con logo y título ---
col1, col2 = st.columns([1, 5])
with col1:
    st.image("logo.png", width=160)
with col2:
    st.markdown("""
        <h2 style='margin-bottom:0;'>Matriz de madurez de motor de decisión</h2>
        <p style='color: #555; margin-top:0;'>Objetivo: brindar una matriz objetiva de evaluación a las organizaciones</p>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- CUESTIONARIO ---
st.title("📊 Cuestionario de Evaluación de Madurez")
st.markdown("Seleccioná el nivel de madurez para cada variable según tu percepción.")

respuestas = {}
categorias = {}

for pregunta in preguntas:
    categoria = pregunta["categoria"]
    variable = pregunta["variable"]
    descripcion = pregunta["descripcion"]
    opciones = pregunta["opciones"]
    subpreguntas = pregunta.get("subpreguntas", None)

    st.markdown(f"### 🧩 {variable} ({categoria})")
    st.write(f"📝 {descripcion}")

    if subpreguntas:
        st.write("**Subevaluación específica:**")
        valores = []
        for i, sp in enumerate(subpreguntas):
            seleccion = st.radio(
                sp["texto"],
                options=sp["opciones"],
                key=f"{variable}_sub_{i}"
            )
            valores.append(sp["opciones"].index(seleccion) + 1)
        promedio = sum(valores) / len(valores)
        if promedio < 2.0:
            nivel = 1
        elif promedio < 3.0:
            nivel = 2
        elif promedio < 3.5:
            nivel = 3
        elif promedio < 4.5:
            nivel = 4
        else:
            nivel = 5
    else:
        seleccion = st.radio(
            f"Seleccioná el nivel general para '{variable}'",
            options=[f"{i+1}. {opciones[i]}" for i in range(5)],
            key=variable
        )
        nivel = int(seleccion.split(".")[0])
        promedio = nivel * 1.0

    respuestas[variable] = (categoria, promedio, nivel)
    categorias.setdefault(categoria, []).append(nivel)

# --- GUARDAR Y PDF ---
if st.button("💾 Guardar resultados y generar PDF"):
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nombre_usuario = st.session_state.usuario_nombre
    nombre_empresa = st.session_state.usuario_empresa

    resultados_finales = {var: promedio for var, (_, promedio, _) in respuestas.items()}

    for variable, (categoria, promedio, nivel) in respuestas.items():
        cursor.execute('''
            INSERT INTO respuestas (fecha, nombre, empresa, categoria, variable, promedio, nivel)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (fecha_actual, nombre_usuario, nombre_empresa, categoria, variable, promedio, nivel))
    conn.commit()

    # --- CREAR PDF ---
    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 14)
            self.cell(0, 10, "Reporte de Evaluación de Madurez", ln=True, align="C")
            self.set_font("Arial", "", 10)
            self.cell(0, 10, f"Usuario: {nombre_usuario} | Empresa: {nombre_empresa} | Fecha: {fecha_actual}", ln=True, align="C")
            self.ln(10)

        def chapter_title(self, title):
            self.set_font("Arial", "B", 12)
            self.cell(0, 10, title, ln=True)
            self.ln(2)

        def chapter_body(self, body):
            self.set_font("Arial", "", 11)
            self.multi_cell(0, 10, body)
            self.ln()

    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    descripcion_dict = {item["variable"]: item["descripcion"] for item in preguntas}
    opciones_dict = {item["variable"]: item["opciones"] for item in preguntas}
    categoria_niveles = {}

    for variable, (categoria, _, nivel) in respuestas.items():
        categoria_niveles.setdefault(categoria, []).append(nivel)

    for variable, puntaje in resultados_finales.items():
        descripcion = descripcion_dict.get(variable, "")
        opciones = opciones_dict.get(variable, [])
        nivel_obtenido = int(round(puntaje))
        nivel_obtenido = max(1, min(nivel_obtenido, len(opciones)))
        detalle_nivel = opciones[nivel_obtenido - 1] if opciones else "Sin detalle de nivel disponible."
        pdf.chapter_title(variable)
        pdf.chapter_body(
            f"Descripción: {descripcion}\n\n"
            f"Nivel obtenido: {nivel_obtenido} (puntaje {puntaje:.2f})\n\n"
            f"Detalle del nivel: {detalle_nivel}"
        )

    pdf.add_page()
    pdf.chapter_title("Resumen por Categoría")
    for categoria, niveles in categoria_niveles.items():
        promedio = sum(niveles) / len(niveles)
        pdf.chapter_body(f"{categoria}: Nivel promedio {promedio:.2f}")

    categorias = list(categoria_niveles.keys())
    promedios = [sum(vals) / len(vals) for vals in categoria_niveles.values()]
    plt.figure(figsize=(10, 5))
    bars = plt.bar(categorias, promedios)
    plt.ylim(0, 5)
    plt.ylabel("Nivel Promedio")
    plt.title("Resumen de Madurez por Categoría")
    plt.xticks(rotation=45, ha="right")
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 0.1, f"{yval:.2f}", ha="center")

    os.makedirs("graficos", exist_ok=True)
    grafico_path = "graficos/resumen_categorias.png"
    plt.tight_layout()
    plt.savefig(grafico_path)
    plt.close()

    pdf.add_page()
    pdf.chapter_title("Gráfico de Madurez por Categoría")
    pdf.image(grafico_path, w=180)

    os.makedirs("resultados_pdf", exist_ok=True)
    nombre_archivo = f"reporte_madurez_{nombre_usuario}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    ruta_pdf = f"resultados_pdf/{nombre_archivo}"
    pdf.output(ruta_pdf)

    st.success("✅ Respuestas guardadas correctamente.")
    st.download_button("📄 Descargar PDF", data=open(ruta_pdf, "rb"), file_name=nombre_archivo)
