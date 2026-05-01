import streamlit as st
import pdfplumber
import re

# ─────────────────────────────────────────────
#  CONSTANTES
# ─────────────────────────────────────────────
ESCALA   = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
BEMOLES  = {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}
ETIQUETAS = ['intro','coro','puente','final','estrofa','sigue','notas',
             'del','al','fin','vuelta']
NOMBRE_PDF = 'ESTRIBILLOS CON ACORDES 2020.pdf'

# Nombre de notas "prettier" para mostrar en UI
NOTAS_UI = {
    'C':'C','C#':'C#','D':'D','D#':'D#','E':'E',
    'F':'F','F#':'F#','G':'G','G#':'G#','A':'A',
    'A#':'A#','B':'B'
}

# ─────────────────────────────────────────────
#  LÓGICA MUSICAL
# ─────────────────────────────────────────────
def normalizar_nota(nota):
    return BEMOLES.get(nota, nota)

def obtener_tono_base(tono_str):
    if not tono_str:
        return 'C'
    m = re.search(r'[A-G][#b]?', tono_str)
    if m:
        return normalizar_nota(m.group(0))
    return 'C'

def es_linea_de_acordes(linea):
    linea_sin_par = re.sub(r'\([^)]*\)', '', linea)
    palabras = linea_sin_par.strip().split()
    if not palabras:
        palabras = linea.replace('(','').replace(')','').strip().split()
    if not palabras:
        return False
    simbolos  = ['//', '///', '|', '||', '-', '[:', ':]']
    patron    = re.compile(
        r'^[A-G][#b]?(m|Maj|maj|M|dim|dis|aug|aum|sus|add)?\d*(/[A-G][#b]?)?$'
    )
    for p in palabras:
        pl = re.sub(r'[\.,:]+$', '', p).lower()
        if pl in ETIQUETAS or p in simbolos:
            continue
        core = re.sub(r'^(?:/{2,3}|\|+|\[:|\[)+', '', p)
        core = re.sub(r'(?:/{2,3}|\|+|:\]|\])+$', '', core)
        if not core:
            continue
        if '-' in core and len(core) > 1:
            subs  = core.split('-')
            valid = all(patron.match(s) or not s for s in subs)
            if valid:
                continue
            return False
        if not patron.match(core):
            return False
    return True

def transponer_linea(linea, semitonos):
    if semitonos == 0:
        return linea
    partes     = re.split(r'(\s+)', linea)
    patron     = re.compile(
        r'^[\(\[]?[A-G][#b]?(m|Maj|maj|M|dim|dis|aug|aum|sus|add)?\d*(/[A-G][#b]?)?[\)\]\.,:]?$'
    )
    resultado  = ''
    for parte in partes:
        if not parte or parte.isspace():
            resultado += parte
            continue
        core = re.sub(r'^(?:/{2,3}|\|+|\[:|\[)+', '', parte)
        core = re.sub(r'(?:/{2,3}|\|+|:\]|\])+$', '', core)
        es   = patron.match(core)
        if not es and '-' in core:
            frags = core.replace('(','').replace(')','').split('-')
            es    = all(patron.match(f) for f in frags if f)
        if es:
            def cambiar(m):
                n = normalizar_nota(m.group(0))
                if n in ESCALA:
                    return ESCALA[(ESCALA.index(n) + semitonos) % 12]
                return n
            resultado += re.sub(r'(?:^|(?<=[\/\-\(\[\|:]))[A-G][#b]?', cambiar, parte)
        else:
            resultado += parte
    return resultado

# ─────────────────────────────────────────────
#  CARGA DEL PDF
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def cargar_cancionero(ruta):
    canciones     = []
    cancion_actual = None
    patron_bajo   = r'([A-G][#b]?(?:m|Maj|maj|M|dim|dis|aug|aum|sus|add)?\d*)\s*/\s*([A-G][#b]?)'
    with pdfplumber.open(ruta) as pdf:
        for pagina in pdf.pages[1:]:
            texto = pagina.extract_text(layout=True)
            if not texto:
                continue
            for linea in texto.split('\n'):
                linea       = re.sub(patron_bajo, r'\1/\2', linea)
                linea_limpia = linea.strip()
                if not linea_limpia:
                    continue
                if re.match(r'^\d+[\.\-]?\s', linea_limpia):
                    if cancion_actual:
                        canciones.append(cancion_actual)
                    cancion_actual = {
                        'titulo'  : linea_limpia,
                        'tono'    : '',
                        'versos'  : []
                    }
                elif linea_limpia.startswith('TONO:') and cancion_actual:
                    cancion_actual['tono'] = linea_limpia.replace('TONO:','').strip()
                elif cancion_actual is not None:
                    tipo = 'acordes' if es_linea_de_acordes(linea_limpia) else 'letra'
                    cancion_actual['versos'].append({
                        'tipo' : tipo,
                        'texto': linea.rstrip()
                    })
        if cancion_actual:
            canciones.append(cancion_actual)
    return canciones

