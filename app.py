import streamlit as st
import numpy as np
import pandas as pd
import math
import base64

# ==========================================
# 0. INIZIALIZZAZIONE STATO (PER TASTO RESET)
# ==========================================
# Inizializziamo le variabili nella sessione per poterle modificare tramite il tasto reset
if "velocita_nave" not in st.session_state:
    st.session_state.velocita_nave = 6.0
if "ang_prua_s" not in st.session_state:
    st.session_state.ang_prua_s = 10
if "int_prua_s" not in st.session_state:
    st.session_state.int_prua_s = 20.0
if "ang_poppa_s" not in st.session_state:
    st.session_state.ang_poppa_s = -15
if "int_poppa_s" not in st.session_state:
    st.session_state.int_poppa_s = 30.0

def reset_simulation():
    st.session_state.velocita_nave = 5.0
    st.session_state.ang_prua_s = 0
    st.session_state.int_prua_s = 0.0
    st.session_state.ang_poppa_s = 0
    st.session_state.int_poppa_s = 0.0

# ==========================================
# 1. CONFIGURAZIONE E DATABASE
# ==========================================
st.set_page_config(page_title="Vector Towing Simulator", layout="wide")

# Database dettagliato Rimorchiatori (Dimensioni in metri, BP in tonnellate)
tug_db = {
    "ASD 70 ton": {"bp": 70.0, "L": 32.0, "B": 11.0, "color": "#E67E22"},
    "RSD 80 ton": {"bp": 80.0, "L": 25.0, "B": 13.0, "color": "#E74C3C"},
    "VWT 55 ton": {"bp": 55.0, "L": 30.0, "B": 10.0, "color": "#3498DB"},
    "Custom":      {"bp": None, "L": 30.0, "B": 11.0, "color": "#95A5A6"}
}

# Dimensioni Nave fisse
SHIP_L = 200.0
SHIP_B = 20.0
TOWLINE_L_M = 50.0 # Lunghezza cavo fissa in metri

# ==========================================
# 2. BARRA LATERALE (CONTROLLI GLOBALI)
# ==========================================
st.sidebar.title("🎮 Tactical Control")

# Tasto Reset in cima alla barra laterale
st.sidebar.button("🔄 Reset to Default (5kt, 0t pull)", on_click=reset_simulation, use_container_width=True)
st.sidebar.markdown("---")

st.sidebar.subheader("Ship Status")
# Colleghiamo lo slider alla session_state tramite key
velocita_nave = st.sidebar.slider("Ship Speed (knots)", -5.0, 15.0, key="velocita_nave", step=0.5)

st.sidebar.markdown("---")
st.sidebar.subheader("Camera & Display")
focus_on = st.sidebar.radio(
    "VIEW MODE:",
    options=[
        "Full Scene (Auto-center)", 
        "Bow Assembly",        
        "Bow Tug (central)",   
        "Stern Assembly",      
        "Stern Tug (central)"  
    ]
)

# Controllo ZOOM
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
        
    ang_prua = st.slider("Angle (°)", -90, 90, step=1, key="ang_prua_s", help="0° = straight ahead. Positive = Starboard")
    int_prua = st.slider("Intensity (t)", 0.0, float(data_prua["bp"]), step=0.5, key="int_prua_s")

# Input Poppa
with col_poppa:
    st.subheader("Stern Tug (Poppa) ⬇️")
    s_poppa = st.selectbox("Type", list(tug_db.keys()), key="sel_poppa")
    
    data_poppa = tug_db[s_poppa].copy()
    if s_poppa == "Custom":
        data_poppa["bp"] = st.number_input("Max BP (t) - Stern", 10.0, 200.0, 60.0, step=1.0)
        data_poppa["L"] = st.number_input("Length (m) - Stern", 15.0, 50.0, 30.0)
        data_poppa["B"] = st.number_input("Beam (m) - Stern", 5.0, 20.0, 11.0)
        
    ang_poppa = st.slider("Angle (°)", -90, 90, step=1, key="ang_poppa_s", help="0° = straight astern. Positive = Starboard")
    int_poppa = st.slider("Intensity (t)", 0.0, float(data_poppa["bp"]), step=0.5, key="int_poppa_s")


# ==========================================
# 4. MOTORE GRAFICO SVG (Y-DOWN NATIVO)
# ==========================================

