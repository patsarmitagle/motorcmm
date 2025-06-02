
import subprocess
import sys

# Verificar e instalar fpdf si no está presente
try:
    from fpdf import FPDF
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fpdf"])
    from fpdf import FPDF

import streamlit as st
import json
import sqlite3
from datetime import datetime
import os
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import re  

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
    email TEXT,           
    empresa TEXT,
    categoria TEXT,
    variable TEXT,
    promedio REAL,
    nivel INTEGER,
    observacion TEXT
)
''')
conn.commit()

# --- AUTENTICACIÓN SIMPLE ---
PASSWORD = "motor2025"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


if not st.session_state.authenticated:
    col1, col2 = st.columns([1, 5])
    with col1:
        st.image("logo.png", width=150)
    with col2:
        st.title(" Acceso restringido")

    password_input = st.text_input("Ingresá la contraseña para acceder al cuestionario", type="password")
    if password_input == PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    elif password_input:
        st.error("🔐 Contraseña incorrecta.")
    st.stop()

# --- DATOS DEL USUARIO ---
if "usuario_nombre" not in st.session_state:
    st.session_state.usuario_nombre = ""
if "usuario_empresa" not in st.session_state:
    st.session_state.usuario_empresa = ""
if "usuario_email" not in st.session_state:
    st.session_state.usuario_email = ""    

if not st.session_state.usuario_nombre or not st.session_state.usuario_empresa or not st.session_state.usuario_email:
    # Mostrar logo arriba del formulario
    col1, col2 = st.columns([1, 5])
    with col1:
        st.image("logo.png", width=160)  # Cambiar el path si el logo está en otra carpeta
    with col2:
        st.title("Datos del usuario")

    nombre = st.text_input("👤 Nombre completo")
    empresa = st.text_input("🏢 Empresa")
    email = st.text_input("✉️ Email")
  
  #Validar campos y Botón para confirmar

    if st.button("➡️ Continuar"):
        if nombre and empresa and email:
            email_valido = re.match(r"[^@]+@[^@]+\.[^@]+", email)
            if email_valido:
                st.session_state.usuario_nombre = nombre
                st.session_state.usuario_empresa = empresa
                st.session_state.usuario_email = email
                st.success("✅ Datos registrados correctamente.")
                st.rerun()
            else:
                st.error("❌ El email ingresado no tiene un formato válido. Ejemplo: nombre@empresa.com")
        else:
            st.warning("⚠️ Por favor completá todos los campos.")

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
st.title("Cuestionario de Evaluación de Madurez")
st.markdown("Seleccioná el nivel de madurez para cada variable según tu percepción.")

respuestas = {}
categorias = {}

for pregunta in preguntas:
    categoria = pregunta["categoria"]
    variable = pregunta["variable"]
    descripcion = pregunta["descripcion"]
    opciones = pregunta["opciones"]
    subpreguntas = pregunta.get("subpreguntas", None)

    st.markdown(f"###  {variable} ({categoria})")
    st.write(f"📝 {descripcion}")

    if subpreguntas:
        st.write("**Subevaluación específica:**")
        valores = []
        for i, sp in enumerate(subpreguntas):
            st.markdown(f"<div style='font-size:18px; font-weight:500'>{sp['texto']}</div>", unsafe_allow_html=True)
            seleccion = st.radio(
                "",
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

    texto_libre = st.text_area(
    "Puntos de dolor en su empresa o necesidades que necesita cubrir",
        key=f"{variable}_texto_libre"
    )
    respuestas[variable] += (texto_libre,)  # Guardamos como tupla de 4 elementos

# --- GUARDAR Y PDF ---
if st.button("💾 Guardar resultados y generar PDF"):
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nombre_usuario = st.session_state.usuario_nombre
    nombre_empresa = st.session_state.usuario_empresa
    nombre_email = st.session_state.usuario_email

    resultados_finales = {}
    for var, (categoria, promedio, nivel, observacion) in respuestas.items():
        resultados_finales[var] = promedio

    for variable, (categoria, promedio, nivel, observacion) in respuestas.items():
        cursor.execute('''
            INSERT INTO respuestas (fecha, nombre, email, empresa, categoria, variable, promedio, nivel, observacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (fecha_actual, nombre_usuario, nombre_email, nombre_empresa, categoria, variable, promedio, nivel, observacion))
    conn.commit()
   
   # Calcular niveles promedio por categoría
    categoria_niveles = {}
    for variable, (categoria, _, nivel, _) in respuestas.items():
        categoria_niveles.setdefault(categoria, []).append(nivel)
    
    categorias = list(categoria_niveles.keys())
    promedios = [sum(vals) / len(vals) for vals in categoria_niveles.values()]
    
# Datos para gráfico de puntos
    categorias = categorias
    madurez_actual = promedios
    y_pos = np.arange(len(categorias))

# Paleta tipo tab10 (colores suaves distintos por categoría)
    colormap = cm.get_cmap('tab10', len(categorias))
    colores = [mcolors.to_hex(colormap(i)) for i in range(len(categorias))]

# Crear gráfico
    fig, ax = plt.subplots(figsize=(14, 8))

#Dibujar puntos de madurez
    for i, (x, y) in enumerate(zip(madurez_actual, y_pos)):
        ax.scatter(x, y, s=150, color=colores[i], zorder=3)


