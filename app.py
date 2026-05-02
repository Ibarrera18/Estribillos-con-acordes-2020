"""
Estribillos con Acordes 2020 — Cancionero Digital
"""
import streamlit as st
import streamlit.components.v1 as components
import pdfplumber
import json
import re
import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# ─────────────────────────────────────────────────────────────────────
#  CONSTANTES
# ─────────────────────────────────────────────────────────────────────
ESCALA      = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
BEMOLES     = {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}
ETIQUETAS   = ['intro','coro','puente','final','estrofa','sigue','notas',
               'del','al','fin','vuelta']
NOMBRE_PDF  = 'ESTRIBILLOS CON ACORDES 2020.pdf'
CACHE_JSON  = 'cancionero.json'
TONOS_ORDEN = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B',
               'Cm','C#m','Dm','D#m','Em','Fm','F#m','Gm','G#m','Am','A#m','Bm']
LS_KEY      = 'estribillos_favoritos'   # clave en localStorage

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
            def cambiar(m, st=semitonos):
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
def limpiar_chars(texto):
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

def limpiar_letra(texto):
    texto = re.sub(r' {2,}', ' ', texto).strip()
    return limpiar_chars(texto)

def extraer_acordes_con_pos(linea):
    tokens, current, start = [], '', 0
    for i, ch in enumerate(linea):
        if ch == ' ':
            if current.strip():
                tokens.append((start, current.strip()))
            current = ''
            start = i + 1
        else:
            if not current.strip():
                start = i
            current += ch
    if current.strip():
        tokens.append((start, current.strip()))
    return tokens

def courier_char_width_mm(fs):
    return fs * 0.6 * 0.3528

