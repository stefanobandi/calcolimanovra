import streamlit as st
import numpy as np
import pandas as pd
import math
import base64

# ==========================================
# 1. CONFIGURAZIONE E DATABASE
# ==========================================
st.set_page_config(page_title="Vector Towing Simulator", layout="wide")

# Database dettagliato Rimorchiatori (Dimensioni in metri, BP in tonnellate)
# Forme stilizzate ma basate su tipologie reali
tug_db = {
    "ASD 70 ton": {"bp": 70.0, "L": 32.0, "B": 11.0, "color": "#E67E22"}, # Arancio
    "RSD 80 ton": {"bp": 80.0, "L": 25.0, "B": 13.0, "color": "#E74C3C"}, # Rosso (più tozzo)
    "VWT 55 ton": {"bp": 55.0, "L": 30.0, "B": 10.0, "color": "#3498DB"}, # Blu (affusolato)
    "Custom":      {"bp": None, "L": 30.0, "B": 11.0, "color": "#95A5A6"}  # Grigio
}

# Dimensioni Nave fisse
SHIP_L = 200.0
SHIP_B = 20.0

# Parametri grafici base
TOWLINE_L_M = 50.0 # Lunghezza cavo fissa in metri

# ==========================================
# 2. BARRA LATERALE (CONTROLLI GLOBALI)
# ==========================================
st.sidebar.title("🎮 Tactical Control")

st.sidebar.subheader("Ship Status")
velocita_nave = st.sidebar.slider("Ship Speed (knots)", -5.0, 15.0, 6.0, 0.5)

st.sidebar.markdown("---")
st.sidebar.subheader("Camera & Display")
focus_on = st.sidebar.radio(
    "VIEW MODE:",
    options=[
        "Full Scene (Auto-center)", 
        "Bow Assembly",        # Prua nave + cavo + Tug
        "Bow Tug (central)",   # Solo Rimorchiatore Prua
        "Stern Assembly",      # Poppa nave + cavo + Tug
        "Stern Tug (central)"  # Solo Rimorchiatore Poppa
    ]
)

# Controllo ZOOM dinamico (per vector graphics)
zoom_level = st.sidebar.slider("🔎 Visual Scale", 0.5, 3.0, 1.0, 0.1)

# ==========================================
# 3. AREA PRINCIPALE (INTESTAZIONE E INPUT)
# ==========================================
st.title("Vector Towing Force Simulator")

# Banner Work in Progress
st.markdown("""
    <div style='background-color: #ff9800; padding: 20px; text-align: center; border-radius: 10px; border: 2px dashed #e65100; margin-bottom: 20px;'>
        <h1 style='color: white; margin: 0; text-transform: uppercase; font-size: 2.5rem;'>🚧 Work in Progress 🚧</h1>
        <p style='color: white; font-size: 1.2rem; margin-top: 10px;'>This application is currently under heavy construction. Features, physics, and data are subject to change.</p>
    </div>
""", unsafe_allow_html=True)

# Subtitle & Copyright
st.markdown("#### For technical inquiries, feedback, or data contributions, please contact: [stefano.bandi22@gmail.com](mailto:stefano.bandi22@gmail.com)")
st.markdown("*© 2026 Stefano Bandi - All rights reserved. Commercial use is strictly prohibited.*")
st.markdown("---")

st.markdown(f"**Scenario:** Ship length **{SHIP_L}m**, width **{SHIP_B}m** moving at **{velocita_nave} knots**.")

col_prua, col_poppa = st.columns(2)

# Input Prua
with col_prua:
    st.subheader("Bow Tug (Prua) ⬆️")
    s_prua = st.selectbox("Type", list(tug_db.keys()), key="sel_prua")
    
    data_prua = tug_db[s_prua].copy()
    if s_prua == "Custom":
        data_prua["bp"] = st.number_input("Max BP (t) - Bow", 10.0, 200.0, 60.0, step=1.0)
        data_prua["L"] = st.number_input("Length (m) - Bow", 15.0, 50.0, 30.0)
        data_prua["B"] = st.number_input("Beam (m) - Bow", 5.0, 20.0, 11.0)
        
    ang_prua = st.slider("Angle (°)", -90, 90, 10, 1, key="ang_prua_s", help="0° = straight ahead. Positive = Starboard")
    int_prua = st.slider("Intensity (t)", 0.0, float(data_prua["bp"]), 20.0, 0.5, key="int_prua_s")

