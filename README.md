# 📖 Estribillos con Acordes 2020

Cancionero digital interactivo con 327 cantos, transposición automática de acordes y exportación a PDF.

## ✨ Funcionalidades

| Feature | Descripción |
|---|---|
| 🔍 Búsqueda en tiempo real | Por número o nombre del canto |
| 🎵 Transposición | Por tono destino o por semitonos (capo) |
| 📑 Índice lateral | Filtro por tono, búsqueda, solo favoritos |
| ⭐ Favoritos | Guarda cantos rápidamente en sesión |
| ⬇ Exportar PDF | PDF con acordes alineados sobre la letra, ya transpuesto |
| 🎬 Modo presentación | Oculta controles para proyectar en pantalla |
| ☀️ / 🌙 Tema claro/oscuro | Cambio de tema en un clic |
| ⚡ Carga instantánea | Cache JSON — no parsea el PDF en cada inicio |

## 🚀 Deploy en Streamlit Cloud

1. Haz fork de este repositorio
2. Ve a [share.streamlit.io](https://share.streamlit.io) e inicia sesión con GitHub
3. Selecciona este repo, rama `main`, archivo `app.py`
4. Deploy — el link público queda listo en ~2 minutos

## 🖥 Correr localmente

```bash
git clone https://github.com/Ibarrera18/Estribillos-con-acordes-2020.git
cd Estribillos-con-acordes-2020
pip install -r requirements.txt
streamlit run app.py
```

## 📁 Estructura

```
├── app.py                          # Aplicación principal
├── cancionero.json                 # Cache pre-generado (327 cantos)
├── ESTRIBILLOS CON ACORDES 2020.pdf
└── requirements.txt
```

## 📦 Requirements

```
streamlit
pdfplumber
fpdf2
```

## 🔧 Cómo funciona

- **Extracción**: `pdfplumber` con `layout=True` preserva la posición original de los acordes
- **Detección**: Regex que identifica acordes anglosajones con sufijos (`m`, `Maj7`, `dim`, `sus`, `/bajo`)
- **Transposición**: Mapeo matemático sobre escala cromática de 12 semitonos
- **Cache**: El PDF se parsea una sola vez y se guarda como JSON para carga instantánea

---
Desarrollado con Python + Streamlit
