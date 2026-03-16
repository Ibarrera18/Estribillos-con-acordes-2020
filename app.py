import streamlit as st
import pdfplumber
import re

# --- 1. CONFIGURACIÓN Y CONSTANTES ---
ESCALA = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
BEMOLES = {'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#'}

def es_linea_de_acordes(linea):
    palabras = linea.strip().split()
    if not palabras: return False
    
    # Símbolos estructurales que usan los músicos
    simbolos = ['//', '///', '|', '||', '-', '[:', ':]']
    
    # Patrón a prueba de balas: acepta sus4, add9, m(b5), etc.
    patron_acorde = re.compile(r'^[A-G][#b]?(m|Maj|maj|M|dim|aug|sus|add)?\d*(/[A-G][#b]?)?(\([^)]+\))?$')
    
    for palabra in palabras:
        if palabra in simbolos:
            continue
            
        # Si hay guiones uniendo acordes (ej. G-D), los separamos para evaluarlos
        if '-' in palabra and len(palabra) > 1:
            sub_acordes = palabra.split('-')
            valido = True
            for sub in sub_acordes:
                if not sub: continue
                if not patron_acorde.match(sub) and sub not in simbolos:
                    valido = False
                    break
            if valido:
                continue
            return False
            
        if not patron_acorde.match(palabra):
            return False
    return True

def transponer_linea(linea, semitonos):
    def cambiar_nota(match):
        nota = match.group(0)
        if nota in BEMOLES: nota = BEMOLES[nota]
        if nota in ESCALA:
            indice_actual = ESCALA.index(nota)
            nuevo_indice = (indice_actual + semitonos) % 12
            return ESCALA[nuevo_indice]
        return nota
        
    # Regex ultrasensible: solo transpone letras A-G si están al inicio, o después de un espacio, /, -, ( o [
    return re.sub(r'(?:^|(?<=[\s/\-\(\[]))[A-G][#b]?', cambiar_nota, linea)

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
                linea_limpia = linea.strip()
                if not linea_limpia: continue
                
                # Tolerancia por si algún canto no tiene el punto después del número
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
st.set_page_config(page_title="Cancionero Dinámico", page_icon="🎶", layout="centered")
st.title("🎶 Cancionero Dinámico")

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
        col1, col2 = st.columns([3, 1])
        with col1:
            cancion_seleccionada = st.selectbox("Selecciona un canto:", nombres_filtrados)
        with col2:
            semitonos = st.number_input("Transponer (semitonos):", min_value=-12, max_value=12, value=0, step=1)
            
        cancion = next(c for c in canciones if c["titulo"] == cancion_seleccionada)
        
        st.markdown(f"**Tono Original:** `{cancion['tono_original']}`")
        st.divider() 
        
        texto_final_html = "<div style='font-family: \"Courier New\", Courier, monospace; font-size: 16px; line-height: 1.5;'>"
        
        for i, verso in enumerate(cancion["versos"]):
            if verso["tipo"] == "acordes":
                if i > 0 and cancion["versos"][i-1]["tipo"] == "letra":
                    texto_final_html += "<br>" 
                    
                nueva_linea = transponer_linea(verso["texto"], semitonos)
                
                partes = re.split(r'(\s+)', nueva_linea)
                linea_resaltada = ""
                
                for parte in partes:
                    if not parte: continue
                    if parte.isspace():
                        linea_resaltada += parte.replace(" ", "&nbsp;")
                    else:
                        linea_resaltada += f'<span style="background-color: #fcfc99; color: #000; border-radius: 3px;">{parte}</span>'
                
                texto_final_html += linea_resaltada + "<br>"
            else:
                texto_final_html += verso["texto"].replace(" ", "&nbsp;") + "<br>"
                
        texto_final_html += "</div>"
        st.markdown(texto_final_html, unsafe_allow_html=True)