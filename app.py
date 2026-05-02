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
#  CSS
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


# ─────────────────────────────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────────────────────────────
def get_css(tema='oscuro'):
    v = CSS_CLARO if tema == 'claro' else CSS_OSCURO
    return f"""
<style>
:root {{{v}
    --mono  : 'JetBrains Mono','Fira Code','Consolas',monospace;
    --serif : 'EB Garamond',Georgia,serif;
}}
.stApp,[data-testid="stAppViewContainer"],html,body{{
    background:var(--bg)!important;color:var(--text)!important;}}
#MainMenu,footer,header{{visibility:hidden;}}
[data-testid="stToolbar"]{{display:none;}}
[data-testid="stSidebar"]{{display:none!important;}}
.stTextInput input,.stNumberInput input{{
    background:var(--surf2)!important;border:1px solid var(--border)!important;
    border-radius:6px!important;color:var(--text)!important;
    font-family:var(--mono)!important;font-size:.84rem!important;}}
.stTextInput input:focus,.stNumberInput input:focus{{
    border-color:var(--accent)!important;
    box-shadow:0 0 0 2px rgba(140,100,30,.18)!important;}}
.stSelectbox>div>div{{
    background:var(--surf2)!important;border:1px solid var(--border)!important;
    border-radius:6px!important;color:var(--text)!important;
    font-family:var(--mono)!important;font-size:.82rem!important;}}
.stSelectbox label,.stTextInput label,.stSlider label,
.stRadio label,.stNumberInput label{{
    color:var(--muted)!important;font-size:.76rem!important;}}
.stSlider [data-baseweb="slider"] [role="slider"]{{
    background:var(--accent)!important;border-color:var(--accent)!important;}}
.stButton>button{{
    background:var(--surf2)!important;border:1px solid var(--border)!important;
    color:var(--text)!important;border-radius:6px!important;
    font-family:var(--mono)!important;font-size:.79rem!important;
    transition:border-color .14s,background .14s;}}
.stButton>button:hover{{border-color:var(--accent)!important;background:var(--surf)!important;}}
.stDownloadButton>button{{
    background:var(--accdim)!important;border:1px solid var(--accent)!important;
    color:var(--cfg)!important;border-radius:6px!important;
    font-family:var(--mono)!important;font-size:.79rem!important;}}
hr{{border-color:var(--border)!important;margin:6px 0!important;}}
.sb-header{{display:flex;align-items:baseline;gap:14px;
    border-bottom:1px solid var(--border);padding-bottom:14px;margin-bottom:18px;}}
.sb-header h1{{font-family:var(--serif);font-size:2rem;font-weight:400;
    color:var(--accent);margin:0;letter-spacing:.04em;}}
.sb-header span{{font-family:var(--mono);font-size:.68rem;color:var(--muted);
    letter-spacing:.14em;text-transform:uppercase;}}
.stat-row{{display:flex;gap:9px;margin:5px 0 16px;flex-wrap:wrap;}}
.stat-badge{{padding:3px 10px;border-radius:4px;background:var(--surf2);
    border:1px solid var(--border);font-family:var(--mono);
    font-size:.68rem;color:var(--muted);letter-spacing:.05em;}}
.stat-badge b{{color:var(--accent);}}
.tono-pill{{display:inline-block;padding:2px 10px;border-radius:20px;
    background:var(--cbg);border:1px solid var(--accdim);
    color:var(--cfg);font-family:var(--mono);font-size:.8rem;}}
.tono-m{{border-color:#4a6a9a!important;color:#6a98c8!important;}}
.tr-up{{color:var(--green);font-family:var(--mono);font-size:.77rem;margin:3px 0;}}
.tr-down{{color:var(--red);font-family:var(--mono);font-size:.77rem;margin:3px 0;}}
.canto-wrap{{background:var(--surf);border:1px solid var(--border);border-radius:10px;
    padding:24px 28px 34px;margin-top:14px;}}
.canto-titulo{{font-family:var(--serif);font-size:1.5rem;font-weight:400;
    color:var(--accent);margin-bottom:16px;letter-spacing:.02em;
    border-bottom:1px solid var(--border);padding-bottom:10px;}}
.acorde{{background:var(--cbg);color:var(--cfg);border-radius:3px;padding:0 3px;font-weight:600;}}
.etiqueta{{color:var(--lblfg);font-weight:700;}}
.par{{break-inside:avoid-column;page-break-inside:avoid;display:block;margin-bottom:2px;}}
.par-sep{{height:14px;break-inside:avoid-column;}}
/* setlist items */
.sl-item{{
    display:flex;align-items:center;gap:10px;
    padding:8px 12px;border-radius:6px;
    background:var(--surf2);border:1px solid var(--border);
    margin-bottom:6px;cursor:grab;transition:border-color .12s;}}
.sl-item:hover{{border-color:var(--accent);}}
.sl-item.activo{{border-color:var(--accent);background:var(--cbg);}}
.sl-num{{font-family:var(--mono);font-size:.68rem;color:var(--muted);
    min-width:22px;text-align:right;}}
.sl-titulo{{flex:1;font-family:var(--mono);font-size:.78rem;
    color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.sl-tono{{font-size:.65rem;color:var(--cfg);background:var(--cbg);
    border:1px solid var(--accdim);border-radius:10px;padding:1px 7px;}}
</style>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
"""