## Formato de ejes y etiquetas
    ax.set_yticks(y_pos)
    ax.set_yticklabels(categorias, fontsize=12, fontweight='bold')
    ax.set_xlim(0.5, 5.5)
    ax.invert_yaxis()

# Título principal del gráfico
    fig.suptitle("Evaluación de Madurez: Capacidades del Motor de Decisiones", fontsize=14, weight="bold", y=1.08)

# Etiquetas de niveles y números (dibujados sobre la figura)
    etiquetas_x = ["Primer cuartil", "Segundo cuartil", "Tercer cuartil", "Último cuartil", "Líder del mercado"]
    for i, label in enumerate(etiquetas_x, start=1):
        ax.text(i, -1.5, str(i), ha='center', va='center', fontsize=12, fontweight='bold',
            bbox=dict(facecolor='lightgray', edgecolor='gray', boxstyle='circle'))
        ax.text(i, -0.8, label, ha='center', va='top', fontsize=12, fontweight='bold')

# Grillas
    ax.grid(axis='x', linestyle='--', alpha=0.5, zorder=1)
    ax.grid(axis='y', linestyle=':', alpha=0.3)

# Quitar ticks innecesarios
    ax.tick_params(axis='x', bottom=False, labelbottom=False)

# Layout
    plt.tight_layout(rect=[0, 0.05, 1, 0.92])

# Guardar gráfico
    os.makedirs("graficos", exist_ok=True)
    grafico_path = "graficos/resumen_categorias.png"
    plt.savefig(grafico_path)
    plt.close()

    # --- CREAR PDF ---
    class PDF(FPDF):
        def header(self):
            self.image("logo.png", x=10, y=8, w=30)  # x/y = posición en mm, w = ancho del logo
            if hasattr(self, "dejavu"):
                self.set_font("DejaVu", "B", 14)
            else:
                self.set_font("Arial", "B", 14)
            self.cell(0, 10, "Reporte de Evaluación de Madurez de Motor de Decisión", ln=True, align="C")

            if hasattr(self, "dejavu"):
                self.set_font("DejaVu", "", 10)
            else:
                self.set_font("Arial", "", 10)
            self.cell(0, 10, f"Usuario: {nombre_usuario} | Empresa: {nombre_empresa} | Email: {nombre_email} | Fecha: {fecha_actual}", ln=True, align="C")
            self.ln(10)

        def chapter_title(self, title):
            if hasattr(self, "dejavu"):
                self.set_font("DejaVu", "B", 12)
            else:
                self.set_font("Arial", "B", 12)
            self.cell(0, 10, title, ln=True)
            self.ln(2)

        def chapter_body(self, body):
            if hasattr(self, "dejavu"):
                self.set_font("DejaVu", "", 11)
            else:
                self.set_font("Arial", "", 11)
            self.multi_cell(0, 10, body)
            self.ln()
    
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=5)
    
    # Agregar fuente Unicode
    pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
    pdf.add_font("DejaVu", "B", "DejaVuSans.ttf", uni=True)
    pdf.dejavu = True
   
    # Insertar gráfico
    pdf.chapter_title("Gráfico de Madurez por Categoría")
    pdf.image(grafico_path, w=180)
    pdf.ln(10)

    # Resumen por Categoría (formato tabla)
    pdf.chapter_title("Resumen por Categoría (Nivel Promedio)")

    # Encabezado de la tabla
    pdf.set_font("Arial", "B", 10)
    pdf.cell(120, 10, "Categoría", border=1)
    pdf.cell(40, 10, "Nivel Promedio", border=1, ln=True)

    # Filas de datos
    pdf.set_font("Arial", "", 9)
    for categoria, niveles in categoria_niveles.items():
        promedio = sum(niveles) / len(niveles)
        pdf.cell(120, 10, categoria, border=1)
        pdf.cell(40, 10, f"{promedio:.2f}", border=1, ln=True)

    pdf.ln(10)  # Espacio debajo de la tabla
    pdf.add_page() #Separa la sección de resultados individuales
    pdf.chapter_title("Resultados Individuales por Variable")

    descripcion_dict = {item["variable"]: item["descripcion"] for item in preguntas}
    opciones_dict = {item["variable"]: item["opciones"] for item in preguntas}

    for variable, puntaje in resultados_finales.items():
        descripcion = descripcion_dict.get(variable, "")
        opciones = opciones_dict.get(variable, [])
        nivel_obtenido = int(round(puntaje))
        nivel_obtenido = max(1, min(nivel_obtenido, len(opciones)))
        detalle_nivel = opciones[nivel_obtenido - 1] if opciones else "Sin detalle de nivel disponible."
        pdf.chapter_title(variable)
        pdf.chapter_body(
            f"{descripcion}\n\n"
            f"Nivel obtenido: {nivel_obtenido} (puntaje {puntaje:.2f})\n\n"
            f"Detalle del nivel: {detalle_nivel}"
        )

    os.makedirs("resultados_pdf", exist_ok=True)
    nombre_archivo = f"reporte_madurez_{nombre_usuario}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    ruta_pdf = f"resultados_pdf/{nombre_archivo}"
    pdf.output(ruta_pdf)

    st.success("✅ Respuestas guardadas correctamente.")
    st.download_button("📄 Descargar PDF", data=open(ruta_pdf, "rb"), file_name=nombre_archivo)