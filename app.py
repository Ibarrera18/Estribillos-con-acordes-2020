import streamlit as st
import pdfplumber
import re

# --- 1. CONFIGURACIÓN Y CONSTANTES ---
ESCALA = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
BEMOLES = {'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#'}

# Palabras que el evaluador ignorará para no descartar una línea de acordes
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
        
        if palabra_lower in ETIQUETAS_ESTRUCTURA or palabra_limpia in simbolos:
            continue
            
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
            
        if not patron_acorde.match(palabra_core):
            return False
            
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
        
        if patron_acorde.match(parte_core):
            es_acorde = True
        elif '-' in parte_core:
            fragmentos = parte_core.replace('(', '').replace(')', '').split('-')
            if all(patron_acorde.match(f) for f in fragmentos if f):
                es_acorde = True
                
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
        else:
            linea_nueva += parte
            
    return linea_nueva

# --- 2. EXTRACCIÓN DE DATOS ---
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
                    if cancion_actual:
                        cancion_actual["tono_original"] = linea_limpia.replace("TONO:", "").strip()
                elif cancion_actual is not None:
                    if es_linea_de_acordes(linea_limpia):
                        cancion_actual["versos"].append({"tipo": "acordes", "texto": linea.rstrip()})
                    else:
                        cancion_actual["versos"].append({"tipo": "letra", "texto": linea.rstrip()})
                        
        if cancion_actual: canciones.append(cancion_actual)
    return canciones

# --- 3. INTERFAZ GRÁFICA DE STREAMLIT ---
st.set_page_config(page_title="ESTRIBILLOS CON ACORDES", page_icon="🎶", layout="wide")
st.title("ESTRIBILLOS CON ACORDES")

canciones = cargar_cancionero('ESTRIBILLOS CON ACORDES 2020.pdf')

if not canciones:
    st.warning("No se encontraron canciones. Verifica que el archivo PDF esté en la misma carpeta.")
else:
    nombres_canciones = [c["titulo"] for c in canciones]
    busqueda = st.text_input("🔍 Buscar canto por número o nombre:", "")
    nombres_filtrados = [nombre for nombre in nombres_canciones if busqueda.lower() in nombre.lower()]
    
    if not nombres_filtrados:
        st.error("No se encontró ningún canto con ese nombre o número.")
    else:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            cancion_seleccionada = st.selectbox("Selecciona un canto:", nombres_filtrados)
            cancion = next(c for c in canciones if c["titulo"] == cancion_seleccionada)
            st.markdown(f"**Tono Original:** `{cancion['tono_original']}`")
            tono_base_original = obtener_tono_base(cancion['tono_original'])
            
        with col2:
            st.markdown("**Ajustes de Transposición**")
            modo_transposicion = st.radio("Método:", ["Por Tono Destino", "Por Semitonos"], horizontal=True)
            
            if modo_transposicion == "Por Tono Destino":
                idx_actual = ESCALA.index(tono_base_original) if tono_base_original in ESCALA else 0
                tono_destino = st.selectbox("¿En qué tono lo quieres tocar?", ESCALA, index=idx_actual)
                semitonos = (ESCALA.index(tono_destino) - idx_actual) % 12
            else:
                semitonos = st.number_input("Cantidad de semitonos (Capo):", min_value=-12, max_value=12, value=0, step=1)
                
            st.markdown("**Ajustes Visuales**")
            tamano_letra = st.slider("Tamaño del texto:", min_value=12, max_value=40, value=18, step=2)
                
        st.divider() 
        
        texto_final_html = f"<div style='font-family: Consolas, \"Courier New\", monospace; font-size: {tamano_letra}px; line-height: 1.6;'>"
        patron_acorde_puro = re.compile(r'^[A-G][#b]?(m|Maj|maj|M|dim|dis|aug|aum|sus|add)?\d*(/[A-G][#b]?)?$')
        
        for i, verso in enumerate(cancion["versos"]):
            texto_upper = verso["texto"].lstrip().upper()
            es_inicio_seccion = any(texto_upper.startswith(etq.upper()) for etq in ["INTRO", "CORO", "PUENTE", "ESTROFA", "FINAL"])
            
            if es_inicio_seccion and i > 0:
                texto_final_html += "<br><br>"
            
            if verso["tipo"] == "acordes":
                if not es_inicio_seccion and i > 0:
                    texto_final_html += "<br>" 
                    
                nueva_linea = transponer_linea(verso["texto"], semitonos)
                partes = re.split(r'(\s+)', nueva_linea)
                linea_resaltada = ""
                
                for parte in partes:
                    if not parte: continue
                    if parte.isspace():
                        linea_resaltada += parte.replace(" ", "&nbsp;")
                    else:
                        parte_limpia = re.sub(r'[\(\)\[\]\.,:]', '', parte)
                        parte_limpia = re.sub(r'^(?:/{2,3}|\|+)+', '', parte_limpia)
                        parte_limpia = re.sub(r'(?:/{2,3}|\|+)+$', '', parte_limpia)
                        
                        es_acorde_real = False
                        if patron_acorde_puro.match(parte_limpia):
                            es_acorde_real = True
                        elif '-' in parte_limpia:
                            if all(patron_acorde_puro.match(f) for f in parte_limpia.split('-') if f):
                                es_acorde_real = True
                                
                        if es_acorde_real:
                            linea_resaltada += f'<span style="background-color: #fcfc99; color: #000; border-radius: 3px;">{parte}</span>'
                        elif parte_limpia.lower() in ETIQUETAS_ESTRUCTURA:
                            linea_resaltada += f'<span style="color: #2196f3; font-weight: bold;">{parte}</span>'
                        else:
                            linea_resaltada += parte
                            
                texto_final_html += linea_resaltada + "<br>"
            else:
                texto_final_html += verso["texto"].replace(" ", "&nbsp;") + "<br>"
                
        texto_final_html += "</div>"
        st.markdown(texto_final_html, unsafe_allow_html=True)