# Input Poppa
with col_poppa:
    st.subheader("Stern Tug (Poppa) ⬇️")
    s_poppa = st.selectbox("Type", list(tug_db.keys()), key="sel_poppa")
    
    data_poppa = tug_db[s_poppa].copy()
    if s_poppa == "Custom":
        data_poppa["bp"] = st.number_input("Max BP (t) - Stern", 10.0, 200.0, 60.0, step=1.0)
        data_poppa["L"] = st.number_input("Length (m) - Stern", 15.0, 50.0, 30.0)
        data_poppa["B"] = st.number_input("Beam (m) - Stern", 5.0, 20.0, 11.0)
        
    ang_poppa = st.slider("Angle (°)", -90, 90, -15, 1, key="ang_poppa_s", help="0° = straight astern. Positive = Starboard")
    int_poppa = st.slider("Intensity (t)", 0.0, float(data_poppa["bp"]), 30.0, 0.5, key="int_poppa_s")


# ==========================================
# 4. MOTORE GRAFICO SVG (GENERATORE VETTORIALE)
# ==========================================

def generate_svg_scene():
    # --- Geometria del Mondo (Coordinate Metriche) ---
    # Definiamo i punti chiave in metri rispetto al centro nave (0,0)
    
    # Chocks (punti di attacco cavo) sulla nave
    chock_prua_y = SHIP_L / 2 - 5.0  # 5m dalla punta
    chock_poppa_y = -SHIP_L / 2 + 5.0 # 5m dallo specchio di poppa
    
    # Calcolo posizioni dei Tug (Trigonometria)
    rad_prua = math.radians(ang_prua)
    # Angolo 0 è Nord (Su), angoli positivi Est (Destra)
    tug_prua_x = TOWLINE_L_M * math.sin(rad_prua)
    tug_prua_y = chock_prua_y + TOWLINE_L_M * math.cos(rad_prua)
    
    rad_poppa = math.radians(ang_poppa)
    # Angolo 0 è Sud (Giù), angoli positivi Est (Destra)
    tug_poppa_x = TOWLINE_L_M * math.sin(rad_poppa)
    tug_poppa_y = chock_poppa_y - TOWLINE_L_M * math.cos(rad_poppa)
    
    # --- Definizione Sagome (SVG Paths in scala metrica) ---
    
    def get_ship_path():
        b2 = SHIP_B / 2
        l2 = SHIP_L / 2
        taper = 30.0
        d = f"M {b2} {-l2+2} "
        d += f"L {b2} {l2-taper} "
        d += f"C {b2} {l2-taper/2}, {b2*0.3} {l2}, 0 {l2} "
        d += f"C {-b2*0.3} {l2}, {-b2} {l2-taper/2}, {-b2} {l2-taper} "
        d += f"L {-b2} {-l2+2} "
        d += f"C {-b2} {-l2}, {b2} {-l2}, {b2} {-l2+2} Z"
        return d

    def get_tug_path(data):
        l, b = data["L"], data["B"]
        l2, b2 = l/2, b/2
        d = f"M {b2} {-l2+1} "
        d += f"L {b2} {l2-b*0.8} "
        d += f"C {b2} {l2}, {-b2} {l2}, {-b2} {l2-b*0.8} "
        d += f"L {-b2} {-l2+1} "
        d += f"C {-b2} {-l2}, {b2} {-l2}, {b2} {-l2+1} Z"
        return d
    
    # == LOGICA CAMERA (VIEWBOX) ==
    # Determiniamo l'area da inquadrare (in metri) basandoci su posizioni Cartesiane (Y-up)
    margin = 20.0
    
    # Punti estremi della scena (Nave + Tug + Cavi)
    min_x_m = min(-SHIP_B/2, tug_prua_x, tug_poppa_x) - margin
    max_x_m = max(SHIP_B/2, tug_prua_x, tug_poppa_x) + margin
    min_y_m = min(-SHIP_L/2, tug_prua_y, tug_poppa_y) - margin
    max_y_m = max(SHIP_L/2, tug_prua_y, tug_poppa_y) + margin
    
    if focus_on == "Full Scene (Auto-center)":
        ext_x = max(abs(min_x_m), abs(max_x_m))
        ext_y = max(abs(min_y_m), abs(max_y_m))
        vw, vh = ext_x * 2, ext_y * 2
        vx, vy = -ext_x, -ext_y
        
    elif focus_on == "Bow Assembly":
        vw = abs(max_x_m - min_x_m) + margin*2
        vh = abs(tug_prua_y - (chock_prua_y - 20.0))
        vx = (max_x_m + min_x_m)/2 - vw/2
        vy = chock_prua_y - 20.0

    elif focus_on == "Bow Tug (central)":
        vw = 80.0
        vh = 80.0
        vx = tug_prua_x - vw/2
        vy = tug_prua_y - vh/2

    elif focus_on == "Stern Assembly":
        vw = abs(max_x_m - min_x_m) + margin*2
        vh = abs((chock_poppa_y + 20.0) - tug_poppa_y)
        vx = (max_x_m + min_x_m)/2 - vw/2
        vy = tug_poppa_y

    elif focus_on == "Stern Tug (central)":
        vw = 80.0
        vh = 80.0
        vx = tug_poppa_x - vw/2
        vy = tug_poppa_y - vh/2

    # Applichiamo lo zoom
    vw_scaled = vw / zoom_level
    vh_scaled = vh / zoom_level
    vx_scaled = vx + (vw - vw_scaled) / 2
    vy_scaled = vy + (vh - vh_scaled) / 2

    # --- Creazione Stringa SVG ---
    
    # RISOLUZIONE BUG: viewbox e sfondo rimossi/corretti
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="100%" height="600px" 
         viewBox="{vx_scaled} {-vy_scaled - vh_scaled} {vw_scaled} {vh_scaled}"
         style="background-color: #FFFFFF; border-radius: 8px; border: 1px solid #B0BEC5;"
         id="towing-svg">
         
        <style>
            .tug-hull {{ stroke: white; stroke-width: 0.8; filter: drop-shadow(0px 3px 3px rgba(0,0,0,0.3)); transition: all 0.3s ease; }}
            .ship-hull {{ fill: #263238; stroke: #546E7A; stroke-width: 1; }}
            .towline {{ stroke-width: 1.5; stroke-dasharray: 4; stroke: #78909C; fill: none; transition: stroke 0.3s; }}
            .vector-arrow {{ fill: #F1C40F; stroke: black; stroke-width: 0.5; }}
            .text-label {{ font-family: 'Roboto Condensed', sans-serif; font-weight: bold; fill: white; pointer-events: none; text-anchor: middle; }}
            .text-data {{ font-family: monospace; fill: #263238; text-anchor: start; font-size: 10px; }}
        </style>
    """
    
    # Flippiamo la Y internamente per lavorare in coordinate Cartesiane (Y-up) nel mondo virtuale
    svg += '<g transform="scale(1, -1)">'
    
    # == DISEGNO ELEMENTI ==
    
    # 1. Griglia di fondo stilizzata (Vector look)
    svg += '<g stroke="#E0E0E0" stroke-width="0.2" stroke-dasharray="2 10">'
    for i in range(-500, 501, 50):
        svg += f'<line x1="{i}" y1="-500" x2="{i}" y2="500" />'
        svg += f'<line x1="-500" y1="{i}" x2="500" y2="{i}" />'
    svg += '</g>'

    # 2. Nave
    svg += f'<path d="{get_ship_path()}" class="ship-hull" />'
    svg += f'<text x="0" y="0" class="text-label" transform="scale(1,-1)" font-size="12">SHIP</text>'
    
    # Segna Chocks
    svg += f'<circle cx="0" cy="{chock_prua_y}" r="1.5" fill="#E74C3C" stroke="black" stroke-width="0.5"/>'
    svg += f'<circle cx="0" cy="{chock_poppa_y}" r="1.5" fill="#E74C3C" stroke="black" stroke-width="0.5"/>'

    def draw_tug_assembly(tx, ty, angle_deg, intensity, data, label_raw, is_bow):
        assembly = ""
        orig_y = chock_prua_y if is_bow else chock_poppa_y
        stress = intensity / data["bp"] if data["bp"] > 0 else 0
        r_line = int(120 + stress * 135)
        g_line = int(144 * (1-stress))
        b_line = int(156 * (1-stress))
        line_col = f"rgb({r_line},{g_line},{b_line})"
        
        assembly += f'<line x1="0" y1="{orig_y}" x2="{tx}" y2="{ty}" class="towline" stroke="{line_col}" />'
        
        rot = angle_deg if is_bow else angle_deg + 180
        assembly += f'<g transform="translate({tx}, {ty}) rotate({-rot})">'
        assembly += f'<path d="{get_tug_path(data)}" class="tug-hull" fill="{data["color"]}" />'
        label = label_raw.split()[0]
        assembly += f'<text x="0" y="0" class="text-label" transform="rotate({rot}) scale(1,-1)" font-size="7">{label}</text>'
        
        arrow_l = intensity / 2.0
        if arrow_l > 2:
            assembly += f'<line x1="0" y1="{data["L"]/2}" x2="0" y2="{data["L"]/2 + arrow_l}" stroke="#F1C40F" stroke-width="1.5" marker-end="url(#arrowhead)"/>'
        assembly += '</g>'
        
        assembly += f'<g transform="translate({tx+data["B"]/2+2}, {ty}) scale(1,-1)">'
        assembly += f'<text x="0" y="-8" class="text-data" font-weight="bold">{label}</text>'
        assembly += f'<text x="0" y="2" class="text-data">Pull: {intensity:.1f}t</text>'
        assembly += f'<text x="0" y="12" class="text-data">Ang: {angle_deg}°</text>'
        assembly += '</g>'
        return assembly

    svg += draw_tug_assembly(tug_prua_x, tug_prua_y, ang_prua, int_prua, data_prua, s_prua, is_bow=True)
    svg += draw_tug_assembly(tug_poppa_x, tug_poppa_y, ang_poppa, int_poppa, data_poppa, s_poppa, is_bow=False)

    svg += """
    <defs>
        <marker id="arrowhead" markerWidth="5" markerHeight="5" refX="2.5" refY="2.5" orient="auto">
            <polygon points="0 0, 5 2.5, 0 5" fill="#F1C40F" />
        </marker>
    </defs>
    """
    svg += "</g></svg>"
    return svg

# ==========================================
# 5. CALCOLI FISICI E TABELLA RISULTATI
# ==========================================

chock_prua_y_m = SHIP_L / 2 - 5.0
chock_poppa_y_m = -SHIP_L / 2 + 5.0

force_prua_x = int_prua * math.sin(math.radians(ang_prua))
moment_prua = force_prua_x * chock_prua_y_m

force_poppa_x = int_poppa * math.sin(math.radians(ang_poppa))
moment_poppa = force_poppa_x * chock_poppa_y_m

total_moment = moment_prua + moment_poppa

res_prua = data_prua["bp"] - int_prua
res_poppa = data_poppa["bp"] - int_poppa

df_results = pd.DataFrame({
    "Parametro": [
        "Velocità Nave", 
        "Tug Prua (Tiro / Max)", 
        "Tug Prua (Riserva Disponibile)",
        "Tug Poppa (Tiro / Max)", 
        "Tug Poppa (Riserva Disponibile)",
        "MOMENTO ROTAZIONE TOTALE (Tug)"
    ],
    "Valore": [
        f"{velocita_nave} nodi",
        f"{int_prua:.1f} t / {data_prua['bp']:.0f} t",
        f"{res_prua:.1f} t",
        f"{int_poppa:.1f} t / {data_poppa['bp']:.0f} t",
        f"{res_poppa:.1f} t",
        f"{total_moment:.0f} t·m"
    ],
    "Unità": ["kn", "t", "t", "t", "t", "t·m"]
})

moment_help = "Rotating Starboard ↻" if total_moment > 50 else ("Rotating Port ↺" if total_moment < -50 else "Pushing Straight")

# ==========================================
# 6. GENERAZIONE E VISUALIZZAZIONE
# ==========================================

with st.spinner("Rendering vector scene..."):
    svg_content = generate_svg_scene()
    
    b64_svg = base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')
    html_img = f'<img src="data:image/svg+xml;base64,{b64_svg}" style="width: 100%; border-radius: 8px;">'
    
    st.markdown(html_img, unsafe_allow_html=True)
    st.caption(f"Vector Tactical View: {focus_on}")

st.markdown("---")
st.metric(label=f"Total Tugs Torque ({moment_help})", value=df_results.iloc[5]["Valore"], delta=f"{total_moment:.0f} t·m")

st.subheader("📋 Simulation Analytical Results")
st.dataframe(df_results, use_container_width=True, hide_index=True)
