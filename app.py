import streamlit as st
import pdfplumber
import re

# --- 1. CONFIGURACIÓN Y CONSTANTES ---
ESCALA = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
BEMOLES = {'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#'}
ETIQUETAS_ESTRUCTURA = ['intro', 'coro', 'puente', 'final', 'estrofa', 'sigue', 'notas', 'del', 'al', 'fin', 'vuelta']

def obtener_tono_base(tono_str):
    if not tono_str: return 'C' 
    match = re.search(r'[A-G][#b]?', tono_str)
    if match:
        nota = match.group(0)
        return BEMOLES.get(nota, nota)
    return 'C'

def es_linea_de_acordes(linea):
    linea_sin_parentesis = re.sub(r'\([^)]*\)', '', linea)
    palabras = linea_sin_parentesis.strip().split()
    if not palabras:
        linea_sin_parentesis = linea.replace('(', '').replace(')', '')
        palabras = linea_sin_parentesis.strip().split()
    if not palabras: return False
    simbolos = ['//', '///', '|', '||', '-', '[:', ':]']
    patron_acorde = re.compile(r'^[A-G][#b]?(m|Maj|maj|M|dim|dis|aug|aum|sus|add)?\d*(/[A-G][#b]?)?$')
    for palabra in palabras:
        palabra_limpia = re.sub(r'[\.,:]+$', '', palabra)
        palabra_lower = palabra_limpia.lower()
        if palabra_lower in ETIQUETAS_ESTRUCTURA or palabra_limpia in simbolos: continue
        palabra_core = re.sub(r'^(?:/{2,3}|\|+|\[:|\[)+', '', palabra_limpia)
        palabra_core = re.sub(r'(?:/{2,3}|\|+|:\]|\])+$', '', palabra_core)
        if not palabra_core: continue
        if '-' in palabra_core and len(palabra_core) > 1:
            sub_acordes = palabra_core.split('-')
            valido = True
            for sub in sub_acordes:
                if not sub: continue
                if not patron_acorde.match(sub) and sub not in simbolos:
                    valido = False
                    break
            if valido: continue
            return False
        if not patron_acorde.match(palabra_core): return False
    return True

def transponer_linea(linea, semitonos):
    partes = re.split(r'(\s+)', linea)
    linea_nueva = ""
    patron_acorde = re.compile(r'^[\(\[]?[A-G][#b]?(m|Maj|maj|M|dim|dis|aug|aum|sus|add)?\d*(/[A-G][#b]?)?[\)\]\.,:]?$')
    for parte in partes:
        if not parte or parte.isspace():
            linea_nueva += parte
            continue
        es_acorde = False
        parte_core = re.sub(r'^(?:/{2,3}|\|+|\[:|\[)+', '', parte)
        parte_core = re.sub(r'(?:/{2,3}|\|+|:\]|\])+$', '', parte_core)
        if patron_acorde.match(parte_core): es_acorde = True
        elif '-' in parte_core:
            fragmentos = parte_core.replace('(', '').replace(')', '').split('-')
            if all(patron_acorde.match(f) for f in fragmentos if f): es_acorde = True
        if es_acorde:
            def cambiar_nota(m):
                nota = m.group(0)
                if nota in BEMOLES: nota = BEMOLES[nota]
                if nota in ESCALA:
                    idx = (ESCALA.index(nota) + semitonos) % 12
                    return ESCALA[idx]
                return nota
            parte_transpuesta = re.sub(r'(?:^|(?<=[\/\-\(\[\|:]))[A-G][#b]?', cambiar_nota, parte)
            linea_nueva += parte_transpuesta
        else: linea_nueva += parte
    return linea_nueva

@st.cache_data
def cargar_cancionero(ruta_pdf):
    canciones = []
    cancion_actual = None
    with pdfplumber.open(ruta_pdf) as pdf:
        for pagina in pdf.pages[1:]: 
            texto = pagina.extract_text(layout=True)
            if not texto: continue
            lineas = texto.split('\n')
            for linea in lineas:
                patron_bajo = r'([A-G][#b]?(?:m|Maj|maj|M|dim|dis|aug|aum|sus|add)?\d*)\s*/\s*([A-G][#b]?)'
                linea = re.sub(patron_bajo, r'\1/\2', linea)
                linea_limpia = linea.strip()
                if not linea_limpia: continue
                if re.match(r'^\d+[\.\-]?\s', linea_limpia):
                    if cancion_actual: canciones.append(cancion_actual)
                    cancion_actual = {"titulo": linea_limpia, "tono_original": "", "versos": []}
                elif linea_limpia.startswith("TONO:"):
                    if cancion_actual: cancion_actual["tono_original"] = linea_limpia.replace("TONO:", "").strip()
                elif cancion_actual is not None:
                    if es_linea_de_acordes(linea_limpia): cancion_actual["versos"].append({"tipo": "acordes", "texto": linea.rstrip()})
                    else: cancion_actual["versos"].append({"tipo": "letra", "texto": linea.rstrip()})
        if cancion_actual: canciones.append(cancion_actual)
    return canciones