# ─────────────────────────────────────────────────────────────────────
#  MODO PRESENTACIÓN — HTML autónomo fullscreen
# ─────────────────────────────────────────────────────────────────────
def render_presentacion(setlist_data, idx_actual, tema):
    """
    setlist_data: list of {titulo, tono_orig, tono_dest, semitonos, es_menor, versos}
    Renderiza fullscreen con botones prev/next flotantes.
    """
    import streamlit.components.v1 as components

    items_json = json.dumps(setlist_data, ensure_ascii=False)
    bg     = '#0d0d0f' if tema == 'oscuro' else '#f5f2eb'
    surf   = '#141418' if tema == 'oscuro' else '#ffffff'
    text   = '#e8e4d8' if tema == 'oscuro' else '#1a1810'
    accent = '#c49b30' if tema == 'oscuro' else '#8a6010'
    cbg    = '#1e1808' if tema == 'oscuro' else '#fdf3d0'
    cfg    = '#f0c060' if tema == 'oscuro' else '#7a4800'
    muted  = '#54525f' if tema == 'oscuro' else '#7a7060'
    border = '#2a2a35' if tema == 'oscuro' else '#d4cdb8'

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:{bg};color:{text};font-family:'JetBrains Mono',monospace;
     overflow-x:hidden;min-height:100vh;}}
#header{{
    position:sticky;top:0;z-index:100;
    background:{surf};border-bottom:1px solid {border};
    padding:10px 20px;display:flex;align-items:center;
    justify-content:space-between;gap:16px;
}}
#titulo-header{{
    font-family:'EB Garamond',serif;font-size:1.2rem;
    color:{accent};flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}}
#tono-header{{
    font-size:.72rem;color:{cfg};background:{cbg};
    border:1px solid #5e4718;border-radius:12px;padding:2px 10px;
    font-family:'JetBrains Mono',monospace;white-space:nowrap;
}}
#progress{{
    font-family:'JetBrains Mono',monospace;font-size:.7rem;
    color:{muted};white-space:nowrap;
}}
#canto-body{{
    padding:28px 32px 120px;
    font-size:18px;line-height:1.7;
}}
.acorde{{color:{cfg};font-weight:700;}}
.etiqueta{{color:#7cb4f0;font-weight:700;}}
/* Nav flotante */
#nav{{
    position:fixed;bottom:24px;left:50%;transform:translateX(-50%);
    display:flex;gap:12px;align-items:center;
    background:{surf};border:1px solid {border};
    border-radius:40px;padding:8px 20px;
    box-shadow:0 4px 24px rgba(0,0,0,.5);z-index:200;
}}
.nav-btn{{
    background:none;border:1px solid {border};
    color:{text};border-radius:20px;padding:6px 18px;
    font-family:'JetBrains Mono',monospace;font-size:.8rem;
    cursor:pointer;transition:border-color .14s,background .14s;
}}
.nav-btn:hover{{border-color:{accent};background:{cbg};}}
.nav-btn:disabled{{opacity:.3;cursor:default;}}
#nav-titulo{{
    font-size:.72rem;color:{muted};
    max-width:180px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
    text-align:center;
}}
#exit-btn{{
    position:fixed;top:12px;right:16px;z-index:300;
    background:none;border:1px solid {border};color:{muted};
    border-radius:6px;padding:4px 12px;font-size:.72rem;
    cursor:pointer;font-family:'JetBrains Mono',monospace;
}}
#exit-btn:hover{{border-color:{accent};color:{accent};}}
/* setlist lateral mini */
#setlist-mini{{
    position:fixed;left:0;top:50%;transform:translateY(-50%);
    display:flex;flex-direction:column;gap:4px;
    padding:8px 6px;z-index:150;
}}
.dot{{
    width:8px;height:8px;border-radius:50%;
    background:{border};cursor:pointer;transition:background .12s,transform .12s;
}}
.dot.activo{{background:{accent};transform:scale(1.4);}}
.dot:hover{{background:{accent};}}
</style>
</head>
<body>
<div id="header">
  <div id="titulo-header"></div>
  <div id="tono-header"></div>
  <div id="progress"></div>