# ─────────────────────────────────────────────
#  CSS GLOBAL  (diseño oscuro editorial)
# ─────────────────────────────────────────────
CSS = """
<style>
/* ── Variables ─────────────────────────── */
:root {
    --bg          : #0d0d0f;
    --surface     : #141418;
    --surface2    : #1c1c22;
    --border      : #2a2a35;
    --accent      : #d4a843;        /* dorado ámbar */
    --accent-dim  : #8a6d28;
    --text-primary: #e8e4d8;
    --text-muted  : #6b6875;
    --chord-bg    : #2a2210;
    --chord-fg    : #f0c060;
    --label-fg    : #7cb4f0;
    --mono        : 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
    --serif       : 'EB Garamond', Georgia, serif;
}

/* ── Fondo principal ─────────────────── */
.stApp, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
}
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}

/* ── Ocultar decoración innecesaria ──── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

/* ── Tipografía base ─────────────────── */
html, body, .stApp * { color: var(--text-primary); }

/* ── Header personalizado ────────────── */
.sb-header {
    display: flex;
    align-items: baseline;
    gap: 16px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 18px;
    margin-bottom: 24px;
}
.sb-header h1 {
    font-family: var(--serif);
    font-size: 2.2rem;
    font-weight: 400;
    letter-spacing: .04em;
    color: var(--accent);
    margin: 0;
}
.sb-header span {
    font-family: var(--mono);
    font-size: .75rem;
    color: var(--text-muted);
    letter-spacing: .12em;
    text-transform: uppercase;
}

/* ── Buscador ────────────────────────── */
.stTextInput input {
    background : var(--surface2) !important;
    border     : 1px solid var(--border) !important;
    border-radius: 6px !important;
    color      : var(--text-primary) !important;
    font-family: var(--mono) !important;
    font-size  : .85rem !important;
}
.stTextInput input:focus {
    border-color: var(--accent) !important;
    box-shadow  : 0 0 0 2px rgba(212,168,67,.15) !important;
}
.stTextInput label { color: var(--text-muted) !important; font-size:.8rem !important; }

/* ── Selectbox ───────────────────────── */
.stSelectbox > div > div {
    background : var(--surface2) !important;
    border     : 1px solid var(--border) !important;
    border-radius: 6px !important;
    color      : var(--text-primary) !important;
}

/* ── Radio ───────────────────────────── */
.stRadio label { color: var(--text-muted) !important; font-size:.82rem !important; }
.stRadio [data-baseweb="radio"] input:checked + div { border-color: var(--accent) !important; }
.stRadio [data-baseweb="radio"] input:checked + div + div { color: var(--accent) !important; }

/* ── Slider ──────────────────────────── */
.stSlider [data-baseweb="slider"] > div > div > div:nth-child(1) {
    background: var(--border) !important;
}
.stSlider [data-baseweb="slider"] [role="slider"] {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
}

/* ── Number input ────────────────────── */
.stNumberInput input {
    background : var(--surface2) !important;
    border     : 1px solid var(--border) !important;
    color      : var(--text-primary) !important;
    font-family: var(--mono) !important;
}

/* ── Divider ─────────────────────────── */
hr { border-color: var(--border) !important; margin: 0 !important; }

/* ── Pill de tono ────────────────────── */
.tono-pill {
    display    : inline-block;
    padding    : 2px 10px;
    border-radius: 20px;
    background : var(--chord-bg);
    border     : 1px solid var(--accent-dim);
    color      : var(--chord-fg);
    font-family: var(--mono);
    font-size  : .82rem;
    margin-bottom: 2px;
}

/* ── Badges de stats ─────────────────── */
.stat-row { display:flex; gap:12px; margin:8px 0 20px; flex-wrap:wrap; }
.stat-badge {
    padding    : 4px 12px;
    border-radius: 4px;
    background : var(--surface2);
    border     : 1px solid var(--border);
    font-family: var(--mono);
    font-size  : .72rem;
    color      : var(--text-muted);
    letter-spacing:.06em;
}
.stat-badge b { color: var(--accent); }

/* ── Contenedor del canto ────────────── */
.canto-wrap {
    background : var(--surface);
    border     : 1px solid var(--border);
    border-radius: 10px;
    padding    : 28px 32px 36px;
    margin-top : 20px;
}

/* ── Título del canto dentro del wrap ── */
.canto-titulo {
    font-family: var(--serif);
    font-size  : 1.5rem;
    font-weight: 400;
    color      : var(--accent);
    margin-bottom: 20px;
    letter-spacing:.02em;
    border-bottom: 1px solid var(--border);
    padding-bottom: 12px;
}

/* ── Bloque par acordes+letra ────────── */
.par {
    break-inside      : avoid-column;
    page-break-inside : avoid;
    display           : block;
    margin-bottom     : 2px;
}
.par-sep { height: 14px; break-inside: avoid-column; }

/* ── Acordes e inline highlights ──────── */
.acorde {
    background   : var(--chord-bg);
    color        : var(--chord-fg);
    border-radius: 3px;
    padding      : 0 3px;
    font-weight  : 600;
}
.etiqueta {
    color      : var(--label-fg);
    font-weight: 700;
}
</style>

<!-- Google Fonts -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
"""

