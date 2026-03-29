import streamlit as st
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import math

# ==========================================
# 1. CONFIGURAZIONE E SETUP
# ==========================================
st.set_page_config(page_title="Tactical Towing Simulator", layout="wide")

# Database Rimorchiatori (Bollard Pull in tonnellate)
tug_db = {
    "ASD 70 ton": 70.0,
    "RSD 80 ton": 80.0,
    "VWT 55 ton": 55.0,
    "Custom": None
}

# ==========================================
# 2. BARRA LATERALE (CONTROLLI GLOBALI)
# ==========================================
st.sidebar.title("🎮 Control Panel")

st.sidebar.subheader("Ship Settings")
velocita_nave = st.sidebar.slider("Ship Speed (knots)", -5.0, 15.0, 6.0, 0.5)

st.sidebar.markdown("---")
st.sidebar.subheader("Camera Settings")
focus_on = st.sidebar.radio(
    "FOCUS ON:",
    options=[
        "Full Scene", 
        "Bow Ship chock",        # Punto di aggancio prua nave
        "Bow Tug (central)",     # Rimorchiatore prua al centro
        "Stern Ship chock",      # Punto di aggancio poppa nave
        "Stern Tug (central)"    # Rimorchiatore poppa al centro
    ]
)

# Controllo ZOOM dinamico
zoom_level = st.sidebar.slider("🔎 Zoom Level", 0.5, 4.0, 1.0, 0.1)

# ==========================================
# 3. AREA PRINCIPALE (CONTROLLI TUG)
# ==========================================
st.title("🚜 Tactical Towing Force Simulator")
st.markdown(f"**Current Status:** Ship moving at **{velocita_nave} knots**.")

col_prua, col_poppa = st.columns(2)

# Input Prua
with col_prua:
    st.subheader("Prua (Bow) Tug ⬆️")
    s_prua = st.selectbox("Type", list(tug_db.keys()), key="sel_prua")
    bp_prua_max = tug_db[s_prua] if s_prua != "Custom" else st.number_input("Max BP (t)", 10, 200, 60, key="bp_p_c")
    
    # Angolo: 0 = in asse a prua via, +90 = dritto a dritta
    ang_prua = st.slider("Towed Angle (°)", -90, 90, 0, 1, key="ang_prua_s", help="0° = straight ahead. Positive = Starboard")
    int_prua = st.slider("Pull Intensity (t)", 0.0, float(bp_prua_max), 0.0, 0.5, key="int_prua_s")

# Input Poppa
with col_poppa:
    st.subheader("Poppa (Stern) Tug ⬇️")
    s_poppa = st.selectbox("Type", list(tug_db.keys()), key="sel_poppa")
    bp_poppa_max = tug_db[s_poppa] if s_poppa != "Custom" else st.number_input("Max BP (t)", 10, 200, 60, key="bp_po_c")
    
    # Angolo: 0 = in asse a poppa via, +90 = dritto a dritta (rispetto al frame del tug)
    ang_poppa = st.slider("Towed Angle (°)", -90, 90, 0, 1, key="ang_poppa_s", help="0° = straight astern. Positive = Starboard")
    int_poppa = st.slider("Pull Intensity (t)", 0.0, float(bp_poppa_max), 0.0, 0.5, key="int_poppa_s")


# ==========================================
# 4. MOTORE GRAFICO 2D (PILLOW)
# ==========================================