</div>
<div id="canto-body"></div>
<div id="setlist-mini"></div>
<div id="nav">
  <button class="nav-btn" id="prev-btn" onclick="navegar(-1)">&#8592; Anterior</button>
  <div id="nav-titulo"></div>
  <button class="nav-btn" id="next-btn" onclick="navegar(1)">Siguiente &#8594;</button>
</div>
<button id="exit-btn" onclick="salir()">✕ Salir</button>

<script>
const ITEMS = {items_json};
let idx = {idx_actual};

const ETIQUETAS = ['intro','coro','puente','final','estrofa','sigue'];

function escapar(t){{return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}}

function renderCanto(){{
    const item = ITEMS[idx];
    // Header
    document.getElementById('titulo-header').textContent = item.titulo;
    const sfx = item.es_menor ? 'm' : '';
    document.getElementById('tono-header').textContent =
        item.tono_orig + '  →  ' + item.tono_dest + sfx;
    document.getElementById('progress').textContent =
        (idx+1) + ' / ' + ITEMS.length;
    // Nav
    document.getElementById('prev-btn').disabled = idx === 0;
    document.getElementById('next-btn').disabled = idx === ITEMS.length - 1;
    const nextItem = idx < ITEMS.length-1 ? ITEMS[idx+1].titulo : '';
    document.getElementById('nav-titulo').textContent = nextItem ? '→ ' + nextItem.substring(0,30) : '';
    // Dots
    const mini = document.getElementById('setlist-mini');
    mini.innerHTML = '';
    ITEMS.forEach((_,i) => {{
        const d = document.createElement('div');
        d.className = 'dot' + (i===idx ? ' activo' : '');
        d.title = ITEMS[i].titulo;
        d.onclick = () => {{ idx=i; renderCanto(); }};
        mini.appendChild(d);
    }});
    // Cuerpo
    let html = '';
    const versos = item.versos;
    let i = 0;
    while(i < versos.length){{
        const v = versos[i];
        const tu = v.texto.trim().toUpperCase();
        const esSecc = ['INTRO','CORO','PUENTE','ESTROFA','FINAL'].some(e => tu.startsWith(e));
        if(esSecc && i > 0) html += '<br>';
        if(v.tipo==='acordes' && i+1<versos.length && versos[i+1].tipo==='letra'){{
            html += '<div style="margin-bottom:2px">';
            html += renderAcordes(v.texto);
            html += '<br>' + escapar(versos[i+1].texto) + '</div>';
            i+=2;
        }} else {{
            if(v.tipo==='acordes') html += '<div>' + renderAcordes(v.texto) + '</div>';
            else html += '<div>' + escapar(v.texto) + '</div>';
            i++;
        }}
    }}
    document.getElementById('canto-body').innerHTML = html;
    window.scrollTo(0,0);
}}

