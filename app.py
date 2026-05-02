"""
Estribillos con Acordes 2020 — Cancionero Digital
"""
import streamlit as st
import pdfplumber
import json
import re
import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# ─────────────────────────────────────────────────────────────────────
#  CONSTANTES
# ─────────────────────────────────────────────────────────────────────
ESCALA     = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
BEMOLES    = {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}
ETIQUETAS  = ['intro','coro','puente','final','estrofa','sigue','notas',
              'del','al','fin','vuelta']
NOMBRE_PDF = 'ESTRIBILLOS CON ACORDES 2020.pdf'
CACHE_JSON = 'cancionero.json'
TONOS_ORDEN = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B',
               'Cm','C#m','Dm','D#m','Em','Fm','F#m','Gm','G#m','Am','A#m','Bm']

# ─────────────────────────────────────────────────────────────────────
#  LÓGICA MUSICAL
# ─────────────────────────────────────────────────────────────────────
def normalizar_nota(nota):
    return BEMOLES.get(nota, nota)

def obtener_tono_base(tono_str):
    if not tono_str:
        return 'C', False
    m = re.search(r'([A-G][#b]?)(m)?', tono_str.strip())
    if m:
        return normalizar_nota(m.group(1)), bool(m.group(2))
    return 'C', False

def es_linea_de_acordes(linea):
    linea_sin_par = re.sub(r'\([^)]*\)', '', linea)
    palabras = linea_sin_par.strip().split()
    if not palabras:
        palabras = linea.replace('(','').replace(')','').strip().split()
    if not palabras:
        return False
    simbolos = ['//', '///', '|', '||', '-', '[:', ':]']
    patron   = re.compile(r'^[A-G][#b]?(m|Maj|maj|M|dim|dis|aug|aum|sus|add)?\d*(/[A-G][#b]?)?$')
    for p in palabras:
        pl = re.sub(r'[\.,:]+$', '', p).lower()
        if pl in ETIQUETAS or p in simbolos:
            continue
        core = re.sub(r'^(?:/{2,3}|\|+|\[:|\[)+', '', p)
        core = re.sub(r'(?:/{2,3}|\|+|:\]|\])+$', '', core)
        if not core:
            continue
        if '-' in core and len(core) > 1:
            subs = core.split('-')
            if all(patron.match(s) or not s for s in subs):
                continue
            return False
        if not patron.match(core):
            return False
    return True

def transponer_linea(linea, semitonos):
    if semitonos == 0:
        return linea
    partes  = re.split(r'(\s+)', linea)
    patron  = re.compile(r'^[\(\[]?[A-G][#b]?(m|Maj|maj|M|dim|dis|aug|aum|sus|add)?\d*(/[A-G][#b]?)?[\)\]\.,:]?$')
    resultado = ''
    for parte in partes:
        if not parte or parte.isspace():
            resultado += parte
            continue
        core = re.sub(r'^(?:/{2,3}|\|+|\[:|\[)+', '', parte)
        core = re.sub(r'(?:/{2,3}|\|+|:\]|\])+$', '', core)
        es = patron.match(core)
        if not es and '-' in core:
            frags = core.replace('(','').replace(')','').split('-')
            es = all(patron.match(f) for f in frags if f)
        if es:
            _st = semitonos
            def cambiar(m, st=_st):
                n = normalizar_nota(m.group(0))
                if n in ESCALA:
                    return ESCALA[(ESCALA.index(n) + st) % 12]
                return n
            resultado += re.sub(r'(?:^|(?<=[\/\-\(\[\|:]))[A-G][#b]?', cambiar, parte)
        else:
            resultado += parte
    return resultado

