import streamlit as st

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Simulatore Forze Rimorchiatori", layout="wide")

# 2. DATABASE RIMORCHIATORI
# Aggiunta opzione personalizzata con Bollard Pull configurabile
tug_options = {
    "ASD 70 ton": 70.0,
    "RSD 80 ton": 80.0,
    "VWT 55 ton": 55.0,
    "Rimorchiatore Personalizzato": None
}

# 3. BARRA LATERALE (SIDEBAR)
st.sidebar.title("Pannello di Controllo")

# Selezione Velocità
velocita_nave = st.sidebar.slider(
    "Velocità della Nave (nodi)", 
    min_value=-5.0, 
    max_value=15.0, 
    value=6.0, 
    step=0.5
)

# Selezione Focus Visivo
st.sidebar.markdown("---")
focus_on = st.sidebar.radio(
    "FOCUS ON:",
    options=[
        "Scena intera", 
        "Prua nave", 
        "Rimorchiatore di prua", 
        "Poppa nave", 
        "Rimorchiatore di poppa"
    ]
)

# 4. CONTROLLI PRINCIPALI (PRUA E POPPA)
st.title("Simulatore di Rimorchio: Gestione Vettori")

col_controlli_prua, col_controlli_poppa = st.columns(2)

# Controlli Prua
with col_controlli_prua:
    st.subheader("Impostazioni Prua ⬆️")
    scelta_prua = st.selectbox("Seleziona Rimorchiatore di Prua", list(tug_options.keys()), key="sel_prua")
    
    bp_max_prua = tug_options[scelta_prua]
    if scelta_prua == "Rimorchiatore Personalizzato":
        bp_max_prua = st.number_input("Imposta Bollard Pull (t) - Prua", min_value=10.0, max_value=200.0, value=60.0, step=1.0)
    
    dir_prua = st.slider("Direzione Tiro Prua (°)", min_value=-90, max_value=90, value=0, step=1, key="dir_prua")
    int_prua = st.slider("Intensità Tiro Prua (t)", min_value=0.0, max_value=float(bp_max_prua), value=0.0, step=0.5, key="int_prua")

# Controlli Poppa
with col_controlli_poppa:
    st.subheader("Impostazioni Poppa ⬇️")
    scelta_poppa = st.selectbox("Seleziona Rimorchiatore di Poppa", list(tug_options.keys()), key="sel_poppa")
    
    bp_max_poppa = tug_options[scelta_poppa]
    if scelta_poppa == "Rimorchiatore Personalizzato":
        bp_max_poppa = st.number_input("Imposta Bollard Pull (t) - Poppa", min_value=10.0, max_value=200.0, value=60.0, step=1.0)
    
    dir_poppa = st.slider("Direzione Tiro Poppa (°)", min_value=-90, max_value=90, value=0, step=1, key="dir_poppa")
    int_poppa = st.slider("Intensità Tiro Poppa (t)", min_value=0.0, max_value=float(bp_max_poppa), value=0.0, step=0.5, key="int_poppa")

st.markdown("---")

# 5. GENERAZIONE GRAFICA HTML/CSS
st.subheader(f"Visualizzazione: {focus_on}")

# Funzioni di supporto per disegnare gli elementi tramite HTML/CSS
def draw_tug(scelta_nome, direzione, intensita, max_bp):
    # Estrae la prima parola (ASD, RSD, VWT o Custom) per l'etichetta
    etichetta = "CUSTOM" if scelta_nome == "Rimorchiatore Personalizzato" else scelta_nome.split()[0]
    percentuale = (intensita / max_bp * 100) if max_bp > 0 else 0
    
    return f"""
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin: 10px;">
        <div style="
            width: 60px; height: 100px; 
            background-color: #D35400; 
            border-radius: 30px 30px 10px 10px; 
            transform: rotate({direzione}deg);
            display: flex; align-items: center; justify-content: center;
            border: 3px solid #F1C40F;
            box-shadow: 0px 5px 15px rgba(0,0,0,0.5);
            transition: transform 0.3s ease-out;
            position: relative;
        ">
            <span style="
                color: white; font-weight: bold; font-size: 14px; 
                transform: rotate({-direzione}deg); /* Mantiene il testo dritto */
                text-align: center; display: block;
            ">{etichetta}</span>
        </div>
        <div style="margin-top: 15px; background: rgba(255,255,255,0.8); padding: 5px 10px; border-radius: 5px; color: black; font-weight: bold; font-family: monospace;">
            Tiro: {intensita:.1f}t<br>Angolo: {direzione}°<br>Carico: {percentuale:.0f}%
        </div>
    </div>
    """

def draw_ship_section(tipo="full"):
    if tipo == "prua":
        return """
        <div style="width: 120px; height: 150px; background-color: #2C3E50; border-radius: 60px 60px 0 0; border: 2px solid white; border-bottom: none; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">PRUA</div>
        """
    elif tipo == "poppa":
        return """
        <div style="width: 120px; height: 150px; background-color: #2C3E50; border-radius: 0 0 20px 20px; border: 2px solid white; border-top: none; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">POPPA</div>
        """
    else: # full
        return """
        <div style="width: 120px; height: 400px; background-color: #2C3E50; border-radius: 60px 60px 20px 20px; border: 2px solid white; display: flex; flex-direction: column; align-items: center; justify-content: space-between; padding: 20px 0; color: white; font-weight: bold; box-shadow: inset 0px 0px 10px rgba(0,0,0,0.5);">
            <span>PRUA</span>
            <span style="color: #7F8C8D; font-size: 12px;">NAVE</span>
            <span>POPPA</span>
        </div>
        """

def draw_tow_line():
    return """<div style="width: 4px; height: 60px; background-color: #BDC3C7; border: 1px dashed #7F8C8D;"></div>"""

# 6. MOTORE DI RENDERING DELLA SCENA
# Costruiamo l'HTML finale in base al FOCUS ON selezionato
html_scene_start = """
<div style="
    display: flex; flex-direction: column; align-items: center; justify-content: center; 
    background-color: #3498DB; padding: 40px; border-radius: 10px; 
    border: 2px solid #2980B9; min-height: 500px;
">
"""
html_scene_end = "</div>"

content = ""

if focus_on == "Scena intera":
    content += draw_tug(scelta_prua, dir_prua, int_prua, bp_max_prua)
    content += draw_tow_line()
    content += draw_ship_section("full")
    content += draw_tow_line()
    content += draw_tug(scelta_poppa, dir_poppa, int_poppa, bp_max_poppa)

elif focus_on == "Prua nave":
    content += draw_ship_section("prua")

elif focus_on == "Rimorchiatore di prua":
    content += draw_tug(scelta_prua, dir_prua, int_prua, bp_max_prua)
    content += draw_tow_line()

elif focus_on == "Poppa nave":
    content += draw_ship_section("poppa")

elif focus_on == "Rimorchiatore di poppa":
    content += draw_tow_line()
    content += draw_tug(scelta_poppa, dir_poppa, int_poppa, bp_max_poppa)

# Disegna la scena
st.markdown(html_scene_start + content + html_scene_end, unsafe_allow_html=True)
