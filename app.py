import streamlit as st
import numpy as np
import pandas as pd
import math
import base64

# ==========================================
# 0. INIZIALIZZAZIONE STATO (PER TASTO RESET)
# ==========================================
if "velocita_nave" not in st.session_state:
    st.session_state.velocita_nave = 5.0
if "ang_prua_s" not in st.session_state:
    st.session_state.ang_prua_s = 0
if "int_prua_s" not in st.session_state:
    st.session_state.int_prua_s = 0.0
if "ang_poppa_s" not in st.session_state:
    st.session_state.ang_poppa_s = 0
if "int_poppa_s" not in st.session_state:
    st.session_state.int_poppa_s = 0.0

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

tug_db = {
    "ASD 70 ton": {"bp": 70.0, "L": 32.0, "B": 11.0, "color": "#E67E22", "tow_point": "bow"},
    "RSD 80 ton": {"bp": 80.0, "L": 25.0, "B": 13.0, "color": "#E74C3C", "tow_point": "bow"},
    "VWT 55 ton": {"bp": 55.0, "L": 30.0, "B": 10.0, "color": "#3498DB", "tow_point": "stern"},
    "Custom":      {"bp": None, "L": 30.0, "B": 11.0, "color": "#95A5A6", "tow_point": "bow"}
}

# Dimensioni Nave Aggiornate
SHIP_L = 240.0
SHIP_B = 32.0
TOWLINE_L_M = 60.0 

def get_available_bp(bp_max, speed, position):
    """
    Calcola la potenza disponibile in base alla fisica del rimorchio e alla velocità.
    """
    if bp_max is None or bp_max == 0: return 0.0
    
    if position == "bow":
        # Direct Towing: La potenza crolla all'aumentare della velocità. Ad 8-10 nodi è quasi zero.
        if speed > 0:
            loss = (speed / 8.0) ** 2
            return max(0.0, bp_max * (1.0 - loss))
        else:
            loss = (abs(speed) / 10.0) ** 2
            return max(0.0, bp_max * (1.0 - loss))
    
    elif position == "stern":
        # Indirect Towing (Escort): Oltre i 6 nodi, le forze idrodinamiche moltiplicano la spinta.
        if speed >= 6.0:
            multiplier = 1.0 + (speed - 6.0) * 0.15 
            return bp_max * multiplier
        else:
            return float(bp_max)

# ==========================================
# 2. BARRA LATERALE (CONTROLLI GLOBALI)
# ==========================================
st.sidebar.title("🎮 Tactical Control")
st.sidebar.button("🔄 Reset to Default (5kt, 0t pull)", on_click=reset_simulation, use_container_width=True)
st.sidebar.markdown("---")

st.sidebar.subheader("Ship Status")
velocita_nave = st.sidebar.slider("Ship Speed (knots)", -5.0, 15.0, key="velocita_nave", step=0.5)

st.sidebar.markdown("---")
st.sidebar.subheader("Camera & Display")
focus_on = st.sidebar.radio(
    "VIEW MODE:",
    options=["Full Scene (Tight Fit)", "Bow Assembly", "Bow Tug (central)", "Stern Assembly", "Stern Tug (central)"]
)
# MODIFICA: Limite minimo dello zoom abbassato a 0.2 per permettere una visuale molto più ampia
zoom_level = st.sidebar.slider("🔎 Visual Scale", 0.2, 3.0, 1.0, 0.1)

# ==========================================
# 3. AREA PRINCIPALE (INTESTAZIONE E INPUT)
# ==========================================
st.title("Vector Towing Force Simulator")

st.markdown("""
    <div style='background-color: #ff9800; padding: 20px; text-align: center; border-radius: 10px; border: 2px dashed #e65100; margin-bottom: 20px;'>
        <h1 style='color: white; margin: 0; text-transform: uppercase; font-size: 2.5rem;'>🚧 Work in Progress 🚧</h1>
        <p style='color: white; font-size: 1.2rem; margin-top: 10px;'>This application is currently under heavy construction. Features, physics, and data are subject to change.</p>
    </div>
""", unsafe_allow_html=True)

st.markdown("#### For technical inquiries, feedback, or data contributions, please contact: [stefano.bandi22@gmail.com](mailto:stefano.bandi22@gmail.com)")
st.markdown("*© 2026 Stefano Bandi - All rights reserved. Commercial use is strictly prohibited.*")
st.markdown("---")

# Calcolo Pivot Point Dinamico
max_pp_offset = SHIP_L / 6.0 

if velocita_nave > 0:
    ratio = min(velocita_nave / 8.0, 1.0)
    pp_offset_y = -max_pp_offset * ratio
