import streamlit as st
import pdfplumber
import re
import streamlit.components.v1 as components

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

# --- 3. INTERFAZ GRÁFICA ---
st.set_page_config(page_title="ESTRIBILLOS CON ACORDES", page_icon="🎶", layout="wide")

# CSS SEGURO PARA IMPRESIÓN
st.markdown("""
<style>
@media print {
    /* Ocultar todo lo que no sea el área del canto */
    .no-print, header, footer, [data-testid="stHeader"], [data-testid="stSidebar"] {
        display: none !important;
    }
    .stApp { background-color: white !important; }
    @page { margin: 1cm; }
}
</style>
""", unsafe_allow_html=True)

# --- ÁREA DE CONTROLES (NO SE IMPRIME) ---
st.markdown('<div class="no-print">', unsafe_allow_html=True)
st.title("ESTRIBILLOS CON ACORDES")
canciones = cargar_cancionero('ESTRIBILLOS CON ACORDES 2020.pdf')

if not canciones:
    st.warning("No se encontraron canciones.")
    st.stop()

busqueda = st.text_input("🔍 Buscar canto:", "")
nombres_filtrados = [n["titulo"] for n in canciones if busqueda.lower() in n["titulo"].lower()]

if not nombres_filtrados:
    st.error("No hay resultados.")
    st.stop()

col1, col2 = st.columns([2, 1])
with col1:
    sel = st.selectbox("Canto:", nombres_filtrados)
    cancion = next(c for c in canciones if c["titulo"] == sel)
    st.write(f"Tono Original: {cancion['tono_original']}")
    t_base = obtener_tono_base(cancion['tono_original'])

with col2:
    modo = st.radio("Transponer:", ["Tono", "Semitonos"], horizontal=True)
    if modo == "Tono":
        idx = ESCALA.index(t_base) if t_base in ESCALA else 0
        t_dest = st.selectbox("Destino:", ESCALA, index=idx)
        semitonos = (ESCALA.index(t_dest) - idx) % 12
        tono_actual_nombre = t_dest
    else:
        semitonos = st.number_input("Semitonos:", -12, 12, 0)
        # Calcular nombre del tono actual para la impresión
        idx_org = ESCALA.index(t_base) if t_base in ESCALA else 0
        tono_actual_nombre = ESCALA[(idx_org + semitonos) % 12]

    c_v1, c_v2 = st.columns(2)
    tamano = c_v1.slider("Tamaño:", 12, 40, 18)
    modo_vista = c_v2.radio("Vista:", ["Vertical", "Horizontal"], horizontal=True)

st.divider()

components.html("""
    <script>function imprimir(){window.parent.print();}</script>
    <div style="text-align: right;"><button onclick="imprimir()" style="background-color: #2196f3; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold;">🖨️ Imprimir Canto</button></div>
""", height=50)
st.markdown('</div>', unsafe_allow_html=True)

# --- ÁREA DEL CANTO (SÍ SE IMPRIME) ---
num_cols = 1 if modo_vista == "Vertical" else 2
estilo_cols = f"column-count: {num_cols}; column-gap: 40px;" if num_cols > 1 else ""

# Armamos el HTML
html_final = f"""
<div style='font-family: Consolas, monospace; font-size: {tamano}px; line-height: 1.5; color: black; {estilo_cols}'>
    <h1 style='column-span: all; margin: 0;'>{cancion['titulo']}</h1>
    <p style='column-span: all; margin-bottom: 20px;'><strong>Tono: {tono_actual_nombre}</strong></p>
"""

patron_puro = re.compile(r'^[A-G][#b]?(m|Maj|maj|M|dim|dis|aug|aum|sus|add)?\d*(/[A-G][#b]?)?$')

for i, verso in enumerate(cancion["versos"]):
    u = verso["texto"].lstrip().upper()
    if any(u.startswith(e) for e in ["INTRO", "CORO", "PUENTE", "ESTROFA", "FINAL"]) and i > 0:
        html_final += "<br><br>"
    
    if verso["tipo"] == "acordes":
        if i > 0: html_final += "<br>"
        nl = transponer_linea(verso["texto"], semitonos)
        for p in re.split(r'(\s+)', nl):
            if not p: continue
            if p.isspace(): html_final += p.replace(" ", "&nbsp;")
            else:
                pl = re.sub(r'[\(\)\[\]\.,:]', '', p)
                pl = re.sub(r'^(?:/{2,3}|\|+)+', '', pl)
                pl = re.sub(r'(?:/{2,3}|\|+)+$', '', pl)
                if patron_puro.match(pl) or ('-' in pl and all(patron_puro.match(f) for f in pl.split('-') if f)):
                    html_final += f'<span style="background-color: #fcfc99; color: black; border-radius: 3px;">{p}</span>'
                elif pl.lower() in ETIQUETAS_ESTRUCTURA:
                    html_final += f'<span style="color: #2196f3; font-weight: bold;">{p}</span>'
                else: html_final += p
        html_final += "<br>"
    else:
        html_final += verso["texto"].replace(" ", "&nbsp;") + "<br>"

html_final += "</div>"
st.markdown(html_final, unsafe_allow_html=True)