# ─────────────────────────────────────────────────────────────────────
#  CARGA DEL CANCIONERO
# ─────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def cargar_cancionero():
    if os.path.exists(CACHE_JSON):
        with open(CACHE_JSON, encoding='utf-8') as f:
            return json.load(f)
    if not os.path.exists(NOMBRE_PDF):
        return []
    canciones      = []
    cancion_actual = None
    patron_bajo    = r'([A-G][#b]?(?:m|Maj|maj|M|dim|dis|aug|aum|sus|add)?\d*)\s*/\s*([A-G][#b]?)'
    with pdfplumber.open(NOMBRE_PDF) as pdf:
        for pagina in pdf.pages[1:]:
            texto = pagina.extract_text(layout=True)
            if not texto:
                continue
            for linea in texto.split('\n'):
                linea        = re.sub(patron_bajo, r'\1/\2', linea)
                linea_limpia = linea.strip()
                if not linea_limpia:
                    continue
                if re.match(r'^\d+[\.\-]?\s', linea_limpia):
                    if cancion_actual:
                        canciones.append(cancion_actual)
                    cancion_actual = {'titulo': linea_limpia, 'tono': '', 'versos': []}
                elif linea_limpia.startswith('TONO:') and cancion_actual:
                    cancion_actual['tono'] = linea_limpia.replace('TONO:', '').strip()
                elif cancion_actual is not None:
                    tipo = 'acordes' if es_linea_de_acordes(linea_limpia) else 'letra'
                    cancion_actual['versos'].append({'tipo': tipo, 'texto': linea.rstrip()})
        if cancion_actual:
            canciones.append(cancion_actual)
    try:
        with open(CACHE_JSON, 'w', encoding='utf-8') as f:
            json.dump(canciones, f, ensure_ascii=False)
    except Exception:
        pass
    return canciones

# ─────────────────────────────────────────────────────────────────────
#  PDF EXPORT
# ─────────────────────────────────────────────────────────────────────
def limpiar_pdf(texto):
    """Colapsa espacios múltiples y convierte a latin-1."""
    texto = re.sub(r' {2,}', ' ', texto).strip()
    reemplazos = {
        '\u2019':"'", '\u2018':"'", '\u201c':'"', '\u201d':'"',
        '\u2013':'-', '\u2014':'-', '\u2026':'...', '\u00b7':'.',
        '\u00e1':'a', '\u00e9':'e', '\u00ed':'i', '\u00f3':'o', '\u00fa':'u',
        '\u00c1':'A', '\u00c9':'E', '\u00cd':'I', '\u00d3':'O', '\u00da':'U',
        '\u00e0':'a', '\u00e8':'e', '\u00ec':'i', '\u00f2':'o', '\u00f9':'u',
        '\u00f1':'n', '\u00d1':'N', '\u00fc':'u', '\u00dc':'U',
        '\u00bf':'?', '\u00a1':'!',
    }
    for k, v in reemplazos.items():
        texto = texto.replace(k, v)
    return texto.encode('latin-1', errors='replace').decode('latin-1')