def generar_pdf(cancion, semitonos, t_destino, es_menor):
    FS      = 8.5
    LH_A    = 4.0
    LH_L    = 5.5
    CW      = courier_char_width_mm(FS)
    LMARGIN = 12

    pdf = FPDF()
    pdf.set_margins(LMARGIN, 12, 12)
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(160, 110, 20)
    pdf.multi_cell(0, 8, limpiar_letra(cancion['titulo']), align='L',
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(110, 110, 130)
    sfx = 'm' if es_menor else ''
    tono_orig = limpiar_chars(cancion['tono'] or '?')
    pdf.cell(0, 5,
             f"Tono original: {tono_orig}   ->   Transpuesto a: {t_destino}{sfx}",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.set_draw_color(180, 160, 100)
    pdf.line(LMARGIN, pdf.get_y(), 198, pdf.get_y())
    pdf.ln(5)

    versos = cancion['versos']
    i = 0
    while i < len(versos):
        v  = versos[i]
        tu = v['texto'].strip().upper()

        if any(tu.startswith(e.upper())
               for e in ['INTRO','CORO','PUENTE','ESTROFA','FINAL']) and i > 0:
            pdf.ln(4)

        if v['tipo'] == 'acordes' and (i+1 < len(versos)) and versos[i+1]['tipo'] == 'letra':
            acorde_t = limpiar_chars(transponer_linea(v['texto'], semitonos))
            letra_t  = limpiar_letra(versos[i+1]['texto'])
            y_acorde = pdf.get_y()

            pdf.set_font('Courier', 'B', FS)
            pdf.set_text_color(160, 110, 20)
            for col, acorde in extraer_acordes_con_pos(acorde_t):
                x = min(LMARGIN + col * CW, pdf.w - pdf.r_margin - 12)
                pdf.set_xy(x, y_acorde)
                pdf.cell(30, LH_A, acorde)

            pdf.set_xy(LMARGIN, y_acorde + LH_A)
            pdf.set_font('Courier', '', FS)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, LH_L, letra_t, align='L',
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            i += 2

        elif v['tipo'] == 'acordes':
            acorde_t = limpiar_chars(transponer_linea(v['texto'], semitonos))
            y_acorde = pdf.get_y()
            pdf.set_font('Courier', 'B', FS)
            pdf.set_text_color(160, 110, 20)
            for col, acorde in extraer_acordes_con_pos(acorde_t):
                x = min(LMARGIN + col * CW, pdf.w - pdf.r_margin - 12)
                pdf.set_xy(x, y_acorde)
                pdf.cell(30, LH_A, acorde)
            pdf.set_xy(LMARGIN, y_acorde + LH_A)
            i += 1

        else:
            letra_t = limpiar_letra(v['texto'])
            pdf.set_font('Courier', '', FS)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, LH_L, letra_t, align='L',
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
#  COMPONENTE localStorage — bridge bidireccional
# ─────────────────────────────────────────────────────────────────────
def ls_bridge(favoritos_actuales: list, titulos_todos: list, height=0) -> str | None:
    """
    Inyecta un iframe HTML que:
      - Lee favoritos de localStorage al cargar y los envía a Streamlit
      - Escucha cambios desde Streamlit y los persiste en localStorage
    Retorna el título seleccionado desde el panel flotante, o None.
    """
    favs_json  = json.dumps(favoritos_actuales)
    todos_json = json.dumps(titulos_todos)
    ls_key     = LS_KEY

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; font-family:'Segoe UI',sans-serif; }}
  body {{ background:transparent; }}

  /* ── Botón flotante ── */
  #fab {{
    position: fixed;
    bottom: 28px; right: 28px;
    width: 52px; height: 52px;
    border-radius: 50%;
    background: #c49b30;
    border: none;
    font-size: 22px;
    cursor: pointer;
    box-shadow: 0 4px 16px rgba(0,0,0,.45);
    z-index: 9999;
    transition: transform .15s, background .15s;
    display: flex; align-items: center; justify-content: center;
  }}
  #fab:hover {{ transform: scale(1.1); background: #d4a843; }}

  /* ── Panel flotante ── */
  #panel {{
    position: fixed;
    bottom: 90px; right: 28px;
    width: 310px;
    max-height: 420px;
    background: #141418;
    border: 1px solid #2a2a35;
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0,0,0,.6);
    z-index: 9998;
    display: none;
    flex-direction: column;
    overflow: hidden;
    animation: slideUp .18s ease;
  }}
  @keyframes slideUp {{
    from {{ opacity:0; transform:translateY(12px); }}
    to   {{ opacity:1; transform:translateY(0); }}
  }}
  #panel.open {{ display: flex; }}

  /* Tema claro */
  body.claro #panel  {{ background:#fff; border-color:#d4cdb8; }}
  body.claro #fab    {{ background:#8a6010; }}
  body.claro #fab:hover {{ background:#a07018; }}
  body.claro .item   {{ color:#1a1810 !important; }}
  body.claro .item:hover {{ background:#f0ece2 !important; }}
  body.claro #panel-header {{ background:#f5f2eb; border-color:#d4cdb8; color:#1a1810; }}
  body.claro #empty  {{ color:#7a7060; }}

  #panel-header {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid #2a2a35;
    background: #0f0f13;
    flex-shrink: 0;
  }}
  #panel-header span {{
    font-size: .82rem; font-weight: 600;
    color: #c49b30; letter-spacing: .06em; text-transform: uppercase;
  }}
  #badge {{
    background: #c49b30; color: #0d0d0f;
    border-radius: 10px; font-size: .68rem;
    padding: 1px 7px; font-weight: 700;
  }}
  #close-btn {{
    background: none; border: none; color: #54525f;
    font-size: 16px; cursor: pointer; padding: 2px 6px;
    border-radius: 4px;
  }}
  #close-btn:hover {{ color: #e8e4d8; background: #2a2a35; }}

  #list {{
    overflow-y: auto; flex: 1;
    padding: 6px 0;
    scrollbar-width: thin;
    scrollbar-color: #2a2a35 transparent;
  }}
  .item {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 9px 14px;
    color: #e8e4d8;
    font-size: .78rem;
    cursor: pointer;
    transition: background .1s;
    gap: 8px;
  }}
  .item:hover {{ background: #1c1c22; }}
  .item-titulo {{
    flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }}
  .item-tono {{
    font-size: .65rem; color: #f0c060;
    background: #1e1808; border: 1px solid #5e4718;
    border-radius: 10px; padding: 1px 6px; flex-shrink: 0;
  }}
  .del-btn {{
    background: none; border: none; color: #54525f;
    cursor: pointer; font-size: 14px; padding: 0 2px;
    flex-shrink: 0;
  }}
  .del-btn:hover {{ color: #e05a6a; }}

  #empty {{
    padding: 32px 16px; text-align: center;
    color: #54525f; font-size: .8rem; line-height: 1.6;
  }}
  #empty span {{ font-size: 1.8rem; display:block; margin-bottom:8px; }}
</style>
</head>
<body>

<!-- Botón flotante -->
<button id="fab" title="Favoritos">⭐</button>

<!-- Panel flotante -->
<div id="panel">
  <div id="panel-header">
    <span>⭐ Favoritos <span id="badge">0</span></span>
    <button id="close-btn" title="Cerrar">✕</button>
  </div>
  <div id="list"></div>
</div>

<script>
const LS_KEY   = "{ls_key}";
const TODOS    = {todos_json};
// Map titulo -> tono for display
const TONO_MAP = {{}};

// We'll receive tono info via postMessage from parent if needed
// For now build from TODOS list (titles only, tono shown if passed)

// ── State ──────────────────────────────────────────────────────────
let favs = [];
let panelOpen = false;
let tema = 'oscuro';

// ── Load from localStorage ─────────────────────────────────────────
function loadFavs() {{
  try {{
    const raw = localStorage.getItem(LS_KEY);
    if (raw) favs = JSON.parse(raw);
  }} catch(e) {{ favs = []; }}
  // Seed from Python-passed list if localStorage is empty
  if (favs.length === 0) {{
    favs = {favs_json};
    saveFavs();
  }}
  renderList();
  notifyParent();
}}

function saveFavs() {{
  localStorage.setItem(LS_KEY, JSON.stringify(favs));
}}

// ── Render ─────────────────────────────────────────────────────────
function renderList() {{
  const list = document.getElementById('list');
  const badge = document.getElementById('badge');
  badge.textContent = favs.length;
  document.getElementById('fab').textContent = favs.length > 0 ? '⭐' : '☆';

  if (favs.length === 0) {{
    list.innerHTML = '<div id="empty"><span>☆</span>Aún no tienes favoritos.<br>Presiona ☆ Guardar en cualquier canto.</div>';
    return;
  }}

  list.innerHTML = '';
  favs.forEach(titulo => {{
    const div = document.createElement('div');
    div.className = 'item';

    const t = document.createElement('div');
    t.className = 'item-titulo';
    t.textContent = titulo;
    t.title = titulo;

    const del = document.createElement('button');
    del.className = 'del-btn';
    del.textContent = '✕';
    del.title = 'Quitar de favoritos';
    del.onclick = (e) => {{
      e.stopPropagation();
      favs = favs.filter(f => f !== titulo);
      saveFavs();
      renderList();
      notifyParent();
    }};

    div.appendChild(t);
    div.appendChild(del);

    // Click en el título → seleccionar canto
    t.onclick = () => {{
      window.parent.postMessage({{
        type: 'fav_select',
        titulo: titulo
      }}, '*');
      togglePanel(false);
    }};

    list.appendChild(div);
  }});
}}

// ── Toggle panel ───────────────────────────────────────────────────
function togglePanel(force) {{
  panelOpen = force !== undefined ? force : !panelOpen;
  const panel = document.getElementById('panel');
  if (panelOpen) panel.classList.add('open');
  else panel.classList.remove('open');
}}

document.getElementById('fab').onclick = () => togglePanel();
document.getElementById('close-btn').onclick = () => togglePanel(false);

// Cerrar al hacer clic fuera
document.addEventListener('click', (e) => {{
  const panel = document.getElementById('panel');
  const fab   = document.getElementById('fab');
  if (panelOpen && !panel.contains(e.target) && !fab.contains(e.target)) {{
    togglePanel(false);
  }}
}});

// ── Comunicación con Streamlit (postMessage) ───────────────────────
function notifyParent() {{
  window.parent.postMessage({{
    type: 'favs_update',
    favs: favs
  }}, '*');
}}

// Recibir mensajes desde Streamlit
window.addEventListener('message', (e) => {{
  if (!e.data || !e.data.type) return;

  if (e.data.type === 'add_fav') {{
    if (!favs.includes(e.data.titulo)) {{
      favs.push(e.data.titulo);
      saveFavs(); renderList(); notifyParent();
    }}
  }}
  if (e.data.type === 'remove_fav') {{
    favs = favs.filter(f => f !== e.data.titulo);
    saveFavs(); renderList(); notifyParent();
  }}
  if (e.data.type === 'set_tema') {{
    tema = e.data.tema;
    if (tema === 'claro') document.body.classList.add('claro');
    else document.body.classList.remove('claro');
  }}
  if (e.data.type === 'sync_favs') {{
    // Streamlit pide sincronización al iniciar
    notifyParent();
  }}
}});

// ── Init ───────────────────────────────────────────────────────────
loadFavs();
</script>
</body>
</html>
"""
    result = components.html(html, height=height, scrolling=False)
    return result



# ─────────────────────────────────────────────────────────────────────
#  DESIGN TOKENS
# ─────────────────────────────────────────────────────────────────────
CSS_OSCURO = """
    --bg        : #0c0c0e;
    --surf      : #111116;
    --surf2     : #18181f;
    --surf3     : #0a0a0d;
    --border    : #222230;
    --border2   : #2e2e3e;
    --accent    : #c8983a;
    --accent2   : #e8b84a;
    --accdim    : #3a2808;
    --text      : #e6e2d8;
    --text2     : #9e9aaa;
    --muted     : #48465a;
    --cbg       : #1a1405;
    --cfg       : #eab84a;
    --lblfg     : #6aace8;
    --green     : #3a9e6a;
    --red       : #c86848;
"""
CSS_CLARO = """
    --bg        : #faf8f4;
    --surf      : #ffffff;
    --surf2     : #f2efe8;
    --surf3     : #f5f2ea;
    --border    : #e0d8c8;
    --border2   : #ccc4b0;
    --accent    : #7a5010;
    --accent2   : #9a6820;
    --accdim    : #e8d8a0;
    --text      : #1a1810;
    --text2     : #6a6050;
    --muted     : #9a9080;
    --cbg       : #fdf6e0;
    --cfg       : #6a4000;
    --lblfg     : #1a5898;
    --green     : #1a6a40;
    --red       : #a04020;
"""

def get_css(tema='oscuro'):
    v = CSS_CLARO if tema == 'claro' else CSS_OSCURO
    return f"""
<style>
:root {{{v}
    --mono  : 'JetBrains Mono','Fira Code','Consolas',monospace;
    --serif : 'EB Garamond',Georgia,serif;
    --r4    : 4px;
    --r8    : 8px;
    --r12   : 12px;
}}

/* ── Reset & base ──────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; }}
.stApp, [data-testid="stAppViewContainer"], html, body {{
    background: var(--bg) !important;
    color: var(--text) !important;
}}
#MainMenu, footer, header {{ visibility: hidden; }}
[data-testid="stToolbar"], [data-testid="stSidebar"] {{ display: none !important; }}
[data-testid="stMainBlockContainer"] {{ padding-top: 2rem !important; }}

/* ── Scrollbar ─────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 4px; height: 4px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: var(--border2); border-radius: 2px; }}

/* ── Streamlit tab overrides ───────────────────────────── */
[data-baseweb="tab-list"] {{
    background: transparent !important;
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important;
}}
[data-baseweb="tab"] {{
    background: transparent !important;
    color: var(--text2) !important;
    font-family: var(--mono) !important;
    font-size: .78rem !important;
    letter-spacing: .06em !important;
    padding: 10px 20px !important;
    border-bottom: 2px solid transparent !important;
    transition: color .15s !important;
}}
[data-baseweb="tab"]:hover {{ color: var(--text) !important; }}
[aria-selected="true"][data-baseweb="tab"] {{
    color: var(--accent2) !important;
    border-bottom-color: var(--accent) !important;
}}
[data-testid="stTabPanel"] {{ padding-top: 1.5rem !important; }}

/* ── Inputs ────────────────────────────────────────────── */
.stTextInput input, .stNumberInput input {{
    background: var(--surf2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r8) !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
    font-size: .84rem !important;
    padding: 8px 12px !important;
    transition: border-color .15s !important;
}}
.stTextInput input:focus, .stNumberInput input:focus {{
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(200,152,58,.12) !important;
    outline: none !important;
}}
.stSelectbox > div > div {{
    background: var(--surf2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r8) !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
    font-size: .84rem !important;
    transition: border-color .15s !important;
}}
.stSelectbox > div > div:focus-within {{
    border-color: var(--accent) !important;
}}

/* ── Labels ────────────────────────────────────────────── */
.stSelectbox label, .stTextInput label, .stSlider label,
.stRadio label, .stNumberInput label, .stCheckbox label {{
    color: var(--text2) !important;
    font-family: var(--mono) !important;
    font-size: .72rem !important;
    letter-spacing: .05em !important;
    text-transform: uppercase !important;
}}

/* ── Radio ─────────────────────────────────────────────── */
[data-baseweb="radio"] {{
    gap: 6px !important;
}}
[data-baseweb="radio"] label {{
    color: var(--text2) !important;
    font-family: var(--mono) !important;
    font-size: .78rem !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
}}

/* ── Slider ────────────────────────────────────────────── */
.stSlider [data-baseweb="slider"] > div > div > div:first-child {{
    background: var(--border2) !important;
}}
.stSlider [data-baseweb="slider"] [role="slider"] {{
    background: var(--accent) !important;
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(200,152,58,.15) !important;
}}

/* ── Buttons ───────────────────────────────────────────── */
.stButton > button {{
    background: var(--surf2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text2) !important;
    border-radius: var(--r8) !important;
    font-family: var(--mono) !important;
    font-size: .78rem !important;
    padding: 6px 14px !important;
    transition: all .15s !important;
    letter-spacing: .02em !important;
}}
.stButton > button:hover {{
    border-color: var(--accent) !important;
    color: var(--text) !important;
    background: var(--surf) !important;
}}
.stButton > button[kind="primary"],
.stButton > button[data-testid*="primary"] {{
    background: var(--accent) !important;
    border-color: var(--accent) !important;
    color: #0c0c0e !important;
}}
.stButton > button[kind="primary"]:hover {{
    background: var(--accent2) !important;
    border-color: var(--accent2) !important;
}}
.stDownloadButton > button {{
    background: var(--accdim) !important;
    border: 1px solid var(--border2) !important;
    color: var(--cfg) !important;
    border-radius: var(--r8) !important;
    font-family: var(--mono) !important;
    font-size: .78rem !important;
}}
.stDownloadButton > button:hover {{
    border-color: var(--accent) !important;
}}

/* ── Divider ───────────────────────────────────────────── */
hr {{ border: none !important; border-top: 1px solid var(--border) !important; margin: 20px 0 !important; }}

/* ── Info / Alert ──────────────────────────────────────── */
.stAlert {{ border-radius: var(--r8) !important; }}

/* ══════════════════════════════════════════════════════════
   COMPONENTES CUSTOM
   ══════════════════════════════════════════════════════════ */

/* ── App header ────────────────────────────────────────── */
.app-header {{
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    padding-bottom: 20px;
    margin-bottom: 8px;
    border-bottom: 1px solid var(--border);
}}
.app-header-left h1 {{
    font-family: var(--serif);
    font-size: 1.9rem;
    font-weight: 400;
    color: var(--accent2);
    letter-spacing: .02em;
    margin: 0;
    line-height: 1;
}}
.app-header-left span {{
    font-family: var(--mono);
    font-size: .65rem;
    color: var(--muted);
    letter-spacing: .18em;
    text-transform: uppercase;
    display: block;
    margin-top: 4px;
}}
.app-header-right {{
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
}}
.header-chip {{
    font-family: var(--mono);
    font-size: .65rem;
    color: var(--text2);
    background: var(--surf2);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 3px 10px;
    letter-spacing: .05em;
}}
.header-chip b {{ color: var(--accent2); }}

/* ── Tono pill ─────────────────────────────────────────── */
.tono-pill {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    border-radius: 20px;
    background: var(--cbg);
    border: 1px solid var(--border2);
    color: var(--cfg);
    font-family: var(--mono);
    font-size: .78rem;
    font-weight: 600;
}}
.tono-m {{ border-color: #3a5a8a !important; color: #6a9cce !important; }}

/* ── Control bar ───────────────────────────────────────── */
.ctrl-bar {{
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 14px;
    background: var(--surf);
    border: 1px solid var(--border);
    border-radius: var(--r12);
    margin-bottom: 14px;
    flex-wrap: wrap;
}}
.ctrl-label {{
    font-family: var(--mono);
    font-size: .62rem;
    color: var(--muted);
    letter-spacing: .1em;
    text-transform: uppercase;
    margin-right: 2px;
}}
.ctrl-sep {{
    width: 1px; height: 20px;
    background: var(--border);
    margin: 0 4px;
    flex-shrink: 0;
}}

/* ── Transposition indicator ───────────────────────────── */
.transp-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 20px;
    font-family: var(--mono);
    font-size: .75rem;
    margin-bottom: 12px;
}}
.transp-up   {{ background: rgba(58,158,106,.1); border: 1px solid rgba(58,158,106,.3); color: var(--green); }}
.transp-down {{ background: rgba(200,104,72,.1); border: 1px solid rgba(200,104,72,.3); color: var(--red); }}
.transp-zero {{ display: none; }}

/* ── Canto wrap ────────────────────────────────────────── */
.canto-wrap {{
    background: var(--surf);
    border: 1px solid var(--border);
    border-radius: var(--r12);
    padding: 28px 32px 40px;
    margin-top: 8px;
}}
@media (max-width: 600px) {{
    .canto-wrap {{ padding: 18px 16px 32px; }}
}}
.canto-titulo {{
    font-family: var(--serif);
    font-size: 1.4rem;
    font-weight: 400;
    color: var(--accent2);
    margin-bottom: 20px;
    letter-spacing: .02em;
    border-bottom: 1px solid var(--border);
    padding-bottom: 12px;
    line-height: 1.3;
}}
.acorde {{
    color: var(--cfg);
    font-weight: 700;
    background: var(--cbg);
    border-radius: 3px;
    padding: 0 3px;
}}
.etiqueta {{
    color: var(--lblfg);
    font-weight: 700;
    font-size: .9em;
    letter-spacing: .06em;
}}
.par {{ break-inside: avoid-column; page-break-inside: avoid; display: block; margin-bottom: 2px; }}
.par-sep {{ height: 16px; break-inside: avoid-column; }}

/* ── Setlist items ─────────────────────────────────────── */
.sl-row {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    background: var(--surf);
    border: 1px solid var(--border);
    border-radius: var(--r8);
    margin-bottom: 6px;
    transition: border-color .15s;
}}
.sl-row:hover {{ border-color: var(--border2); }}
.sl-num {{
    font-family: var(--mono);
    font-size: .65rem;
    color: var(--muted);
    min-width: 18px;
    text-align: right;
}}
.sl-titulo {{
    flex: 1;
    font-family: var(--mono);
    font-size: .8rem;
    color: var(--text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.sl-tono {{
    font-family: var(--mono);
    font-size: .65rem;
    color: var(--cfg);
    background: var(--cbg);
    border: 1px solid var(--border2);
    border-radius: 10px;
    padding: 2px 8px;
}}

/* ── Empty state ───────────────────────────────────────── */
.empty-state {{
    text-align: center;
    padding: 64px 24px;
    color: var(--text2);
}}
.empty-icon {{ font-size: 2.5rem; margin-bottom: 16px; opacity: .5; }}
.empty-title {{
    font-family: var(--serif);
    font-size: 1.3rem;
    color: var(--text2);
    margin-bottom: 8px;
}}
.empty-sub {{
    font-family: var(--mono);
    font-size: .75rem;
    color: var(--muted);
    line-height: 1.7;
}}
</style>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
"""
def render_presentacion(setlist_data, idx_actual, tema):
    import streamlit.components.v1 as components

    items_json = json.dumps(setlist_data, ensure_ascii=False)
    is_dark = tema == 'oscuro'
    bg     = '#0a0a0c' if is_dark else '#f8f5ee'
    surf   = '#13131a' if is_dark else '#ffffff'
    text   = '#edeae0' if is_dark else '#1a1810'
    accent = '#d4a843' if is_dark else '#8a6010'
    cbg    = '#1e1808' if is_dark else '#fdf3d0'
    cfg    = '#f0c060' if is_dark else '#7a4800'
    muted  = '#4a4858' if is_dark else '#8a8070'
    border = '#252530' if is_dark else '#d4cdb8'
    nav_bg = '#1a1a24ee' if is_dark else '#ffffffee'
    lbl_fg = '#7cb4f0'

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}

html, body {{
    background: {bg};
    color: {text};
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    height: 100%;
    overflow: hidden;
}}

/* ── Fullscreen container ── */
#app {{
    width: 100vw;
    height: 100vh;
    display: flex;
    flex-direction: column;
    position: relative;
    overflow: hidden;
}}

/* ── Top bar ── */
#topbar {{
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 10px 20px 10px 32px;
    background: {surf};
    border-bottom: 1px solid {border};
    z-index: 10;
}}
#titulo-h {{
    font-family: 'EB Garamond', serif;
    font-size: 1.15rem;
    font-weight: 400;
    color: {accent};
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    letter-spacing: .02em;
}}
#tono-h {{
    font-size: .7rem;
    color: {cfg};
    background: {cbg};
    border: 1px solid #5e4718;
    border-radius: 12px;
    padding: 3px 12px;
    white-space: nowrap;
    letter-spacing: .06em;
}}
#prog-h {{
    font-size: .7rem;
    color: {muted};
    white-space: nowrap;
    letter-spacing: .06em;
}}
#fs-btn {{
    background: none;
    border: 1px solid {border};
    color: {muted};
    border-radius: 6px;
    padding: 4px 10px;
    font-size: .72rem;
    cursor: pointer;
    font-family: 'JetBrains Mono', monospace;
    transition: border-color .14s, color .14s;
    white-space: nowrap;
}}
#fs-btn:hover {{ border-color: {accent}; color: {accent}; }}

/* ── Cuerpo scrollable ── */
#scroll-area {{
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 32px 48px 140px 48px;
    scrollbar-width: thin;
    scrollbar-color: {border} transparent;
}}
#scroll-area::-webkit-scrollbar {{ width: 6px; }}
#scroll-area::-webkit-scrollbar-thumb {{ background: {border}; border-radius: 3px; }}

/* ── Texto del canto ── */
#canto-body {{
    font-size: clamp(14px, 2.2vw, 22px);
    line-height: 1.7;
    max-width: 900px;
    margin: 0 auto;
}}
.acorde {{ color: {cfg}; font-weight: 700; }}
.etiqueta {{ color: {lbl_fg}; font-weight: 700; }}
.par {{ margin-bottom: 2px; }}
.par-sep {{ height: 18px; }}

/* ── Dots laterales ── */
#dots {{
    position: fixed;
    left: 10px;
    top: 50%;
    transform: translateY(-50%);
    display: flex;
    flex-direction: column;
    gap: 6px;
    z-index: 20;
    padding: 8px 0;
}}
.dot {{
    width: 7px; height: 7px;
    border-radius: 50%;
    background: {border};
    cursor: pointer;
    transition: background .15s, transform .15s;
}}
.dot.activo {{ background: {accent}; transform: scale(1.5); }}
.dot:hover {{ background: {accent}; }}

/* ── Barra de navegación flotante ── */
#nav {{
    position: fixed;
    bottom: 0; left: 0; right: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    padding: 12px 24px;
    background: {nav_bg};
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-top: 1px solid {border};
    z-index: 50;
}}
.nav-zone {{
    flex: 1;
    display: flex;
    align-items: center;
}}
.nav-zone.right {{ justify-content: flex-end; }}
.nav-zone.center {{
    flex: 2;
    flex-direction: column;
    align-items: center;
    gap: 2px;
}}
.nav-btn {{
    display: flex;
    align-items: center;
    gap: 8px;
    background: none;
    border: 1px solid {border};
    color: {text};
    border-radius: 24px;
    padding: 8px 22px;
    font-family: 'JetBrains Mono', monospace;
    font-size: .8rem;
    cursor: pointer;
    transition: border-color .14s, background .14s, color .14s;
    white-space: nowrap;
}}
.nav-btn:hover:not(:disabled) {{
    border-color: {accent};
    background: {cbg};
    color: {cfg};
}}
.nav-btn:disabled {{ opacity: .25; cursor: default; }}
.nav-btn .arrow {{ font-size: 1rem; }}
#next-preview {{
    font-size: .65rem;
    color: {muted};
    text-align: center;
    max-width: 260px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
#next-label {{
    font-size: .58rem;
    color: {muted};
    letter-spacing: .1em;
    text-transform: uppercase;
}}
</style>
</head>
<body>
<div id="app">

  <!-- Top bar -->
  <div id="topbar">
    <div id="titulo-h"></div>
    <div id="tono-h"></div>
    <div id="prog-h"></div>
    <button id="fs-btn" onclick="toggleFS()">⛶ Pantalla completa</button>
  </div>

  <!-- Dots -->
  <div id="dots"></div>

  <!-- Cuerpo -->
  <div id="scroll-area">
    <div id="canto-body"></div>
  </div>

  <!-- Nav flotante -->
  <div id="nav">
    <div class="nav-zone left">
      <button class="nav-btn" id="prev-btn" onclick="navegar(-1)">
        <span class="arrow">←</span> Anterior
      </button>
    </div>
    <div class="nav-zone center">
      <div id="next-label">SIGUIENTE</div>
      <div id="next-preview">—</div>
    </div>
    <div class="nav-zone right">
      <button class="nav-btn" id="next-btn" onclick="navegar(1)">
        Siguiente <span class="arrow">→</span>
      </button>
    </div>
  </div>

</div><!-- #app -->

<script>
const ITEMS = {items_json};
let idx = {idx_actual};
const ETIQUETAS = ['intro','coro','puente','final','estrofa','sigue'];

function esc(t) {{
    return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}

function renderAcordes(linea) {{
    return linea.split(/(\s+)/).map(p => {{
        if (!p) return '';
        if (/^\s+$/.test(p)) return p.replace(/ /g, '&nbsp;');
        let pl = p.replace(/[\(\)\[\]\.,:]/g, '');
        pl = pl.replace(/^[\/|[]+/, '').replace(/[\/|]+$/, '');
        if (/^[A-G][#b]?(m|Maj|maj|M|dim|dis|aug|aum|sus|add)?[\d]*(\/[A-G][#b]?)?$/.test(pl))
            return '<span class="acorde">' + esc(p) + '</span>';
        if (ETIQUETAS.includes(pl.toLowerCase()))
            return '<span class="etiqueta">' + esc(p) + '</span>';
        return esc(p);
    }}).join('');
}}

function renderCanto() {{
    const item = ITEMS[idx];

    // Topbar
    document.getElementById('titulo-h').textContent = item.titulo;
    const sfx = item.es_menor ? 'm' : '';
    document.getElementById('tono-h').textContent =
        (item.tono_orig || '?') + ' → ' + item.tono_dest + sfx;
    document.getElementById('prog-h').textContent = (idx + 1) + ' / ' + ITEMS.length;

    // Botones nav
    document.getElementById('prev-btn').disabled = idx === 0;
    document.getElementById('next-btn').disabled = idx === ITEMS.length - 1;

    // Preview siguiente
    if (idx < ITEMS.length - 1) {{
        document.getElementById('next-label').style.opacity = '1';
        document.getElementById('next-preview').textContent = ITEMS[idx + 1].titulo.replace(/^\d+[\.\-]?\s*/, '');
    }} else {{
        document.getElementById('next-label').style.opacity = '0';
        document.getElementById('next-preview').textContent = 'Fin del setlist';
    }}

    // Dots
    const dotsEl = document.getElementById('dots');
    dotsEl.innerHTML = '';
    ITEMS.forEach((_, i) => {{
        const d = document.createElement('div');
        d.className = 'dot' + (i === idx ? ' activo' : '');
        d.title = ITEMS[i].titulo;
        d.onclick = () => {{ idx = i; renderCanto(); }};
        dotsEl.appendChild(d);
    }});

    // Cuerpo
    let html = '';
    const versos = item.versos;
    let i = 0;
    while (i < versos.length) {{
        const v = versos[i];
        const tu = (v.texto || '').trim().toUpperCase();
        const esSecc = ['INTRO','CORO','PUENTE','ESTROFA','FINAL'].some(e => tu.startsWith(e));
        if (esSecc && i > 0) html += '<div class="par-sep"></div>';

        if (v.tipo === 'acordes' && i + 1 < versos.length && versos[i + 1].tipo === 'letra') {{
            html += '<div class="par">';
            html += renderAcordes(v.texto);
            html += '<br>' + esc(versos[i + 1].texto);
            html += '</div>';
            i += 2;
        }} else if (v.tipo === 'acordes') {{
            html += '<div class="par">' + renderAcordes(v.texto) + '</div>';
            i++;
        }} else {{
            html += '<div class="par">' + esc(v.texto) + '</div>';
            i++;
        }}
    }}
    document.getElementById('canto-body').innerHTML = html;
    document.getElementById('scroll-area').scrollTo(0, 0);
}}

function navegar(dir) {{
    idx = Math.max(0, Math.min(ITEMS.length - 1, idx + dir));
    renderCanto();
}}

// Fullscreen API
function toggleFS() {{
    const el = document.documentElement;
    if (!document.fullscreenElement) {{
        (el.requestFullscreen || el.webkitRequestFullscreen || el.mozRequestFullScreen || el.msRequestFullscreen).call(el);
        document.getElementById('fs-btn').textContent = '✕ Salir pantalla completa';
    }} else {{
        (document.exitFullscreen || document.webkitExitFullscreen || document.mozCancelFullScreen || document.msExitFullscreen).call(document);
        document.getElementById('fs-btn').textContent = '⛶ Pantalla completa';
    }}
}}

document.addEventListener('fullscreenchange', () => {{
    if (!document.fullscreenElement)
        document.getElementById('fs-btn').textContent = '⛶ Pantalla completa';
}});

// Teclado
document.addEventListener('keydown', e => {{
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === ' ') {{
        e.preventDefault(); navegar(1);
    }}
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {{
        e.preventDefault(); navegar(-1);
    }}
    if (e.key === 'f' || e.key === 'F') toggleFS();
}});

// Swipe en móvil
let touchX = 0;
document.addEventListener('touchstart', e => {{ touchX = e.touches[0].clientX; }});
document.addEventListener('touchend', e => {{
    const dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 60) navegar(dx < 0 ? 1 : -1);
}});

// Auto-fullscreen al abrir
window.addEventListener('load', () => {{
    setTimeout(() => {{
        try {{
            document.documentElement.requestFullscreen && document.documentElement.requestFullscreen();
            document.getElementById('fs-btn').textContent = '✕ Salir pantalla completa';
        }} catch(e) {{}}
    }}, 300);
}});

renderCanto();
</script>
</body>
</html>"""

    components.html(html, height=750, scrolling=False)



# ─────────────────────────────────────────────────────────────────────
#  APP PRINCIPAL
# ─────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────
#  APP
# ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title='Estribillos con Acordes',
    page_icon='🎵',
    layout='wide',
    initial_sidebar_state='collapsed'
)

for k, v in [('seleccion', None), ('tema', 'oscuro'),
             ('setlist', []), ('modo', 'cancionero'), ('pres_idx', 0)]:
    if k not in st.session_state:
        st.session_state[k] = v

with st.spinner('Cargando cancionero…'):
    canciones = cargar_cancionero()

if not canciones:
    st.error('⚠️  No se encontró el PDF ni el cache.')
    st.stop()

titulos = [c['titulo'] for c in canciones]

# ─────────────────────────────────────────────────────────────────────
#  MODO PRESENTACIÓN
# ─────────────────────────────────────────────────────────────────────
if st.session_state.modo == 'presentacion':
    st.markdown(get_css(st.session_state.tema), unsafe_allow_html=True)
    setlist_data = []
    for item in st.session_state.setlist:
        c = next((x for x in canciones if x['titulo'] == item['titulo']), None)
        if c:
            _, es_menor = obtener_tono_base(c['tono'])
            setlist_data.append({
                'titulo'   : c['titulo'],
                'tono_orig': c['tono'],
                'tono_dest': item['t_dest'],
                'semitonos': item['semitonos'],
                'es_menor' : es_menor,
                'versos'   : c['versos']
            })
    render_presentacion(setlist_data, st.session_state.pres_idx, st.session_state.tema)
    if st.button('✕ Salir de presentación', key='salir_pres'):
        st.session_state.modo = 'setlist'
        st.rerun()
    st.stop()

# ─────────────────────────────────────────────────────────────────────
#  LAYOUT NORMAL
# ─────────────────────────────────────────────────────────────────────
st.markdown(get_css(st.session_state.tema), unsafe_allow_html=True)

# ── APP HEADER ────────────────────────────────────────────────────────
tema_icon = '☀️' if st.session_state.tema == 'oscuro' else '🌙'
tema_text = 'Claro' if st.session_state.tema == 'oscuro' else 'Oscuro'

hcol1, hcol2 = st.columns([4, 1])
with hcol1:
    st.markdown(
        f'<div class="app-header-left">'
        f'<h1>Estribillos con Acordes</h1>'
        f'<span>Cancionero · 327 cantos · 2020</span>'
        f'</div>',
        unsafe_allow_html=True
    )
with hcol2:
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    if st.button(f'{tema_icon} {tema_text}', use_container_width=True, key='btn_tema'):
        st.session_state.tema = 'claro' if st.session_state.tema == 'oscuro' else 'oscuro'
        st.rerun()

st.markdown('<div style="height:4px;border-bottom:1px solid var(--border,#222230);margin-bottom:20px"></div>',
            unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────────────────────────────
sl_count = len(st.session_state.setlist)
tab1, tab2 = st.tabs([
    '  Cancionero  ',
    f'  Setlist  {sl_count if sl_count else ""}  '.strip()
])

# ═══════════════════════════════════════════════════════════════════
#  TAB 1 — CANCIONERO
# ═══════════════════════════════════════════════════════════════════
with tab1:

    # ── Selector de canto ─────────────────────────────────────────
    def on_select():
        st.session_state.seleccion = st.session_state.sel_widget

    idx_def = 0
    if st.session_state.seleccion and st.session_state.seleccion in titulos:
        idx_def = titulos.index(st.session_state.seleccion)

    st.selectbox('Canto', titulos, index=idx_def,
                 label_visibility='collapsed',
                 key='sel_widget', on_change=on_select)

    seleccion = st.session_state.seleccion or titulos[0]
    cancion   = next(c for c in canciones if c['titulo'] == seleccion)
    t_base, es_menor = obtener_tono_base(cancion['tono'])
    idx_base  = ESCALA.index(t_base) if t_base in ESCALA else 0
    ya_en_sl  = any(x['titulo'] == seleccion for x in st.session_state.setlist)

    # ── Barra de controles ────────────────────────────────────────
    cc1, cc2, cc3, cc4, cc5 = st.columns([1.4, 1.2, 1, 1, 1.2])

    with cc1:
        modo_t = st.radio('Transponer', ['Por tono', 'Por capo'],
                          horizontal=True, key='modo_t')
    with cc2:
        if modo_t == 'Por tono':
            t_dest    = st.selectbox('Tono destino', ESCALA, index=idx_base, key='sel_tono')
            semitonos = (ESCALA.index(t_dest) - idx_base) % 12
        else:
            semitonos = int(st.number_input('Capo (semitonos)', -12, 12, 0, key='num_semi'))
            t_dest    = ESCALA[(idx_base + semitonos) % 12]
    with cc3:
        tamano = st.slider('Tamaño fuente', 13, 42, 18, key='slider_font')
    with cc4:
        cols_v = st.radio('Columnas', ['1', '2'], horizontal=True, key='radio_cols')
    with cc5:
        mc  = 'tono-m' if es_menor else ''
        sfx = 'm' if es_menor else ''
        st.markdown(
            f'<div style="padding-top:6px">'
            f'<div style="font-family:var(--mono);font-size:.62rem;color:var(--muted);'
            f'letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px">Tono original</div>'
            f'<span class="tono-pill {mc}">{cancion["tono"] or "—"}{sfx}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── Indicador de transposición ────────────────────────────────
    delta = semitonos if semitonos <= 6 else semitonos - 12
    sfx   = 'm' if es_menor else ''
    if delta != 0:
        signo = '▲' if delta > 0 else '▼'
        clase = 'transp-up' if delta > 0 else 'transp-down'
        semi_txt = f'{abs(delta)} semitono{"s" if abs(delta)>1 else ""}'
        st.markdown(
            f'<div class="transp-badge {clase}">'
            f'{signo} {semi_txt} &nbsp;·&nbsp; '
            f'{t_base}{sfx} → {t_dest}{sfx}'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── Acciones: agregar setlist + PDF ──────────────────────────
    act1, act2, act3 = st.columns([2, 1.4, 1])
    with act1:
        if ya_en_sl:
            st.markdown(
                f'<div style="padding:8px 0;font-family:var(--mono);font-size:.78rem;'
                f'color:var(--green)">✓ En setlist como {t_dest}{sfx}</div>',
                unsafe_allow_html=True
            )
        else:
            if st.button(f'＋ Agregar al setlist · {t_dest}{sfx}',
                         use_container_width=True, key='btn_add2'):
                st.session_state.setlist.append({
                    'titulo': seleccion, 'semitonos': semitonos,
                    't_dest': t_dest, 'es_menor': es_menor
                })
                st.rerun()
    with act2:
        pdf_bytes = generar_pdf(cancion, semitonos, t_dest, es_menor)
        nombre_f  = re.sub(r'[^\w\s-]', '', cancion['titulo'])[:38].strip().replace(' ', '_')
        st.download_button(
            label     = f'⬇ PDF — {t_dest}{sfx}',
            data      = pdf_bytes,
            file_name = f'{nombre_f}_{t_dest}{sfx}.pdf',
            mime      = 'application/pdf',
            key       = 'dl_pdf',
            use_container_width = True
        )
    with act3:
        pass  # espacio visual

    st.divider()

    # ── Render del canto ──────────────────────────────────────────
    num_cols  = 2 if cols_v == '2' else 1
    col_style = f'column-count:{num_cols};column-gap:56px;' if num_cols > 1 else ''

    html = (
        f'<div class="canto-wrap">'
        f'<div class="canto-titulo">{cancion["titulo"]}</div>'
        f'<div style="font-family:\'JetBrains Mono\',\'Consolas\',monospace;'
        f'font-size:{tamano}px;line-height:1.7;{col_style}">'
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

# ═══════════════════════════════════════════════════════════════════
#  TAB 2 — SETLIST
# ═══════════════════════════════════════════════════════════════════
with tab2:
    if not st.session_state.setlist:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">📋</div>'
            '<div class="empty-title">Setlist vacío</div>'
            '<div class="empty-sub">Ve al Cancionero, selecciona un canto<br>'
            'y presiona <b>＋ Agregar al setlist</b>.</div>'
            '</div>',
            unsafe_allow_html=True
        )
    else:
        # ── Acciones del setlist ──────────────────────────────────
        sa1, sa2, sa3 = st.columns([2, 1, 1])
        with sa1:
            if st.button('🎬 Iniciar Presentación', use_container_width=True,
                         key='btn_presentar', type='primary'):
                st.session_state.modo = 'presentacion'
                st.session_state.pres_idx = 0
                st.rerun()
        with sa2:
            if st.button('🗑 Vaciar setlist', use_container_width=True, key='btn_clear'):
                st.session_state.setlist = []
                st.rerun()
        with sa3:
            pass

        st.markdown(
            f'<div style="font-family:var(--mono);font-size:.7rem;color:var(--text2);'
            f'margin:12px 0 16px;letter-spacing:.04em">'
            f'{len(st.session_state.setlist)} canto{"s" if len(st.session_state.setlist)!=1 else ""}'
            f'</div>',
            unsafe_allow_html=True
        )

        # ── Lista ────────────────────────────────────────────────
        to_delete = None
        to_move   = None

        for i, item in enumerate(st.session_state.setlist):
            sfx_sl = 'm' if item['es_menor'] else ''
            sc1, sc2, sc3, sc4, sc5 = st.columns([.35, 4.5, .8, .5, .5])
            with sc1:
                st.markdown(
                    f'<div style="padding-top:10px;text-align:right;font-family:var(--mono);'
                    f'font-size:.65rem;color:var(--muted)">{i+1}</div>',
                    unsafe_allow_html=True
                )
            with sc2:
                titulo_disp = item['titulo']
                # Strip leading number
                titulo_disp = re.sub(r'^\d+[\.\-]?\s*', '', titulo_disp)
                st.markdown(
                    f'<div style="padding-top:9px;font-family:var(--mono);font-size:.8rem;'
                    f'color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
                    f'{titulo_disp[:60]}{"…" if len(titulo_disp)>60 else ""}</div>',
                    unsafe_allow_html=True
                )
            with sc3:
                st.markdown(
                    f'<div style="padding-top:7px">'
                    f'<span class="tono-pill" style="font-size:.68rem">'
                    f'{item["t_dest"]}{sfx_sl}</span></div>',
                    unsafe_allow_html=True
                )
            with sc4:
                if i > 0:
                    if st.button('↑', key=f'up_{i}', use_container_width=True):
                        to_move = (i, -1)
            with sc5:
                if st.button('✕', key=f'del_{i}', use_container_width=True):
                    to_delete = i

            # Down button in a separate tiny row below sc4 to avoid cramping
            # (handled via the same column trick)

        if to_delete is not None:
            st.session_state.setlist.pop(to_delete)
            st.rerun()
        if to_move is not None:
            idx_m, d = to_move
            sl = st.session_state.setlist
            sl[idx_m], sl[idx_m+d] = sl[idx_m+d], sl[idx_m]
            st.rerun()

# ── FOOTER ────────────────────────────────────────────────────────────
st.markdown(
    '<div style="margin-top:48px;padding-top:16px;text-align:center;'
    'border-top:1px solid var(--border,#222230);'
    'font-family:\'JetBrains Mono\',monospace;font-size:.62rem;'
    'color:var(--muted,#48465a);letter-spacing:.06em;">'
    'ESTRIBILLOS CON ACORDES · 2020'
    '</div>',
    unsafe_allow_html=True
)