def draw_tactical_scene():
    # --- Configurazione Canvas ---
    # Usiamo un canvas grande (mondo virtuale) per permettere lo zoom
    W, H = 2000, 2000 
    cx, cy = W // 2, H // 2 # Centro del mondo
    img = Image.new("RGB", (W, H), "#34495E") # Colore acqua scura
    draw = ImageDraw.Draw(img)
    
    # Tentativo di caricare un font di sistema, altrimenti default
    try:
        font_main = ImageFont.truetype("Arial.ttf", 30)
        font_sub = ImageFont.truetype("Arial.ttf", 20)
    except:
        font_main = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # --- Dimensioni Reali Scalate (Pixel) ---
    # Assumiamo 1px = 0.2 metri circa per stilizzazione
    ship_w, ship_h = 160, 600
    tug_w, tug_h = 50, 100
    towline_length = 250 # Lunghezza cavo fissa per ora

    # Coordinate Punti di Aggancio (Chocks) sulla nave
    chock_prua_y = cy - (ship_h // 2) + 20
    chock_poppa_y = cy + (ship_h // 2) - 20
    
    # == DISEGNO NAVE (Scafo Stilizzato) ==
    ship_color = "#2C3E50" # Grigio scuro nave
    ship_coords = [
        (cx, cy - ship_h//2), # Prua (punta)
        (cx + ship_w//2, cy - ship_h//2 + 80), # Spalla dritta
        (cx + ship_w//2, cy + ship_h//2 - 30), # Poppa dritta
        (cx - ship_w//2, cy + ship_h//2 - 30), # Poppa sinistra
        (cx - ship_w//2, cy - ship_h//2 + 80), # Spalla sinistra
    ]
    draw.polygon(ship_coords, fill=ship_color, outline="white", width=3)
    draw.text((cx - 40, cy - 20), "N A V E", fill="white", font=font_main)
    
    # Segna i chocks
    draw.ellipse((cx-5, chock_prua_y-5, cx+5, chock_prua_y+5), fill="red")
    draw.ellipse((cx-5, chock_poppa_y-5, cx+5, chock_poppa_y+5), fill="red")

    # == LOGICA E DISEGNO RIMORCHIATORI (Vettoriale) ==
    
    def draw_tug_assembly(chock_x, chock_y, angle_deg, intensity, name, is_bow=True):
        # 1. Calcolo trigonometria (l'angolo 0 è verticale: su per prua, giù per poppa)
        # In Pillow Y cresce verso il basso.
        
        base_angle_rad = math.radians(angle_deg)
        
        if is_bow:
            # Prua: angolo 0 = Alto (Y diminuisce)
            target_angle_rad = base_angle_rad - (math.pi / 2)
            # Centro Tug
            tug_cx = chock_x + towline_length * math.cos(target_angle_rad)
            tug_cy = chock_y + towline_length * math.sin(target_angle_rad)
            # Rotazione scafo: Pillow ruota in senso orario. 
            # Dobbiamo allineare lo scafo (verticale) all'angolo del cavo.
            hull_rotation = angle_deg
        else:
            # Poppa: angolo 0 = Basso (Y aumenta)
            target_angle_rad = base_angle_rad + (math.pi / 2)
            tug_cx = chock_x + towline_length * math.cos(target_angle_rad)
            tug_cy = chock_y + towline_length * math.sin(target_angle_rad)
            hull_rotation = angle_deg + 180 # Girato di 180 rispetto alla prua
            
        # 2. Disegno Cavo (Sempre in asse)
        # Colore cavo dinamico in base all'intensità (Grigio -> Rosso)
        color_val = int((intensity / bp_prua_max if is_bow else intensity / bp_poppa_max) * 255) if (bp_prua_max if is_bow else bp_poppa_max) > 0 else 0
        line_color = (200, 200 - color_val, 200 - color_val) # Tende al rosso
        
        draw.line([(chock_x, chock_y), (tug_cx, tug_cy)], fill=line_color, width=4)
        
        # 3. Disegno Scafo Rimorchiatore (Ruotato)
        # Creiamo un'immagine temporanea per il tug per ruotarla
        tug_img = Image.new("RGBA", (tug_w + 20, tug_h + 20), (0,0,0,0))
        tug_draw = ImageDraw.Draw(tug_img)
        
        # Forma tug stilizzata (punta avanti)
        # Disegnamo verticale centrato nella sua img temporanea
        tx, ty = (tug_w+20)//2, (tug_h+20)//2
        tug_shape = [
            (tx, ty - tug_h//2), # Punta
            (tx + tug_w//2, ty - tug_h//2 + 20),
            (tx + tug_w//2, ty + tug_h//2),
            (tx - tug_w//2, ty + tug_h//2),
            (tx - tug_w//2, ty - tug_h//2 + 20),
        ]
        tug_draw.polygon(tug_shape, fill="#D35400", outline="#F1C40F", width=2)
        
        # Scritta tipo (ASD/RSD) - la scriviamo dritta prima di ruotare
        # Per leggerla bene la scriviamo orizzontale
        text_label = name.split()[0] # Prende solo ASD, RSD, VWT
        w_t = tug_draw.textlength(text_label, font=font_sub)
        tug_draw.text((tx - w_t//2, ty), text_label, fill="white", font=font_sub)
        
        # Rotazione
        # hull_rotation deve combaciare con l'angolo del cavo
        rotated_tug = tug_img.rotate(-hull_rotation, resample=Image.BICUBIC, expand=0) # Meno perché Pillow è orario
        
        # Incolliamo sul canvas principale
        img.paste(rotated_tug, (int(tug_cx - rotated_tug.width//2), int(tug_cy - rotated_tug.height//2)), rotated_tug)
        
        # 4. Info Box (Testo dritto vicino al tug, non ruotato)
        info_text = f"{text_label}\nP:{intensity:.1f}t\nA:{angle_deg}°"
        draw.text((tug_cx + 40, tug_cy - 30), info_text, fill="white", font=font_sub)
        
        return tug_cx, tug_cy # Ritorniamo la posizione per il focus camera

    # Esegui disegno assemblaggi
    t_prua_x, t_prua_y = draw_tug_assembly(cx, chock_prua_y, ang_prua, int_prua, s_prua, is_bow=True)
    t_poppa_x, t_poppa_y = draw_tug_assembly(cx, chock_poppa_y, ang_poppa, int_poppa, s_poppa, is_bow=False)
    
    # ==========================================
    # 5. GESTIONE CAMERA (FOCUS + ZOOM)
    # ==========================================
    
    # Determiniamo il punto centrale dell'inquadratura (LookAt)
    look_at_x, look_at_y = cx, cy # Default: centro nave
    
    if focus_on == "Bow Ship chock":
        look_at_x, look_at_y = cx, chock_prua_y
    elif focus_on == "Bow Tug (central)":
        look_at_x, look_at_y = t_prua_x, t_prua_y
    elif focus_on == "Stern Ship chock":
        look_at_x, look_at_y = cx, chock_poppa_y
    elif focus_on == "Stern Tug (central)":
        look_at_x, look_at_y = t_poppa_x, t_poppa_y
    # "Full Scene" resta cx, cy
    
    # Calcolo finestra di ritaglio base (output size desiderata, es 1000x800)
    out_w, out_h = 1000, 700
    
    # Applichiamo lo zoom: più alto lo zoom, più piccola l'area del mondo che ritagliamo
    crop_w = out_w / zoom_level
    crop_h = out_h / zoom_level
    
    left = look_at_x - (crop_w / 2)
    top = look_at_y - (crop_h / 2)
    right = look_at_x + (crop_w / 2)
    bottom = look_at_y + (crop_h / 2)
    
    # Ritaglio (Crop)
    cropped_img = img.crop((left, top, right, bottom))
    
    # Ridimensioniamo alla dimensione di output finale per Streamlit (Upscale/Downscale pulito)
    final_img = cropped_img.resize((out_w, out_h), Image.Resampling.LANCZOS)
    
    return final_img

# ==========================================
# 6. GENERAZIONE E VISUALIZZAZIONE
# ==========================================

with st.spinner("Generating tactical view..."):
    tactic_image = draw_tactical_scene()
    
    # Mostra immagine centrata
    st.image(tactic_image, use_container_width=True, caption=f"Tactical View: {focus_on} (Zoom: {zoom_level:.1f}x)")

# Visualizzazione Dati Numerici sotto
st.markdown("---")
col_d1, col_d2, col_d3 = st.columns(3)
col_d1.metric("Ship Speed", f"{velocita_nave} kn")
col_d2.metric("Bow Pull", f"{int_prua:.1f} t", f"{ang_prua}°")
col_d3.metric("Stern Pull", f"{int_poppa:.1f} t", f"{ang_poppa}°")