# ─────────────────────────────────────────────
#  RENDER DE LÍNEAS
# ─────────────────────────────────────────────
PATRON_PURO = re.compile(
    r'^[A-G][#b]?(m|Maj|maj|M|dim|dis|aug|aum|sus|add)?\d*(/[A-G][#b]?)?$'
)

def render_linea_acordes(linea, semitonos):
    linea_t = transponer_linea(linea, semitonos)
    out     = ''
    for parte in re.split(r'(\s+)', linea_t):
        if not parte:
            continue
        if parte.isspace():
            out += parte.replace(' ', '&nbsp;')
            continue
        pl = re.sub(r'[\(\)\[\]\.,:]','', parte)
        pl = re.sub(r'^(?:/{2,3}|\|+)+', '', pl)
        pl = re.sub(r'(?:/{2,3}|\|+)+$', '', pl)
        if PATRON_PURO.match(pl) or ('-' in pl and all(PATRON_PURO.match(f) for f in pl.split('-') if f)):
            out += f'<span class="acorde">{parte}</span>'
        elif pl.lower() in ETIQUETAS:
            out += f'<span class="etiqueta">{parte}</span>'
        else:
            out += parte
    return out + '<br>'

def render_linea_letra(linea):
    return linea.replace(' ','&nbsp;') + '<br>'

# ─────────────────────────────────────────────
#  APP
# ─────────────────────────────────────────────
st.set_page_config(
    page_title = 'Estribillos con Acordes',
    page_icon  = '🎵',
    layout     = 'wide',
    initial_sidebar_state = 'collapsed'
)

st.markdown(CSS, unsafe_allow_html=True)

# ── Header ──────────────────────────────────
st.markdown("""
<div class="sb-header">
    <h1>📖 Estribillos con Acordes</h1>
    <span>Cancionero Digital · 2020</span>
</div>
""", unsafe_allow_html=True)

# ── Carga ────────────────────────────────────
with st.spinner('Cargando cancionero…'):
    canciones = cargar_cancionero(NOMBRE_PDF)

if not canciones:
    st.error('⚠️ No se encontró el archivo PDF. Colócalo junto a este script.')
    st.stop()

# ── Stats globales ────────────────────────────
st.markdown(f"""
<div class="stat-row">
  <div class="stat-badge"><b>{len(canciones)}</b>&nbsp;&nbsp;cantos</div>
  <div class="stat-badge"><b>126</b>&nbsp;&nbsp;páginas</div>
  <div class="stat-badge">Tonos: <b>C · D · E · F · G · A · B</b></div>
</div>
""", unsafe_allow_html=True)

# ── Controles en dos filas ────────────────────
col_busq, col_sel = st.columns([1, 2])
with col_busq:
    busqueda = st.text_input('🔍 Buscar canto', placeholder='número o nombre…', label_visibility='collapsed')
