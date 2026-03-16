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

# --- 3. INTERFAZ GRÁFICA DE STREAMLIT ---
st.set_page_config(page_title="ESTRIBILLOS CON ACORDES", page_icon="🎶", layout="wide")

# CSS REFORZADO PARA ELIMINAR CUALQUIER RASTRO DE CONTROLES EN IMPRESIÓN
css_impresion = """
<style>
@media print {
    /* 1. Ocultamos TODA la estructura de Streamlit */
    [data-testid="stHeader"], 
    [data-testid="stSidebar"], 
    footer, 
    header, 
    .no-print,
    [data-testid="stVerticalBlock"] > div:not(.printable-content) {
        display: none !important;
    }

    /* 2. Forzamos que el contenido imprimible empiece hasta arriba */
    .printable-content {
        display: block !important;
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* 3. Limpieza de página */
    @page { margin: 1.5cm; size: auto; }
    body, .stApp { background-color: white !important; }
    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
}
</style>
"""
st.markdown(css_impresion, unsafe_allow_html=True)

# TODO ESTE BLOQUE SE OCULTARÁ EN LA IMPRESIÓN
with st.container():
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    st.title("ESTRIBILLOS CON ACORDES")
    canciones = cargar_cancionero('ESTRIBILLOS CON ACORDES 2020.pdf')

    if not canciones:
        st.warning("No se encontraron canciones.")
        st.stop()

    nombres_canciones = [c["titulo"] for c in canciones]
    busqueda = st.text_input("🔍 Buscar canto por número o nombre:", "")
    nombres_filtrados = [nombre for nombre in nombres_canciones if busqueda.lower() in nombre.lower()]
    
    if not nombres_filtrados:
        st.error("No se encontró nada.")
        st.stop()

    col1, col2 = st.columns([2, 1])
    with col1:
        cancion_seleccionada = st.selectbox("Selecciona un canto:", nombres_filtrados)
        cancion = next(c for c in canciones if c["titulo"] == cancion_seleccionada)
        st.write(f"**Tono Original:** {cancion['tono_original']}")
        tono_base_original = obtener_tono_base(cancion['tono_original'])
        
    with col2:
        st.write("**Ajustes de Transposición**")
        modo = st.radio("Método:", ["Tono", "Semitonos"], horizontal=True)
        if modo == "Tono":
            idx = ESCALA.index(tono_base_original) if tono_base_original in ESCALA else 0
            t_dest = st.selectbox("Tono destino:", ESCALA, index=idx)
            semitonos = (ESCALA.index(t_dest) - idx) % 12
        else:
            semitonos = st.number_input("Semitonos:", -12, 12, 0)
            
        st.write("**Visualización**")
        c1, c2 = st.columns(2)
        tamano = c1.slider("Tamaño de letra:", 12, 40, 18)
        modo_vista = c2.radio("Modo de lectura:", ["Vertical", "Horizontal"], index=0, horizontal=True)
        num_columnas = 1 if modo_vista == "Vertical" else 2

    st.divider()
    
    components.html(
        """<script>function imprimir(){window.parent.print();}</script>
        <div style="text-align: right;"><button onclick="imprimir()" style="background-color: #2196f3; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold;">🖨️ Imprimir Canto</button></div>""",
        height=50
    )
    st.markdown('</div>', unsafe_allow_html=True)

# ESTE ES EL BLOQUE QUE SÍ SE IMPRIMIRÁ (Clase: printable-content)
estilo_columnas = f"column-count: {num_columnas}; column-gap: 50px;" if num_columnas > 1 else ""
texto_html = f"<div class='printable-content' style='font-family: Consolas, monospace; font-size: {tamano}px; line-height: 1.6; {estilo_columnas}'>"
texto_html += f"<h1 style='column-span: all; margin-top: 0; padding-top: 0;'>{cancion['titulo']}</h1>"

patron_puro = re.compile(r'^[A-G][#b]?(m|Maj|maj|M|dim|dis|aug|aum|sus|add)?\d*(/[A-G][#b]?)?$')
for i, verso in enumerate(cancion["versos"]):
    u = verso["texto"].lstrip().upper()
    if any(u.startswith(e) for e in ["INTRO", "CORO", "PUENTE", "ESTROFA", "FINAL"]) and i > 0:
        texto_html += "<br><br>"
    if verso["tipo"] == "acordes":
        if i > 0: texto_html += "<br>" 
        nl = transponer_linea(verso["texto"], semitonos)
        for p in re.split(r'(\s+)', nl):
            if not p: continue
            if p.isspace(): texto_html += p.replace(" ", "&nbsp;")
            else:
                pl = re.sub(r'[\(\)\[\]\.,:]', '', p)
                pl = re.sub(r'^(?:/{2,3}|\|+)+', '', pl)
                pl = re.sub(r'(?:/{2,3}|\|+)+$', '', pl)
                if patron_puro.match(pl) or ('-' in pl and all(patron_puro.match(f) for f in pl.split('-') if f)):
                    texto_html += f'<span style="background-color: #fcfc99; color: black; border-radius: 3px;">{p}</span>'
                elif pl.lower() in ETIQUETAS_ESTRUCTURA:
                    texto_html += f'<span style="color: #2196f3; font-weight: bold;">{p}</span>'
                else: texto_html += p
        texto_html += "<br>"
    else: texto_html += verso["texto"].replace(" ", "&nbsp;") + "<br>"

texto_html += "</div>"
st.markdown(texto_html, unsafe_allow_html=True)