elif velocita_nave < 0:
    ratio = min(abs(velocita_nave) / 5.0, 1.0)
    pp_offset_y = max_pp_offset * ratio
else:
    pp_offset_y = 0.0

st.markdown(f"**Scenario:** Ship {SHIP_L}m x {SHIP_B}m at **{velocita_nave} knots**. Dynamic Pivot Point at **{abs(pp_offset_y):.1f}m** {'Forward' if pp_offset_y < 0 else 'Aft' if pp_offset_y > 0 else 'Center'} from midships.")

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
        data_prua["tow_point"] = st.radio("Tow Point - Bow", ["bow", "stern"], index=0, horizontal=True)
    
    bp_avail_prua = get_available_bp(data_prua["bp"], velocita_nave, "bow")
    st.caption(f"Direct Tow Limit (Speed Penalty): **{bp_avail_prua:.1f} t**")
        
    ang_prua = st.slider("Angle (°)", -90, 90, step=1, key="ang_prua_s", help="0° = ahead. Positive = Starboard")
    int_prua = st.slider("Intensity (t)", 0.0, float(bp_avail_prua), step=0.5, key="int_prua_s")

# Input Poppa
with col_poppa:
    st.subheader("Stern Tug (Poppa) ⬇️")
    s_poppa = st.selectbox("Type", list(tug_db.keys()), key="sel_poppa")
    
    data_poppa = tug_db[s_poppa].copy()
    if s_poppa == "Custom":
        data_poppa["bp"] = st.number_input("Max BP (t) - Stern", 10.0, 200.0, 60.0, step=1.0)
        data_poppa["L"] = st.number_input("Length (m) - Stern", 15.0, 50.0, 30.0)
        data_poppa["B"] = st.number_input("Beam (m) - Stern", 5.0, 20.0, 11.0)
        data_poppa["tow_point"] = st.radio("Tow Point - Stern", ["bow", "stern"], index=0, horizontal=True)
        
    bp_avail_poppa = get_available_bp(data_poppa["bp"], velocita_nave, "stern")
    
    if velocita_nave >= 6.0:
        st.caption(f"🔥 Indirect Tow Multiplier! Max Steering Force: **{bp_avail_poppa:.1f} t**")
    else:
        st.caption(f"Static Tow Limit: **{bp_avail_poppa:.1f} t**")
        
    ang_poppa = st.slider("Angle (°)", -90, 90, step=1, key="ang_poppa_s", help="0° = astern. Positive = Starboard")
    int_poppa = st.slider("Intensity (t)", 0.0, float(bp_avail_poppa), step=0.5, key="int_poppa_s")


# ==========================================
# 4. MOTORE GRAFICO SVG (Y-DOWN NATIVO)
# ==========================================