# --- 2. INTERFAZ GRÁFICA ---
st.set_page_config(page_title="ESTRIBILLOS CON ACORDES", page_icon="🎶", layout="wide")

st.title("ESTRIBILLOS CON ACORDES")
canciones = cargar_cancionero('ESTRIBILLOS CON ACORDES 2020.pdf')

if not canciones:
    st.warning("No se encontró el archivo PDF.")
    st.stop()

# --- BUSCADOR Y SELECCIÓN ---
busqueda = st.text_input("🔍 Buscar canto (número o nombre):", "")
nombres_filtrados = [n["titulo"] for n in canciones if busqueda.lower() in n["titulo"].lower()]

if not nombres_filtrados:
    st.error("No hay resultados para tu búsqueda.")
    st.stop()

col1, col2 = st.columns([2, 1])
with col1:
    sel = st.selectbox("Selecciona el canto:", nombres_filtrados)
    cancion = next(c for c in canciones if c["titulo"] == sel)
    st.write(f"**Tono Original:** {cancion['tono_original']}")
    t_base = obtener_tono_base(cancion['tono_original'])

with col2:
    st.write("**Transposición**")
    modo = st.radio("Método:", ["Tono Destino", "Semitonos"], horizontal=True)
    if modo == "Tono Destino":
        idx = ESCALA.index(t_base) if t_base in ESCALA else 0
        t_dest = st.selectbox("Tocar en:", ESCALA, index=idx)
        semitonos = (ESCALA.index(t_dest) - idx) % 12
    else:
        semitonos = st.number_input("Semitonos (Capo):", -12, 12, 0)

    st.write("**Visualización**")
    c_v1, c_v2 = st.columns(2)
    tamano = c_v1.slider("Tamaño de letra:", 12, 40, 18)
    modo_vista = c_v2.radio("Modo de lectura:", ["Vertical", "Horizontal"], horizontal=True)

st.divider()

# --- DESPLIEGUE DEL CANTO ---
num_cols = 1 if modo_vista == "Vertical" else 2
estilo_cols = f"column-count: {num_cols}; column-gap: 50px;" if num_cols > 1 else ""

html_canto = f"""
<div style='font-family: Consolas, monospace; font-size: {tamano}px; line-height: 1.6; {estilo_cols}'>
    <h2 style='column-span: all; margin-top: 0;'>{cancion['titulo']}</h2>
"""

patron_puro = re.compile(r'^[A-G][#b]?(m|Maj|maj|M|dim|dis|aug|aum|sus|add)?\d*(/[A-G][#b]?)?$')

for i, verso in enumerate(cancion["versos"]):
    u = verso["texto"].lstrip().upper()
    if any(u.startswith(e) for e in ["INTRO", "CORO", "PUENTE", "ESTROFA", "FINAL"]) and i > 0:
        html_canto += "<br><br>"
    
    if verso["tipo"] == "acordes":
        if i > 0: html_canto += "<br>"
        nl = transponer_linea(verso["texto"], semitonos)
        for p in re.split(r'(\s+)', nl):
            if not p: continue
            if p.isspace(): html_canto += p.replace(" ", "&nbsp;")
            else:
                pl = re.sub(r'[\(\)\[\]\.,:]', '', p)
                pl = re.sub(r'^(?:/{2,3}|\|+)+', '', pl)
                pl = re.sub(r'(?:/{2,3}|\|+)+$', '', pl)
                if patron_puro.match(pl) or ('-' in pl and all(patron_puro.match(f) for f in pl.split('-') if f)):
                    html_canto += f'<span style="background-color: #fcfc99; color: black; border-radius: 3px;">{p}</span>'
                elif pl.lower() in ETIQUETAS_ESTRUCTURA:
                    html_canto += f'<span style="color: #2196f3; font-weight: bold;">{p}</span>'
                else: html_canto += p
        html_canto += "<br>"
    else:
        html_canto += verso["texto"].replace(" ", "&nbsp;") + "<br>"

html_canto += "</div>"
st.markdown(html_canto, unsafe_allow_html=True)