with col_sel:
    filtrados = [c['titulo'] for c in canciones if busqueda.lower() in c['titulo'].lower()]
    if not filtrados:
        st.error('Sin resultados.')
        st.stop()
    seleccion = st.selectbox('Canto', filtrados, label_visibility='collapsed')

cancion = next(c for c in canciones if c['titulo'] == seleccion)
t_base  = obtener_tono_base(cancion['tono'])
idx_base = ESCALA.index(t_base) if t_base in ESCALA else 0

# ── Barra de controles ────────────────────────
st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns([1.2, 1.4, 1, 1, 1])

with c1:
    st.markdown(f'<div style="padding-top:6px">Tono original:&nbsp;<span class="tono-pill">{cancion["tono"] or "—"}</span></div>', unsafe_allow_html=True)

with c2:
    modo = st.radio('Transponer por:', ['Tono destino', 'Semitonos (capo)'], horizontal=True, label_visibility='collapsed')

with c3:
    if modo == 'Tono destino':
        t_dest   = st.selectbox('Tono', ESCALA, index=idx_base, label_visibility='collapsed')
        semitonos = (ESCALA.index(t_dest) - idx_base) % 12
    else:
        semitonos = st.number_input('Semitonos', -12, 12, 0, label_visibility='collapsed')
        t_dest    = ESCALA[(idx_base + semitonos) % 12]

with c4:
    tamano = st.slider('Tamaño fuente', 13, 38, 18, label_visibility='collapsed')

with c5:
    cols_vista = st.radio('Columnas', ['1 columna', '2 columnas'], horizontal=True, label_visibility='collapsed')

# ── Indicador de transposición ────────────────
delta = semitonos if semitonos <= 6 else semitonos - 12
if delta != 0:
    signo  = '▲' if delta > 0 else '▼'
    etiq   = f'{signo} {abs(delta)} semitono{"s" if abs(delta)>1 else ""}  ·  {t_base} → {t_dest}'
    color  = '#4caf7d' if delta > 0 else '#e07b5a'
    st.markdown(f'<div style="font-family:var(--mono,monospace);font-size:.78rem;color:{color};margin:4px 0 0;">{etiq}</div>', unsafe_allow_html=True)

st.divider()

# ── Render del canto ──────────────────────────
num_cols   = 1 if cols_vista == '1 columna' else 2
col_style  = f'column-count:{num_cols};column-gap:48px;' if num_cols > 1 else ''

html = f"""
<div class="canto-wrap">
  <div class="canto-titulo">{cancion['titulo']}</div>
  <div style="font-family:var(--mono,'Consolas',monospace);font-size:{tamano}px;line-height:1.65;{col_style}">
"""

versos = cancion['versos']
i = 0
while i < len(versos):
    v = versos[i]

    # Detección de etiqueta de sección
    texto_upper = v['texto'].strip().upper()
    es_inicio_seccion = any(texto_upper.startswith(e.upper()) for e in
                            ['INTRO','CORO','PUENTE','ESTROFA','FINAL'])

    if es_inicio_seccion and i > 0:
        html += '<div class="par-sep"></div>'

    # Par acordes + letra
    if v['tipo'] == 'acordes' and (i+1 < len(versos)) and versos[i+1]['tipo'] == 'letra':
        html += '<div class="par">'
        html += render_linea_acordes(v['texto'], semitonos)
        html += render_linea_letra(versos[i+1]['texto'])
        html += '</div>'
        i += 2
    else:
        html += '<div class="par">'
        if v['tipo'] == 'acordes':
            html += render_linea_acordes(v['texto'], semitonos)
        else:
            html += render_linea_letra(v['texto'])
        html += '</div>'
        i += 1

html += '</div></div>'
st.markdown(html, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────
st.markdown(f"""
<div style="margin-top:40px;text-align:center;font-family:var(--mono,monospace);
            font-size:.7rem;color:#3a3a48;border-top:1px solid #1e1e28;padding-top:12px;">
  Estribillos con Acordes 2020 &nbsp;·&nbsp; {len(canciones)} cantos &nbsp;·&nbsp;
  Tono actual: {t_dest if delta!=0 else cancion['tono'] or t_base}
</div>
""", unsafe_allow_html=True)