def generate_svg_scene():
    chock_prua_y = -SHIP_L / 2 + 5.0  
    chock_poppa_y = SHIP_L / 2 - 5.0  
    
    rad_prua = math.radians(ang_prua)
    tug_prua_x = TOWLINE_L_M * math.sin(rad_prua)
    tug_prua_y = chock_prua_y - TOWLINE_L_M * math.cos(rad_prua) 
    
    rad_poppa = math.radians(ang_poppa)
    tug_poppa_x = TOWLINE_L_M * math.sin(rad_poppa)
    tug_poppa_y = chock_poppa_y + TOWLINE_L_M * math.cos(rad_poppa)
    
    def get_ship_path():
        b2 = SHIP_B / 2
        l2 = SHIP_L / 2
        taper = 40.0
        d = f"M {b2} {l2-2} L {b2} {-l2+taper} C {b2} {-l2+taper/2}, {b2*0.3} {-l2}, 0 {-l2} "
        d += f"C {-b2*0.3} {-l2}, {-b2} {-l2+taper/2}, {-b2} {-l2+taper} L {-b2} {l2-2} "
        d += f"C {-b2} {l2}, {b2} {l2}, {b2} {l2-2} Z"
        return d

    def get_tug_path(data):
        l, b = data["L"], data["B"]
        l2, b2 = l/2, b/2
        d = f"M {b2} {l2-1} L {b2} {-l2+b*0.8} C {b2} {-l2}, {-b2} {-l2}, {-b2} {-l2+b*0.8} "
        d += f"L {-b2} {l2-1} C {-b2} {l2}, {b2} {l2}, {b2} {l2-1} Z"
        return d
    
    margin = 40.0
    
    min_x = min(-SHIP_B/2, tug_prua_x, tug_poppa_x)
    max_x = max(SHIP_B/2, tug_prua_x, tug_poppa_x)
    min_y = min(-SHIP_L/2, tug_prua_y, tug_poppa_y)
    max_y = max(SHIP_L/2, tug_prua_y, tug_poppa_y)
    
    if focus_on == "Full Scene (Tight Fit)":
        vw = (max_x - min_x) + margin*2
        vh = (max_y - min_y) + margin*2
        vx = min_x - margin
        vy = min_y - margin
    elif focus_on == "Bow Assembly":
        vw = abs(max_x - min_x) + margin*2
        vh = abs(chock_prua_y - tug_prua_y) + margin*3
        vx = min_x - margin
        vy = min(chock_prua_y, tug_prua_y) - margin*1.5
    elif focus_on == "Bow Tug (central)":
        vw, vh = 100.0, 100.0
        vx, vy = tug_prua_x - vw/2, tug_prua_y - vh/2
    elif focus_on == "Stern Assembly":
        vw = abs(max_x - min_x) + margin*2
        vh = abs(tug_poppa_y - chock_poppa_y) + margin*3
        vx = min_x - margin
        vy = min(chock_poppa_y, tug_poppa_y) - margin*1.5
    elif focus_on == "Stern Tug (central)":
        vw, vh = 100.0, 100.0
        vx, vy = tug_poppa_x - vw/2, tug_poppa_y - vh/2

    cx = vx + vw / 2
    cy = vy + vh / 2
    vw_scaled = vw / zoom_level
    vh_scaled = vh / zoom_level
    vx_scaled = cx - vw_scaled / 2
    vy_scaled = cy - vh_scaled / 2

    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" 
         viewBox="{vx_scaled} {vy_scaled} {vw_scaled} {vh_scaled}"
         style="background-color: #FFFFFF; border-radius: 8px; border: 1px solid #B0BEC5; max-height: 80vh;"
         id="towing-svg">
         
        <style>
            .tug-hull {{ stroke: white; stroke-width: 0.8; filter: drop-shadow(0px 3px 3px rgba(0,0,0,0.3)); transition: all 0.3s ease; }}
            .ship-hull {{ fill: #2C3E50; stroke: #34495E; stroke-width: 1.5; }}
            .towline {{ stroke-width: 1.5; stroke-dasharray: 4; stroke: #7F8C8D; fill: none; transition: stroke 0.3s; }}
            .text-label {{ font-family: 'Arial', sans-serif; font-weight: bold; fill: white; pointer-events: none; text-anchor: middle; }}
            .text-data {{ font-family: monospace; fill: #2C3E50; text-anchor: start; font-size: 8px; font-weight: bold; background-color: rgba(255,255,255,0.7); }}
            .pivot-cross {{ stroke: #27AE60; stroke-width: 1.5; }}
        </style>
    """
    
    svg += '<g stroke="#F0F0F0" stroke-width="0.3" stroke-dasharray="5 15">'
    for i in range(-500, 501, 20):
        svg += f'<line x1="{i}" y1="-500" x2="{i}" y2="500" />'
        svg += f'<line x1="-500" y1="{i}" x2="500" y2="{i}" />'
    svg += '</g>'

    svg += f'<path d="{get_ship_path()}" class="ship-hull" />'
    svg += f'<text x="0" y="5" class="text-label" font-size="16">SHIP</text>'
    
    svg += f'<circle cx="0" cy="{pp_offset_y}" r="3" fill="none" stroke="#27AE60" stroke-width="1.5"/>'
    svg += f'<line x1="-12" y1="{pp_offset_y}" x2="12" y2="{pp_offset_y}" class="pivot-cross"/>'
    svg += f'<line x1="0" y1="{pp_offset_y-12}" x2="0" y2="{pp_offset_y+12}" class="pivot-cross"/>'
    svg += f'<text x="15" y="{pp_offset_y+4}" fill="#27AE60" font-size="8" font-weight="bold">PIVOT POINT</text>'

    svg += f'<circle cx="0" cy="{chock_prua_y}" r="2" fill="#E74C3C" stroke="black" stroke-width="0.5"/>'
    svg += f'<circle cx="0" cy="{chock_poppa_y}" r="2" fill="#E74C3C" stroke="black" stroke-width="0.5"/>'

    def draw_tug_assembly(tx, ty, angle_deg, intensity, data, label_raw, is_bow):
        assembly = ""
        orig_y = chock_prua_y if is_bow else chock_poppa_y
        
        stress = intensity / data["bp"] if data["bp"] > 0 else 0
        r_line = int(127 + stress * 128)
        g_line = int(140 * (1-stress))
        b_line = int(141 * (1-stress))
        line_col = f"rgb({r_line},{g_line},{b_line})"
        
        assembly += f'<line x1="0" y1="{orig_y}" x2="{tx}" y2="{ty}" class="towline" stroke="{line_col}" />'
        
        if is_bow:
            rot = angle_deg
            offset_y = -data["L"] / 2.0 
        else:
            yaw_drift = velocita_nave * math.sin(math.radians(angle_deg)) * 2.5 
            if data["tow_point"] == "bow":
                rot = angle_deg + 180 + yaw_drift 
                offset_y = data["L"] / 2.0 
            else:
                rot = angle_deg + yaw_drift 
                offset_y = -data["L"] / 2.0 
            
        assembly += f'<g transform="translate({tx}, {ty}) rotate({rot})">'
        
        assembly += f'<g transform="translate(0, {offset_y})">'
        assembly += f'<path d="{get_tug_path(data)}" class="tug-hull" fill="{data["color"]}" />'
        
        label = label_raw.split()[0]
        assembly += f'<text x="0" y="3" class="text-label" transform="rotate({-rot})" font-size="7">{label}</text>'
        
        arrow_l = intensity / 2.0
        if arrow_l > 2:
            arrow_start = -data["L"]/2
            assembly += f'<line x1="0" y1="{arrow_start}" x2="0" y2="{arrow_start - arrow_l}" stroke="#F1C40F" stroke-width="1.5" marker-end="url(#arrowhead)"/>'
        
        assembly += '</g></g>' 
        
        assembly += f'<g transform="translate({tx+data["B"]/2+5}, {ty})">'
        mode = "DIRECT" if is_bow else "ESCORT" if velocita_nave >= 6 else "DIRECT"
        assembly += f'<text x="0" y="-12" class="text-data">{label} [{mode}]</text>'
        assembly += f'<text x="0" y="-2" class="text-data">Pull: {intensity:.1f}t</text>'
        assembly += f'<text x="0" y="8" class="text-data">Ang: {angle_deg}°</text>'
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

chock_prua_y = -SHIP_L / 2 + 5.0
chock_poppa_y = SHIP_L / 2 - 5.0

braccio_prua = abs(chock_prua_y - pp_offset_y)
braccio_poppa = abs(chock_poppa_y - pp_offset_y)

force_prua_x = int_prua * math.sin(math.radians(ang_prua))
moment_prua = force_prua_x * braccio_prua 

force_poppa_x = int_poppa * math.sin(math.radians(ang_poppa))
moment_poppa = -force_poppa_x * braccio_poppa 

total_moment = moment_prua + moment_poppa

res_prua = bp_avail_prua - int_prua
res_poppa = bp_avail_poppa - int_poppa

df_results = pd.DataFrame({
    "Parametro": [
        "Velocità Nave", 
        "Distanza Pivot Point (dal Centro)",
        "Tug Prua (Tiro / Avail BP)", 
        "Tug Prua (Riserva BP)",
        "Tug Poppa (Tiro / Avail BP)", 
        "Tug Poppa (Riserva BP)",
        "MOMENTO ROTAZIONE TOTALE"
    ],
    "Valore": [
        f"{velocita_nave} nodi",
        f"{abs(pp_offset_y):.1f} m",
        f"{int_prua:.1f} t / {bp_avail_prua:.0f} t (Direct)",
        f"{res_prua:.1f} t",
        f"{int_poppa:.1f} t / {bp_avail_poppa:.0f} t ({'Indirect' if velocita_nave >= 6 else 'Direct'})",
        f"{res_poppa:.1f} t",
        f"{total_moment:.0f} t·m"
    ],
    "Unità": ["kn", "m", "t", "t", "t", "t", "t·m"]
})

moment_help = "Rotating Starboard ↻" if total_moment > 50 else ("Rotating Port ↺" if total_moment < -50 else "Pushing Straight")

# ==========================================
# 6. GENERAZIONE E VISUALIZZAZIONE
# ==========================================

with st.spinner("Calculating physical interactions..."):
    svg_content = generate_svg_scene()
    
    b64_svg = base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')
    html_img = f'<div style="display:flex; justify-content:center;"><img src="data:image/svg+xml;base64,{b64_svg}" style="width: 100%; max-width: 1400px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"></div>'
    
    st.markdown(html_img, unsafe_allow_html=True)
    st.caption(f"Physics Engine View: {focus_on}")

st.markdown("---")
col_m1, col_m2 = st.columns(2)
col_m1.metric(label=f"Total Torque ({moment_help})", value=df_results.iloc[6]["Valore"], delta=f"{total_moment:.0f} t·m")
col_m2.metric(label="Dynamic Pivot Point", value=df_results.iloc[1]["Valore"], delta="From Midships", delta_color="off")

st.subheader("📋 Physics Simulation Results")
st.dataframe(df_results, use_container_width=True, hide_index=True)