def generar_pdf(cancion, semitonos, t_destino, es_menor):
    """
    PDF con acordes ENCIMA de la letra (estilo partitura).
    Ambas líneas usan Courier del mismo tamaño para alineación 1:1.
    """
    FS = 9          # font size único para acordes y letra
    LH_A = 4.5     # line height acordes
    LH_L = 5.5     # line height letra

    pdf = FPDF()
    pdf.set_margins(12, 12, 12)
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    # Cabecera
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(160, 110, 20)
    pdf.multi_cell(0, 8, limpiar_pdf(cancion['titulo']), align='L',
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(110, 110, 130)
    sfx = 'm' if es_menor else ''
    pdf.cell(0, 5,
             f"Tono original: {limpiar_pdf(cancion['tono'] or '?')}   ->   Transpuesto a: {t_destino}{sfx}",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.set_draw_color(180, 160, 100)
    pdf.line(12, pdf.get_y(), 198, pdf.get_y())
    pdf.ln(5)

    versos = cancion['versos']
    i = 0
    while i < len(versos):
        v = versos[i]
        tu = v['texto'].strip().upper()

        if any(tu.startswith(e.upper()) for e in ['INTRO','CORO','PUENTE','ESTROFA','FINAL']) and i > 0:
            pdf.ln(4)

        if v['tipo'] == 'acordes' and (i+1 < len(versos)) and versos[i+1]['tipo'] == 'letra':
            # — Acorde encima, letra abajo, misma fuente Courier FS pt —
            acorde_txt = limpiar_pdf(transponer_linea(v['texto'], semitonos))
            letra_txt  = limpiar_pdf(versos[i+1]['texto'])

            pdf.set_font('Courier', 'B', FS)
            pdf.set_text_color(160, 110, 20)
            pdf.multi_cell(0, LH_A, acorde_txt, align='L',
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            pdf.set_font('Courier', '', FS)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, LH_L, letra_txt, align='L',
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            i += 2

        elif v['tipo'] == 'acordes':
            acorde_txt = limpiar_pdf(transponer_linea(v['texto'], semitonos))
            pdf.set_font('Courier', 'B', FS)
            pdf.set_text_color(160, 110, 20)
            pdf.multi_cell(0, LH_A, acorde_txt, align='L',
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            i += 1

        else:
            letra_txt = limpiar_pdf(v['texto'])
            pdf.set_font('Courier', '', FS)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, LH_L, letra_txt, align='L',
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            i += 1

    return bytes(pdf.output())

# ─────────────────────────────────────────────────────────────────────
#  RENDER HTML
# ─────────────────────────────────────────────────────────────────────
PATRON_PURO = re.compile(
    r'^[A-G][#b]?(m|Maj|maj|M|dim|dis|aug|aum|sus|add)?\d*(/[A-G][#b]?)?$'
)

def render_acordes(linea, semitonos):
    linea_t = transponer_linea(linea, semitonos)
    out = ''
    for parte in re.split(r'(\s+)', linea_t):
        if not parte:
            continue
        if parte.isspace():
            out += parte.replace(' ', '&nbsp;')
            continue
        pl = re.sub(r'[\(\)\[\]\.,:]', '', parte)
        pl = re.sub(r'^(?:/{2,3}|\|+)+', '', pl)
        pl = re.sub(r'(?:/{2,3}|\|+)+$', '', pl)
        if PATRON_PURO.match(pl) or ('-' in pl and all(PATRON_PURO.match(f) for f in pl.split('-') if f)):
            out += f'<span class="acorde">{parte}</span>'
        elif pl.lower() in ETIQUETAS:
            out += f'<span class="etiqueta">{parte}</span>'
        else:
            out += parte
    return out + '<br>'

def render_letra(linea):
    return linea.replace(' ', '&nbsp;') + '<br>'

# ─────────────────────────────────────────────────────────────────────
#  CSS — TEMA OSCURO / CLARO
# ─────────────────────────────────────────────────────────────────────
CSS_OSCURO = """
    --bg        : #0d0d0f;
    --surf      : #141418;
    --surf2     : #1c1c22;
    --surf3     : #0f0f13;
    --border    : #2a2a35;
    --accent    : #c49b30;
    --accdim    : #5e4718;
    --text      : #e8e4d8;
    --muted     : #54525f;
    --cbg       : #1e1808;
    --cfg       : #f0c060;
    --lblfg     : #7cb4f0;
    --green     : #4caf7d;
    --red       : #e07b5a;
"""

CSS_CLARO = """
    --bg        : #f5f2eb;
    --surf      : #ffffff;
    --surf2     : #eeeae0;
    --surf3     : #f0ece2;
    --border    : #d4cdb8;
    --accent    : #8a6010;
    --accdim    : #c8a84b;
    --text      : #1a1810;
    --muted     : #7a7060;
    --cbg       : #fdf3d0;
    --cfg       : #7a4800;
    --lblfg     : #1a60b0;
    --green     : #1a7a40;
    --red       : #c04020;
"""

def get_css(tema='oscuro', modo_pres=False):
    vars_tema = CSS_CLARO if tema == 'claro' else CSS_OSCURO

    pres_hide = """
    .sb-header, .stat-row, .stDownloadButton,
    [data-testid="stBottom"] { display:none !important; }
    .canto-wrap { border:none !important; padding:0 !important;
                  background:transparent !important; }
    """ if modo_pres else ""

    return f"""
<style>
:root {{{vars_tema}
    --mono  : 'JetBrains Mono','Fira Code','Consolas',monospace;
    --serif : 'EB Garamond',Georgia,serif;
}}
.stApp,[data-testid="stAppViewContainer"],
html, body {{ background: var(--bg) !important; color: var(--text) !important; }}
#MainMenu, footer, header {{ visibility: hidden; }}
[data-testid="stToolbar"] {{ display: none; }}
[data-testid="stSidebar"] {{
    background: var(--surf3) !important;
    border-right: 1px solid var(--border) !important;
}}
[data-testid="stSidebar"] * {{ color: var(--text) !important; }}
/* inputs */
.stTextInput input, .stNumberInput input {{
    background: var(--surf2) !important; border: 1px solid var(--border) !important;
    border-radius: 6px !important; color: var(--text) !important;
    font-family: var(--mono) !important; font-size: .84rem !important;
}}
.stTextInput input:focus, .stNumberInput input:focus {{
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(140,100,30,.18) !important;
}}
.stSelectbox > div > div {{
    background: var(--surf2) !important; border: 1px solid var(--border) !important;
    border-radius: 6px !important; color: var(--text) !important;
    font-family: var(--mono) !important; font-size: .82rem !important;
}}
.stSelectbox label, .stTextInput label, .stSlider label,
.stRadio label, .stNumberInput label {{
    color: var(--muted) !important; font-size: .76rem !important;
}}
.stSlider [data-baseweb="slider"] [role="slider"] {{
    background: var(--accent) !important; border-color: var(--accent) !important;
}}
/* botones */
.stButton > button {{
    background: var(--surf2) !important; border: 1px solid var(--border) !important;
    color: var(--text) !important; border-radius: 6px !important;
    font-family: var(--mono) !important; font-size: .79rem !important;
    transition: border-color .14s, background .14s;
}}
.stButton > button:hover {{
    border-color: var(--accent) !important; background: var(--surf) !important;
}}
.stDownloadButton > button {{
    background: var(--accdim) !important; border: 1px solid var(--accent) !important;
    color: var(--cfg) !important; border-radius: 6px !important;
    font-family: var(--mono) !important; font-size: .79rem !important;
}}
hr {{ border-color: var(--border) !important; margin: 6px 0 !important; }}
/* header */
.sb-header {{
    display: flex; align-items: baseline; gap: 14px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 14px; margin-bottom: 18px;
}}
.sb-header h1 {{
    font-family: var(--serif); font-size: 2rem; font-weight: 400;
    color: var(--accent); margin: 0; letter-spacing: .04em;
}}
.sb-header span {{
    font-family: var(--mono); font-size: .68rem; color: var(--muted);
    letter-spacing: .14em; text-transform: uppercase;
}}
/* stats */
.stat-row {{ display: flex; gap: 9px; margin: 5px 0 16px; flex-wrap: wrap; }}
.stat-badge {{
    padding: 3px 10px; border-radius: 4px; background: var(--surf2);
    border: 1px solid var(--border); font-family: var(--mono);
    font-size: .68rem; color: var(--muted); letter-spacing: .05em;
}}
.stat-badge b {{ color: var(--accent); }}
/* tono pill */
.tono-pill {{
    display: inline-block; padding: 2px 10px; border-radius: 20px;
    background: var(--cbg); border: 1px solid var(--accdim);
    color: var(--cfg); font-family: var(--mono); font-size: .8rem;
}}
.tono-m {{ border-color: #4a6a9a !important; color: #6a98c8 !important; }}
/* transposición */
.tr-up   {{ color: var(--green); font-family: var(--mono); font-size: .77rem; margin: 3px 0; }}
.tr-down {{ color: var(--red);   font-family: var(--mono); font-size: .77rem; margin: 3px 0; }}
/* canto */
.canto-wrap {{
    background: var(--surf); border: 1px solid var(--border); border-radius: 10px;
    padding: 24px 28px 34px; margin-top: 14px;
}}
.canto-titulo {{
    font-family: var(--serif); font-size: 1.5rem; font-weight: 400;
    color: var(--accent); margin-bottom: 16px; letter-spacing: .02em;
    border-bottom: 1px solid var(--border); padding-bottom: 10px;
}}
.acorde {{
    background: var(--cbg); color: var(--cfg);
    border-radius: 3px; padding: 0 3px; font-weight: 600;
}}
.etiqueta {{ color: var(--lblfg); font-weight: 700; }}
.par {{
    break-inside: avoid-column; page-break-inside: avoid;
    display: block; margin-bottom: 2px;
}}
.par-sep {{ height: 14px; break-inside: avoid-column; }}
{pres_hide}
</style>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
"""

# ─────────────────────────────────────────────────────────────────────
#  APP
# ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title='Estribillos con Acordes',
    page_icon='🎵',
    layout='wide',
    initial_sidebar_state='expanded'
)

# Session state
for k, v in [('favoritos', set()), ('seleccion', None),
             ('presentacion', False), ('tema', 'oscuro')]:
    if k not in st.session_state:
        st.session_state[k] = v

# Carga
with st.spinner('Cargando cancionero…'):
    canciones = cargar_cancionero()

if not canciones:
    st.error('⚠️ No se encontró el PDF ni el cache.')
    st.stop()

tonos_disponibles = sorted(
    set(c['tono'].strip() for c in canciones if c['tono'].strip()),
    key=lambda t: TONOS_ORDEN.index(t) if t in TONOS_ORDEN else 99
)

# ── SIDEBAR ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="font-family:\'EB Garamond\',serif;font-size:1.25rem;'
        'color:var(--accent,#d4a843);border-bottom:1px solid #2a2a35;'
        'padding-bottom:9px;margin-bottom:12px;">📖 Índice</div>',
        unsafe_allow_html=True
    )
    busq_sb   = st.text_input('🔍', placeholder='buscar canto…',
                               label_visibility='collapsed', key='sb_busq')
    solo_favs = st.checkbox('⭐ Solo favoritos')
    tono_sb   = st.selectbox('Tono', ['Todos'] + tonos_disponibles, key='sb_tono')

    lista_sb = canciones
    if busq_sb:
        lista_sb = [c for c in lista_sb if busq_sb.lower() in c['titulo'].lower()]
    if solo_favs:
        lista_sb = [c for c in lista_sb if c['titulo'] in st.session_state.favoritos]
    if tono_sb != 'Todos':
        lista_sb = [c for c in lista_sb if c['tono'].strip() == tono_sb]

    st.caption(f'{len(lista_sb)} de {len(canciones)} cantos')

    for c in lista_sb:
        es_fav = c['titulo'] in st.session_state.favoritos
        label  = ('⭐ ' if es_fav else '') + c['titulo'][:46] + ('…' if len(c['titulo']) > 46 else '')
        if st.button(label, key=f'sb_{c["titulo"]}', use_container_width=True):
            st.session_state.seleccion = c['titulo']
            st.rerun()

    st.caption(f'{len(st.session_state.favoritos)} favorito(s)')

# ── CSS ───────────────────────────────────────────────────────────────
st.markdown(
    get_css(st.session_state.tema, st.session_state.presentacion),
    unsafe_allow_html=True
)

# ── HEADER ───────────────────────────────────────────────────────────
st.markdown(
    '<div class="sb-header">'
    '<h1>📖 Estribillos con Acordes</h1>'
    '<span>Cancionero Digital · 2020</span>'
    '</div>',
    unsafe_allow_html=True
)
st.markdown(
    f'<div class="stat-row">'
    f'<div class="stat-badge"><b>{len(canciones)}</b>&nbsp;cantos</div>'
    f'<div class="stat-badge"><b>126</b>&nbsp;páginas</div>'
    f'<div class="stat-badge">⭐&nbsp;<b>{len(st.session_state.favoritos)}</b>&nbsp;favoritos</div>'
    f'</div>',
    unsafe_allow_html=True
)

# ── SELECTOR + FAVORITO ───────────────────────────────────────────────
col_sel, col_fav = st.columns([5, 1])
titulos = [c['titulo'] for c in canciones]

with col_sel:
    idx_def = 0
    if st.session_state.seleccion and st.session_state.seleccion in titulos:
        idx_def = titulos.index(st.session_state.seleccion)
    seleccion = st.selectbox('Canto', titulos, index=idx_def,
                             label_visibility='collapsed', key='sel_principal')
    if seleccion != st.session_state.seleccion:
        st.session_state.seleccion = seleccion

cancion  = next(c for c in canciones if c['titulo'] == seleccion)
t_base, es_menor = obtener_tono_base(cancion['tono'])
idx_base = ESCALA.index(t_base) if t_base in ESCALA else 0
es_fav   = seleccion in st.session_state.favoritos

with col_fav:
    if st.button('⭐ Quitar' if es_fav else '☆ Guardar',
                 use_container_width=True, key='btn_fav'):
        if es_fav:
            st.session_state.favoritos.discard(seleccion)
        else:
            st.session_state.favoritos.add(seleccion)
        st.rerun()

# ── CONTROLES (una fila, 7 columnas) ─────────────────────────────────
c1, c2, c3, c4, c5, c6, c7 = st.columns([1.2, 1.4, 1, 1, 1, 1, 1])

with c1:
    mc = 'tono-m' if es_menor else ''
    ml = f"{cancion['tono']}{'  (menor)' if es_menor else ''}"
    st.markdown(
        f'<div style="padding-top:8px;font-family:monospace;font-size:.78rem;'
        f'color:var(--muted,#54525f)">Tono:&nbsp;'
        f'<span class="tono-pill {mc}">{ml or "—"}</span></div>',
        unsafe_allow_html=True
    )

with c2:
    modo_t = st.radio('M', ['Tono destino', 'Semitonos (capo)'],
                      horizontal=True, label_visibility='collapsed', key='modo_t')

with c3:
    if modo_t == 'Tono destino':
        t_dest    = st.selectbox('T', ESCALA, index=idx_base, label_visibility='collapsed')
        semitonos = (ESCALA.index(t_dest) - idx_base) % 12
    else:
        semitonos = int(st.number_input('S', -12, 12, 0, label_visibility='collapsed'))
        t_dest    = ESCALA[(idx_base + semitonos) % 12]

with c4:
    tamano = st.slider('F', 13, 42, 18, label_visibility='collapsed')

with c5:
    cols_v = st.radio('Vista', ['1 columna', '2 columnas'],
                      horizontal=True, label_visibility='collapsed', key='cols_v')

with c6:
    if st.button('🎬 Salir' if st.session_state.presentacion else '🎬 Presentar',
                 use_container_width=True, key='btn_pres'):
        st.session_state.presentacion = not st.session_state.presentacion
        st.rerun()

with c7:
    tema_label = '☀️ Claro' if st.session_state.tema == 'oscuro' else '🌙 Oscuro'
    if st.button(tema_label, use_container_width=True, key='btn_tema'):
        st.session_state.tema = 'claro' if st.session_state.tema == 'oscuro' else 'oscuro'
        st.rerun()

# ── INDICADOR TRANSPOSICIÓN ───────────────────────────────────────────
delta = semitonos if semitonos <= 6 else semitonos - 12
if delta != 0:
    sfx   = 'm' if es_menor else ''
    signo = '▲' if delta > 0 else '▼'
    clase = 'tr-up' if delta > 0 else 'tr-down'
    st.markdown(
        f'<div class="{clase}">{signo} {abs(delta)} '
        f'semitono{"s" if abs(delta)>1 else ""}'
        f'&nbsp;·&nbsp;{t_base}{sfx} → {t_dest}{sfx}</div>',
        unsafe_allow_html=True
    )

# ── EXPORT PDF ────────────────────────────────────────────────────────
sfx_pdf  = 'm' if es_menor else ''
pdf_bytes = generar_pdf(cancion, semitonos, t_dest, es_menor)
nombre_f  = re.sub(r'[^\w\s-]', '', cancion['titulo'])[:38].strip().replace(' ', '_')
st.download_button(
    label     = f'⬇ Descargar PDF — {t_dest}{sfx_pdf}',
    data      = pdf_bytes,
    file_name = f'{nombre_f}_{t_dest}{sfx_pdf}.pdf',
    mime      = 'application/pdf',
    key       = 'dl_pdf'
)

st.divider()

# ── RENDER CANTO ─────────────────────────────────────────────────────
num_cols  = 2 if cols_v == '2 columnas' else 1
col_style = f'column-count:{num_cols};column-gap:52px;' if num_cols > 1 else ''

html = (
    f'<div class="canto-wrap">'
    f'<div class="canto-titulo">{cancion["titulo"]}</div>'
    f'<div style="font-family:\'JetBrains Mono\',\'Consolas\',monospace;'
    f'font-size:{tamano}px;line-height:1.65;{col_style}">'
)

versos = cancion['versos']
i = 0
while i < len(versos):
    v       = versos[i]
    tu      = v['texto'].strip().upper()
    es_secc = any(tu.startswith(e.upper())
                  for e in ['INTRO','CORO','PUENTE','ESTROFA','FINAL'])

    if es_secc and i > 0:
        html += '<div class="par-sep"></div>'

    if v['tipo'] == 'acordes' and (i+1 < len(versos)) and versos[i+1]['tipo'] == 'letra':
        html += '<div class="par">'
        html += render_acordes(v['texto'], semitonos)
        html += render_letra(versos[i+1]['texto'])
        html += '</div>'
        i += 2
    else:
        html += '<div class="par">'
        if v['tipo'] == 'acordes':
            html += render_acordes(v['texto'], semitonos)
        else:
            html += render_letra(v['texto'])
        html += '</div>'
        i += 1

html += '</div></div>'
st.markdown(html, unsafe_allow_html=True)

# ── FOOTER ────────────────────────────────────────────────────────────
sfx_f = 'm' if es_menor else ''
st.markdown(
    f'<div style="margin-top:42px;text-align:center;'
    f'font-family:\'JetBrains Mono\',monospace;font-size:.66rem;'
    f'color:var(--muted,#54525f);border-top:1px solid var(--border,#2a2a35);'
    f'padding-top:10px;">'
    f'Estribillos con Acordes 2020 · {len(canciones)} cantos · '
    f'Tono: {t_dest}{sfx_f}</div>',
    unsafe_allow_html=True
)