def generate_svg_scene():
    # In SVG nativo, il punto (0,0) è in alto a sinistra. La Y cresce verso il BASSO.
    # Posizioniamo il centro della nave a (0,0) logico.
    # Prua (Nord) corrisponde a Y negative. Poppa (Sud) a Y positive.
    
    chock_prua_y = -SHIP_L / 2 + 5.0  # Valore negativo = verso l'alto
    chock_poppa_y = SHIP_L / 2 - 5.0  # Valore positivo = verso il basso
    
    rad_prua = math.radians(ang_prua)
    tug_prua_x = TOWLINE_L_M * math.sin(rad_prua)
    # Sottraggo per andare ancora più in alto (verso Nord)
    tug_prua_y = chock_prua_y - TOWLINE_L_M * math.cos(rad_prua) 
    
    rad_poppa = math.radians(ang_poppa)
    tug_poppa_x = TOWLINE_L_M * math.sin(rad_poppa)
    # Sommo per andare ancora più in basso (verso Sud)
    tug_poppa_y = chock_poppa_y + TOWLINE_L_M * math.cos(rad_poppa)
    
    def get_ship_path():
        b2 = SHIP_B / 2
        l2 = SHIP_L / 2
        taper = 30.0
        # Disegno in coordinate Y-down
        d = f"M {b2} {l2-2} " # Poppa dritta
        d += f"L {b2} {-l2+taper} " # Linea dritta fino al taper prua
        d += f"C {b2} {-l2+taper/2}, {b2*0.3} {-l2}, 0 {-l2} " # Curva prua dritta
        d += f"C {-b2*0.3} {-l2}, {-b2} {-l2+taper/2}, {-b2} {-l2+taper} " # Curva prua sinistra
        d += f"L {-b2} {l2-2} " # Linea dritta sinistra
        d += f"C {-b2} {l2}, {b2} {l2}, {b2} {l2-2} Z" # Specchio poppa
        return d

    def get_tug_path(data):
        l, b = data["L"], data["B"]
        l2, b2 = l/2, b/2
        d = f"M {b2} {l2-1} "
        d += f"L {b2} {-l2+b*0.8} "
        d += f"C {b2} {-l2}, {-b2} {-l2}, {-b2} {-l2+b*0.8} "
        d += f"L {-b2} {l2-1} "
        d += f"C {-b2} {l2}, {b2} {l2}, {b2} {l2-1} Z"
        return d
    
    margin = 30.0
    
    min_x_m = min(-SHIP_B/2, tug_prua_x, tug_poppa_x) - margin
    max_x_m = max(SHIP_B/2, tug_prua_x, tug_poppa_x) + margin
    min_y_m = min(-SHIP_L/2, tug_prua_y, tug_poppa_y) - margin
    max_y_m = max(SHIP_L/2, tug_prua_y, tug_poppa_y) + margin
    
    if focus_on == "Full Scene (Auto-center)":
        # Calcolo per mantenere lo (0,0) della nave perfettamente al centro del canvas
        ext_x = max(abs(min_x_m), abs(max_x_m))
        ext_y = max(abs(min_y_m), abs(max_y_m))
        vw, vh = ext_x * 2, ext_y * 2
        vx, vy = -ext_x, -ext_y
        
    elif focus_on == "Bow Assembly":
        vw = abs(max_x_m - min_x_m) + margin*2
        vh = abs(chock_prua_y - tug_prua_y) + margin*2
        vx = (max_x_m + min_x_m)/2 - vw/2
        vy = min(chock_prua_y, tug_prua_y) - margin

    elif focus_on == "Bow Tug (central)":
        vw, vh = 80.0, 80.0
        vx, vy = tug_prua_x - vw/2, tug_prua_y - vh/2

    elif focus_on == "Stern Assembly":
        vw = abs(max_x_m - min_x_m) + margin*2
        vh = abs(tug_poppa_y - chock_poppa_y) + margin*2
        vx = (max_x_m + min_x_m)/2 - vw/2
        vy = min(chock_poppa_y, tug_poppa_y) - margin

    elif focus_on == "Stern Tug (central)":
        vw, vh = 80.0, 80.0
        vx, vy = tug_poppa_x - vw/2, tug_poppa_y - vh/2

    # Applichiamo lo zoom calcolando il nuovo centro e la nuova larghezza
    vw_scaled = vw / zoom_level
    vh_scaled = vh / zoom_level
    vx_scaled = vx + (vw - vw_scaled) / 2
    vy_scaled = vy + (vh - vh_scaled) / 2

    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="100%" height="600px" 
         viewBox="{vx_scaled} {vy_scaled} {vw_scaled} {vh_scaled}"
         style="background-color: #FFFFFF; border-radius: 8px; border: 1px solid #B0BEC5;"
         id="towing-svg">
         
        <style>
            .tug-hull {{ stroke: white; stroke-width: 0.8; filter: drop-shadow(0px 3px 3px rgba(0,0,0,0.3)); transition: all 0.3s ease; }}
            .ship-hull {{ fill: #2C3E50; stroke: #34495E; stroke-width: 1; }}
            .towline {{ stroke-width: 1.5; stroke-dasharray: 4; stroke: #7F8C8D; fill: none; transition: stroke 0.3s; }}
            .text-label {{ font-family: 'Arial', sans-serif; font-weight: bold; fill: white; pointer-events: none; text-anchor: middle; }}
            .text-data {{ font-family: monospace; fill: #2C3E50; text-anchor: start; font-size: 8px; font-weight: bold; background-color: rgba(255,255,255,0.7); }}
            .center-cross {{ stroke: #BDC3C7; stroke-width: 0.5; }}
        </style>
    """
    
    # Croce centrale per indicare il Pivot Point / Centro Nave
    svg += '<line x1="-10" y1="0" x2="10" y2="0" class="center-cross"/>'
    svg += '<line x1="0" y1="-10" x2="0" y2="10" class="center-cross"/>'

    # 1. Nave
    svg += f'<path d="{get_ship_path()}" class="ship-hull" />'
    svg += f'<text x="0" y="5" class="text-label" font-size="12">SHIP</text>'
    
    # 2. Chocks
    svg += f'<circle cx="0" cy="{chock_prua_y}" r="1.5" fill="#E74C3C" stroke="black" stroke-width="0.5"/>'
    svg += f'<circle cx="0" cy="{chock_poppa_y}" r="1.5" fill="#E74C3C" stroke="black" stroke-width="0.5"/>'

    # Funzione interna per assemblaggio Tug
    def draw_tug_assembly(tx, ty, angle_deg, intensity, data, label_raw, is_bow):
        assembly = ""
        orig_y = chock_prua_y if is_bow else chock_poppa_y
        
        # Colore cavo
        stress = intensity / data["bp"] if data["bp"] > 0 else 0
        r_line = int(127 + stress * 128)
        g_line = int(140 * (1-stress))
        b_line = int(141 * (1-stress))
        line_col = f"rgb({r_line},{g_line},{b_line})"
        
        assembly += f'<line x1="0" y1="{orig_y}" x2="{tx}" y2="{ty}" class="towline" stroke="{line_col}" />'
        
        # Rotazione Tug: in SVG positivo ruota in senso orario.
        # Poppa: aggiungiamo 180 gradi per girare il tug verso la nave
        rot = angle_deg if is_bow else angle_deg + 180
        
        assembly += f'<g transform="translate({tx}, {ty}) rotate({rot})">'
        assembly += f'<path d="{get_tug_path(data)}" class="tug-hull" fill="{data["color"]}" />'
        label = label_raw.split()[0]
        # Testo dentro il tug ruotato all'inverso per rimanere leggibile orizzontalmente
        assembly += f'<text x="0" y="3" class="text-label" transform="rotate({-rot})" font-size="7">{label}</text>'
        
        # Vettore Tiro (Freccia) disegnata verso prua del rimorchiatore
        arrow_l = intensity / 2.0
        if arrow_l > 2:
            assembly += f'<line x1="0" y1="{-data["L"]/2}" x2="0" y2="{-data["L"]/2 - arrow_l}" stroke="#F1C40F" stroke-width="1.5" marker-end="url(#arrowhead)"/>'
        assembly += '</g>'
        
        # Data Box esterno (fisso, non ruotato)
        assembly += f'<g transform="translate({tx+data["B"]/2+3}, {ty})">'
        assembly += f'<text x="0" y="-10" class="text-data">{label}</text>'
        assembly += f'<text x="0" y="0" class="text-data">Pull: {intensity:.1f}t</text>'
        assembly += f'<text x="0" y="10" class="text-data">Ang: {angle_deg}°</text>'
        assembly += '</g>'
        return assembly

    svg += draw_tug_assembly(tug_prua_x, tug_prua_y, ang_prua, int_prua, data_prua, s_prua, is_bow=True)
    svg += draw_tug_assembly(tug_poppa_x, tug_poppa_y, ang_poppa, int_poppa, data_poppa, s_poppa, is_bow=False)

    svg += """
    <defs>
        <marker id="arrowhead" markerWidth="5" markerHeight="5" refX="2.5" refY="2.5" orient="auto" markerUnits="strokeWidth">
            <polygon points="0 0, 5 2.5, 0 5" fill="#F1C40F" />
        </marker>
    </defs>
    </svg>
    """
    return svg

# ==========================================
# 5. CALCOLI FISICI E TABELLA RISULTATI
# ==========================================

# Calcolo semplificato Momento Torcente (Braccio positivo = mezzo scafo)
braccio_leva = SHIP_L / 2 - 5.0

# Forza X positiva = Tiro verso dritta (Starboard)
# Momento: Prua verso dritta spinge la nave in rotazione oraria (positivo)
force_prua_x = int_prua * math.sin(math.radians(ang_prua))
moment_prua = force_prua_x * braccio_leva

# Poppa verso dritta spinge la poppa a dritta, quindi la prua a sinistra (rotazione antioraria, negativo)
force_poppa_x = int_poppa * math.sin(math.radians(ang_poppa))
moment_poppa = -force_poppa_x * braccio_leva

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

with st.spinner("Rendering clean vector scene..."):
    svg_content = generate_svg_scene()
    
    b64_svg = base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')
    html_img = f'<img src="data:image/svg+xml;base64,{b64_svg}" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">'
    
    st.markdown(html_img, unsafe_allow_html=True)
    st.caption(f"Clean Vector View: {focus_on}")

st.markdown("---")
st.metric(label=f"Total Tugs Torque ({moment_help})", value=df_results.iloc[5]["Valore"], delta=f"{total_moment:.0f} t·m")

st.subheader("📋 Simulation Analytical Results")
st.dataframe(df_results, use_container_width=True, hide_index=True)