function renderAcordes(linea){{
    return linea.split(/(\s+)/).map(p => {{
        if(!p || /^\s+$/.test(p)) return p.replace(/ /g,'&nbsp;');
        let pl = p.replace(/[\(\)\[\]\.,:]/g,'').replace(/^(\/{{2,3}}|\|+)+/,'').replace(/(\/{{2,3}}|\|+)+$/,'');
        if(/^[A-G][#b]?(m|Maj|maj|M|dim|dis|aug|aum|sus|add)?[\d]*(\/[A-G][#b]?)?$/.test(pl))
            return '<span class="acorde">'+p+'</span>';
        if(ETIQUETAS.includes(pl.toLowerCase()))
            return '<span class="etiqueta">'+p+'</span>';
        return escapar(p);
    }}).join('');
}}

function navegar(dir){{
    idx = Math.max(0, Math.min(ITEMS.length-1, idx+dir));
    renderCanto();
}}

function salir(){{
    window.parent.postMessage({{type:'salir_presentacion'}},'*');
}}

document.addEventListener('keydown', e => {{
    if(e.key==='ArrowRight'||e.key==='ArrowDown') navegar(1);
    if(e.key==='ArrowLeft'||e.key==='ArrowUp') navegar(-1);
    if(e.key==='Escape') salir();
}});

renderCanto();
</script>
</body></html>"""

    components.html(html, height=700, scrolling=True)


# ─────────────────────────────────────────────────────────────────────
#  APP PRINCIPAL
# ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title='Estribillos con Acordes',
    page_icon='🎵',
    layout='wide',
    initial_sidebar_state='collapsed'
)

for k, v in [('seleccion', None), ('tema', 'oscuro'),
             ('setlist', []),        # [{titulo, semitonos, t_dest, es_menor}]
             ('modo', 'cancionero'), # 'cancionero' | 'setlist' | 'presentacion'
             ('pres_idx', 0)]:
    if k not in st.session_state:
        st.session_state[k] = v

with st.spinner('Cargando cancionero…'):
    canciones = cargar_cancionero()

if not canciones:
    st.error('⚠️ No se encontró el PDF ni el cache.')
    st.stop()

titulos = [c['titulo'] for c in canciones]

# ─────────────────────────────────────────────────────────────────────
#  MODO PRESENTACIÓN — ocupa toda la pantalla
# ─────────────────────────────────────────────────────────────────────
if st.session_state.modo == 'presentacion':
    st.markdown(get_css(st.session_state.tema), unsafe_allow_html=True)
    # Ocultar TODO excepto el componente
    st.markdown("""
    <style>
    .stApp > div > div > div > div:first-child { padding-top: 0 !important; }
    [data-testid="stVerticalBlock"] > div { gap: 0 !important; }
    </style>""", unsafe_allow_html=True)

    # Construir datos del setlist para el componente
    setlist_data = []
    for item in st.session_state.setlist:
        c = next((x for x in canciones if x['titulo'] == item['titulo']), None)
        if c:
            t_base, es_menor = obtener_tono_base(c['tono'])
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

# ── HEADER ────────────────────────────────────────────────────────────
st.markdown(
    '<div class="sb-header">'
    '<h1>📖 Estribillos con Acordes</h1>'
    '<span>Cancionero Digital · 2020</span>'
    '</div>', unsafe_allow_html=True
)

# ── TABS: Cancionero / Setlist ────────────────────────────────────────
tab_names = ['🎵 Cancionero', f'📋 Setlist ({len(st.session_state.setlist)})']
tab1, tab2 = st.tabs(tab_names)

# ═══════════════════════════════════════════════════════════════════
#  TAB 1 — CANCIONERO
# ═══════════════════════════════════════════════════════════════════
with tab1:
    # Stats
    st.markdown(
        f'<div class="stat-row">'
        f'<div class="stat-badge"><b>{len(canciones)}</b>&nbsp;cantos</div>'
        f'<div class="stat-badge">📋&nbsp;<b>{len(st.session_state.setlist)}</b>&nbsp;en setlist</div>'
        f'</div>', unsafe_allow_html=True
    )

    # Selector + agregar al setlist
    def on_select():
        st.session_state.seleccion = st.session_state.sel_widget

    idx_def = 0
    if st.session_state.seleccion and st.session_state.seleccion in titulos:
        idx_def = titulos.index(st.session_state.seleccion)

    col_sel, col_add = st.columns([5, 1])
    with col_sel:
        st.selectbox('Canto', titulos, index=idx_def,
                     label_visibility='collapsed',
                     key='sel_widget', on_change=on_select)

    seleccion = st.session_state.seleccion or titulos[0]
    cancion   = next(c for c in canciones if c['titulo'] == seleccion)
    t_base, es_menor = obtener_tono_base(cancion['tono'])
    idx_base  = ESCALA.index(t_base) if t_base in ESCALA else 0
    ya_en_sl  = any(x['titulo'] == seleccion for x in st.session_state.setlist)

    with col_add:
        if ya_en_sl:
            if st.button('✓ En setlist', use_container_width=True, key='btn_add', disabled=True):
                pass
        else:
            if st.button('+ Setlist', use_container_width=True, key='btn_add'):
                # Agrega con la transposición actual (se determina abajo, usamos defaults)
                pass  # se maneja después de calcular semitonos

    # Controles
    c1, c2, c3, c4, c5, c6 = st.columns([1.2, 1.4, 1, 1, 1, 1])

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
            t_dest    = st.selectbox('T', ESCALA, index=idx_base,
                                     label_visibility='collapsed', key='sel_tono')
            semitonos = (ESCALA.index(t_dest) - idx_base) % 12
        else:
            semitonos = int(st.number_input('S', -12, 12, 0,
                                            label_visibility='collapsed', key='num_semi'))
            t_dest    = ESCALA[(idx_base + semitonos) % 12]
    with c4:
        tamano = st.slider('F', 13, 42, 18, label_visibility='collapsed', key='slider_font')
    with c5:
        cols_v = st.radio('Vista', ['1 columna', '2 columnas'],
                          horizontal=True, label_visibility='collapsed', key='radio_cols')
    with c6:
        tema_label = '☀️ Claro' if st.session_state.tema == 'oscuro' else '🌙 Oscuro'
        if st.button(tema_label, use_container_width=True, key='btn_tema'):
            st.session_state.tema = 'claro' if st.session_state.tema == 'oscuro' else 'oscuro'
            st.rerun()

    # Botón agregar al setlist (ahora que tenemos semitonos)
    if not ya_en_sl:
        # Re-render the button properly using a form approach via session state
        if st.session_state.get('_add_trigger'):
            st.session_state.setlist.append({
                'titulo'  : seleccion,
                'semitonos': semitonos,
                't_dest'  : t_dest,
                'es_menor': es_menor
            })
            st.session_state._add_trigger = False
            st.rerun()

    # Lógica real del botón agregar
    if not ya_en_sl:
        if st.button(f'➕ Agregar "{seleccion[:35]}…" al setlist en {t_dest}', key='btn_add2'):
            st.session_state.setlist.append({
                'titulo'  : seleccion,
                'semitonos': semitonos,
                't_dest'  : t_dest,
                'es_menor': es_menor
            })
            st.rerun()
    else:
        st.info(f'✓ Ya está en el setlist en tono {t_dest}')

    # Indicador transposición
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

    # PDF
    sfx_pdf   = 'm' if es_menor else ''
    pdf_bytes = generar_pdf(cancion, semitonos, t_dest, es_menor)
    nombre_f  = re.sub(r'[^\w\s-]', '', cancion['titulo'])[:38].strip().replace(' ', '_')
    st.download_button(
        label     = f'⬇ PDF — {t_dest}{sfx_pdf}',
        data      = pdf_bytes,
        file_name = f'{nombre_f}_{t_dest}{sfx_pdf}.pdf',
        mime      = 'application/pdf',
        key       = 'dl_pdf'
    )

    st.divider()

    # Render canto
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

# ═══════════════════════════════════════════════════════════════════
#  TAB 2 — SETLIST
# ═══════════════════════════════════════════════════════════════════
with tab2:
    if not st.session_state.setlist:
        st.markdown(
            '<div style="text-align:center;padding:60px 20px;color:var(--muted,#54525f)">'
            '<div style="font-size:3rem">📋</div>'
            '<div style="font-family:\'EB Garamond\',serif;font-size:1.3rem;margin:12px 0">Setlist vacío</div>'
            '<div style="font-family:monospace;font-size:.8rem">Ve al Cancionero, selecciona un canto<br>'
            'y presiona <b>+ Setlist</b> para agregarlo.</div>'
            '</div>', unsafe_allow_html=True
        )
    else:
        # Botón presentar
        col_pres, col_clear = st.columns([3, 1])
        with col_pres:
            if st.button('🎬 Iniciar Presentación', use_container_width=True, key='btn_presentar',
                         type='primary'):
                st.session_state.modo = 'presentacion'
                st.session_state.pres_idx = 0
                st.rerun()
        with col_clear:
            if st.button('🗑 Vaciar', use_container_width=True, key='btn_clear'):
                st.session_state.setlist = []
                st.rerun()

        st.markdown(f'**{len(st.session_state.setlist)} cantos** en el setlist')
        st.divider()

        # Lista con controles de reorden y eliminación
        to_delete = None
        to_move   = None  # (idx, direction)

        for i, item in enumerate(st.session_state.setlist):
            c_num, c_titulo, c_tono, c_up, c_down, c_del = st.columns([.4, 4, .8, .4, .4, .4])

            with c_num:
                st.markdown(
                    f'<div style="text-align:right;padding-top:8px;'
                    f'font-family:monospace;font-size:.75rem;color:var(--muted,#54525f)">'
                    f'{i+1}</div>', unsafe_allow_html=True
                )
            with c_titulo:
                titulo_corto = item['titulo'][:55] + ('…' if len(item['titulo']) > 55 else '')
                st.markdown(
                    f'<div style="padding-top:8px;font-family:monospace;'
                    f'font-size:.8rem;color:var(--text,#e8e4d8)">{titulo_corto}</div>',
                    unsafe_allow_html=True
                )
            with c_tono:
                sfx = 'm' if item['es_menor'] else ''
                st.markdown(
                    f'<div style="padding-top:6px">'
                    f'<span class="tono-pill" style="font-size:.7rem">'
                    f'{item["t_dest"]}{sfx}</span></div>',
                    unsafe_allow_html=True
                )
            with c_up:
                if i > 0:
                    if st.button('↑', key=f'up_{i}', use_container_width=True):
                        to_move = (i, -1)
            with c_down:
                if i < len(st.session_state.setlist) - 1:
                    if st.button('↓', key=f'dn_{i}', use_container_width=True):
                        to_move = (i, 1)
            with c_del:
                if st.button('✕', key=f'del_{i}', use_container_width=True):
                    to_delete = i

        # Aplicar cambios fuera del loop
        if to_delete is not None:
            st.session_state.setlist.pop(to_delete)
            st.rerun()
        if to_move is not None:
            idx_m, direction = to_move
            sl = st.session_state.setlist
            sl[idx_m], sl[idx_m + direction] = sl[idx_m + direction], sl[idx_m]
            st.rerun()

        st.divider()
        # Preview del primer canto
        if st.session_state.setlist:
            first = st.session_state.setlist[0]
            c_prev = next((x for x in canciones if x['titulo'] == first['titulo']), None)
            if c_prev:
                st.markdown(
                    f'<div style="font-family:monospace;font-size:.72rem;'
                    f'color:var(--muted,#54525f);margin-bottom:6px">'
                    f'PRIMER CANTO:</div>', unsafe_allow_html=True
                )
                st.markdown(
                    f'<div style="font-family:\'EB Garamond\',serif;font-size:1.1rem;'
                    f'color:var(--accent,#c49b30)">{c_prev["titulo"]}</div>',
                    unsafe_allow_html=True
                )

# Footer
st.markdown(
    f'<div style="margin-top:32px;text-align:center;font-family:monospace;'
    f'font-size:.66rem;color:var(--muted,#54525f);'
    f'border-top:1px solid var(--border,#2a2a35);padding-top:10px;margin-bottom:20px;">'
    f'Estribillos con Acordes 2020 · {len(canciones)} cantos</div>',
    unsafe_allow_html=True
)