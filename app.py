import streamlit as st
import google.generativeai as genai
import base64, re
from datetime import datetime

st.set_page_config(page_title="Conversor Darwin", page_icon="🛃", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
* { font-family: 'Inter', sans-serif; }
.step-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 100%);
    color: white; padding: 18px 24px; border-radius: 12px; margin-bottom: 20px;
}
.step-header h2 { color: white; margin: 0; font-size: 20px; }
.step-header p  { color: #b8d4f0; margin: 4px 0 0 0; font-size: 13px; }
.ok-box   { background:#f0fdf4; border-left:3px solid #22c55e; padding:10px 14px; border-radius:6px; font-size:13px; color:#15803d; margin:8px 0; }
.err-box  { background:#fef2f2; border-left:3px solid #ef4444; padding:10px 14px; border-radius:6px; font-size:13px; color:#991b1b; margin:8px 0; }
.warn-box { background:#fffbeb; border-left:3px solid #f59e0b; padding:10px 14px; border-radius:6px; font-size:13px; color:#92400e; margin:8px 0; }
.info-box { background:#f0f9ff; border-left:3px solid #0ea5e9; padding:10px 14px; border-radius:6px; font-size:13px; color:#0c4a6e; margin:8px 0; }
.metric-card { background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:16px; text-align:center; }
.metric-num   { font-size:28px; font-weight:700; color:#1e3a5f; }
.metric-label { font-size:12px; color:#64748b; margin-top:2px; }
</style>
""", unsafe_allow_html=True)

# ─── API KEY ──────────────────────────────────────────────────────────────────
api_key = st.secrets.get("GOOGLE_API_KEY", "")
if not api_key:
    api_key = st.sidebar.text_input("🔑 API Key de Google Gemini", type="password",
                                     help="Obtén tu clave gratis en aistudio.google.com")

with st.sidebar:
    st.markdown("### 🛃 Darwin Conversor")
    st.caption("Versión 2.0 — Gemini + Streamlit\nLayout: Vanguardia Tecnologías")
    st.divider()
    if api_key:
        st.markdown('<div class="ok-box">✅ API Key configurada</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="err-box">⚠️ Ingresa tu API Key de Gemini</div>', unsafe_allow_html=True)
    st.divider()
    st.caption("Archivo generado va en:\n`Darwin\\Facturas\\In`\nSeparador: pipe `|`\nCierre: registro `999`")

# ─── TÍTULO ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="step-header">
  <h2>🛃 Conversor de Facturas → Darwin</h2>
  <p>Convierte tus facturas PDF al formato Darwin — gratis con Google Gemini</p>
</div>
""", unsafe_allow_html=True)

# ─── SELECTOR DE MODO ─────────────────────────────────────────────────────────
st.markdown("### ¿Quién eres?")
col1, col2 = st.columns(2)
with col1:
    b1 = st.button("👤 Usuario / Capturista\nSolo subo facturas", use_container_width=True)
with col2:
    b2 = st.button("🏛️ Agente Aduanal\nControl completo", use_container_width=True)

if "modo" not in st.session_state:
    st.session_state.modo = None
if b1: st.session_state.modo = "usuario"
if b2: st.session_state.modo = "agente"

if not st.session_state.modo:
    st.markdown("""
    <div class="info-box">
    👆 Selecciona tu modo para comenzar.<br><br>
    <b>Modo Usuario:</b> Solo necesitas subir el PDF y tus códigos. Simple y rápido.<br>
    <b>Modo Agente Aduanal:</b> Acceso completo a todos los campos del Layout Darwin.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

modo = st.session_state.modo
st.markdown(f"**Modo activo:** {'👤 Usuario / Capturista' if modo=='usuario' else '🏛️ Agente Aduanal'}")
st.divider()

cfg = {}
TRANSPORTE_OPTS = {
    "🚛 Camión / Autotransporte": "1",
    "🚂 Tren / Ferroviario": "2",
    "🚢 Barco / Marítimo": "3",
    "✈️ Avión / Aéreo": "4",
    "📮 Correo / Paquetería": "7",
    "🔁 Otro": "99",
}
OPERACION_OPTS = {
    "📥 Importación — Mercancía que ENTRA a México": "1",
    "📤 Exportación — Mercancía que SALE de México": "2",
}
CLAVE_DOC_OPTS = {
    "A1 — Importación definitiva": "A1",
    "H2 — Importación temporal (IMMEX)": "H2",
    "IN — Internación temporal": "IN",
    "RT — Retorno de exportación temporal": "RT",
    "A4 — Reimportación": "A4",
}
TIPO_ARCHIVO_OPTS = {
    "P — Pedimento": "P",
    "E — Embarque": "E",
    "C — Consolidado": "C",
}

# ══════════════════════════════════════════════════════════════════════════════
# MODO USUARIO
# ══════════════════════════════════════════════════════════════════════════════
if modo == "usuario":

    st.markdown("### 📋 Paso 1 — Códigos de tu empresa y proveedor")
    col1, col2 = st.columns(2)
    with col1:
        cod_imp = st.text_input("🏭 Código de tu empresa en Darwin *",
                                 max_chars=10, placeholder="Ej: FEMCO")
        cfg["cod_imp"] = cod_imp.upper() if cod_imp else ""
        if cod_imp:
            st.markdown(f'<div class="ok-box">✅ {cod_imp.upper()} ({len(cod_imp)}/10)</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="warn-box">Tu agente aduanal te da este código</div>', unsafe_allow_html=True)
    with col2:
        cod_prov = st.text_input("🏢 Código del proveedor en Darwin *",
                                  max_chars=10, placeholder="Ej: RELIAN")
        cfg["cod_prov"] = cod_prov.upper() if cod_prov else ""
        if cod_prov:
            st.markdown(f'<div class="ok-box">✅ {cod_prov.upper()} ({len(cod_prov)}/10)</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="warn-box">Tu agente aduanal te da este código</div>', unsafe_allow_html=True)

    st.divider()
    st.markdown("### 🚢 Paso 2 — ¿Cómo llega la mercancía?")
    trans_sel = st.radio("Medio de transporte", list(TRANSPORTE_OPTS.keys()),
                          index=2, label_visibility="collapsed")
    cfg["transporte"] = TRANSPORTE_OPTS[trans_sel]

    st.divider()
    st.markdown("### 📦 Paso 3 — Número de guía *(opcional)*")
    tiene_guia = st.toggle("Tengo número de guía o manifiesto")
    if tiene_guia:
        col1, col2 = st.columns([3,1])
        with col1:
            cfg["guia_numero"] = st.text_input("Número de guía", max_chars=20)
        with col2:
            tg = st.selectbox("Tipo", ["🗂 Maestra","📄 Doméstica"])
            cfg["guia_tipo"] = "M" if "Maestra" in tg else "D"
    else:
        cfg["guia_numero"] = ""
        cfg["guia_tipo"] = "M"

    cfg["tipo_op"] = "1"
    cfg["clave_doc"] = "A1"
    cfg["zona"] = "1"
    cfg["tipo_archivo"] = "P"
    cfg["pais_moneda"] = "USA"

    st.divider()
    st.markdown("### 📄 Paso 4 — Sube tu(s) factura(s)")
    uploaded = st.file_uploader("Arrastra los PDFs aquí", type=["pdf"], accept_multiple_files=True)
    if uploaded:
        st.markdown(f'<div class="ok-box">✅ {len(uploaded)} archivo(s) listo(s)</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MODO AGENTE
# ══════════════════════════════════════════════════════════════════════════════
elif modo == "agente":

    st.markdown("### 🏛️ Configuración completa")

    with st.expander("① Códigos de Importador y Proveedor (OBL)", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            cod_imp = st.text_input("Código del Importador * (máx 10)", max_chars=10, placeholder="FEMCO")
            cfg["cod_imp"] = cod_imp.upper() if cod_imp else ""
            if cfg["cod_imp"]: st.caption(f"✅ {cfg['cod_imp']} — {len(cfg['cod_imp'])}/10 chars")
            else: st.caption("⚠️ OBL — requerido para registro 501")
        with col2:
            cod_prov = st.text_input("Código del Proveedor * (máx 10)", max_chars=10, placeholder="RELIAN")
            cfg["cod_prov"] = cod_prov.upper() if cod_prov else ""
            if cfg["cod_prov"]: st.caption(f"✅ {cfg['cod_prov']} — {len(cfg['cod_prov'])}/10 chars")
            else: st.caption("⚠️ OBL — requerido para registro 505")

    with st.expander("② Registro 501 — Encabezado", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            t = st.selectbox("Tipo de operación *", list(OPERACION_OPTS.keys()))
            cfg["tipo_op"] = OPERACION_OPTS[t]
        with col2:
            cd = st.selectbox("Clave de Documento *", list(CLAVE_DOC_OPTS.keys()))
            cfg["clave_doc"] = CLAVE_DOC_OPTS[cd]
        with col3:
            cfg["zona"] = st.text_input("Destino/Zona *", value="1", max_chars=2)
        with col4:
            ta = st.selectbox("Tipo de Archivo", list(TIPO_ARCHIVO_OPTS.keys()))
            cfg["tipo_archivo"] = TIPO_ARCHIVO_OPTS[ta]

        col1, col2 = st.columns(2)
        with col1:
            tr = st.selectbox("Transporte entrada *", list(TRANSPORTE_OPTS.keys()), index=2)
            cfg["transporte"] = TRANSPORTE_OPTS[tr]
        with col2:
            cfg["pais_moneda"] = st.text_input("País Moneda", value="USA", max_chars=3)

        col1, col2, col3 = st.columns(3)
        with col1: cfg["fletes"] = st.text_input("Fletes (OPC)", max_chars=12)
        with col2: cfg["seguros"] = st.text_input("Seguros (OPC)", max_chars=12)
        with col3: cfg["embalajes"] = st.text_input("Embalajes (OPC)", max_chars=12)

    with st.expander("③ Guía / Manifiesto (OPC)"):
        tiene_guia = st.toggle("Incluir registro 503 — Guía")
        if tiene_guia:
            col1, col2 = st.columns([3,1])
            with col1: cfg["guia_numero"] = st.text_input("Número de Guía *", max_chars=20)
            with col2:
                tg = st.selectbox("Tipo *", ["M — Maestra","D — Doméstica"])
                cfg["guia_tipo"] = tg[0]
        else:
            cfg["guia_numero"] = ""
            cfg["guia_tipo"] = "M"

    with st.expander("④ Observaciones al pedimento (OPC)"):
        obs_text = st.text_area("Una observación por línea (máx 120 chars c/u)", height=80)
        cfg["observaciones"] = [l[:120] for l in obs_text.split("\n") if l.strip()]

    st.markdown("### 📄 Sube tu(s) factura(s)")
    uploaded = st.file_uploader("Arrastra los PDFs aquí", type=["pdf"],
                                 accept_multiple_files=True, key="ag_pdf")
    if uploaded:
        st.markdown(f'<div class="ok-box">✅ {len(uploaded)} archivo(s) listo(s)</div>', unsafe_allow_html=True)

    if "fletes" not in cfg: cfg["fletes"] = ""
    if "seguros" not in cfg: cfg["seguros"] = ""
    if "embalajes" not in cfg: cfg["embalajes"] = ""
    if "observaciones" not in cfg: cfg["observaciones"] = []

# ══════════════════════════════════════════════════════════════════════════════
# GENERAR
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.markdown("### 🚀 Generar archivo Darwin")

faltantes = []
if not api_key:              faltantes.append("API Key de Google Gemini")
if not cfg.get("cod_imp"):   faltantes.append("Código del Importador")
if not cfg.get("cod_prov"):  faltantes.append("Código del Proveedor")
if not uploaded:             faltantes.append("Archivo PDF")

if faltantes:
    for f in faltantes:
        st.markdown(f'<div class="warn-box">⚠️ Falta: <b>{f}</b></div>', unsafe_allow_html=True)

if st.button("✅ Generar archivo .txt para Darwin",
             use_container_width=True, type="primary",
             disabled=bool(faltantes)):

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
    except Exception as e:
        st.error(f"Error configurando Gemini: {e}")
        st.stop()

    guia_txt = ""
    if cfg.get("guia_numero"):
        guia_txt = f"503|{cfg['guia_numero'][:20]}|{cfg.get('guia_tipo','M')}"

    obs_txt = ""
    for obs in cfg.get("observaciones", []):
        obs_txt += f"511|{obs}\n"

    prompt = f"""Eres un experto en aduanas mexicanas. Convierte las facturas PDF al formato Darwin de Vanguardia Tecnologías.

DATOS DEL PEDIMENTO:
- Código importador: {cfg['cod_imp']} (máx 10 chars)
- Código proveedor: {cfg['cod_prov']} (máx 10 chars)
- Tipo operación: {cfg.get('tipo_op','1')}
- Clave documento: {cfg.get('clave_doc','A1')}
- Transporte: {cfg.get('transporte','3')}
- Zona destino: {cfg.get('zona','1')}
- País moneda: {cfg.get('pais_moneda','USA')}
- Tipo archivo: {cfg.get('tipo_archivo','P')}
- Fletes: {cfg.get('fletes','')}
- Seguros: {cfg.get('seguros','')}
- Embalajes: {cfg.get('embalajes','')}

REGLAS DEL FORMATO:
- Separador de campos: pipe "|"
- Campos vacíos: dos pipes juntos "||"
- Fecha: aaaammdd sin guiones ni espacios
- Países en 3 letras: CHN=China, TWN=Taiwan, THA=Tailandia, USA=Estados Unidos, MEX=Mexico, VNM=Vietnam, IDN=Indonesia
- Unidades: 01=PZA/EA, 03=PAR/PR, 04=ROL, 06=PAQ/PK

ORDEN OBLIGATORIO:
501 → (503 si hay guía) → (511 si hay observaciones) → 505 → 551 por partida → 999

REGISTRO 501 (uno solo):
501|{cfg.get('tipo_op','1')}|{cfg.get('clave_doc','A1')}||{cfg['cod_imp']}|{cfg.get('fletes','')}|{cfg.get('seguros','')}|{cfg.get('embalajes','')}|||(peso bruto total)|(total bultos)|{cfg.get('transporte','3')}|||{cfg.get('zona','1')}||||{cfg.get('tipo_archivo','P')}|{cfg.get('pais_moneda','USA')}|||||

{('REGISTRO 503 (guía):' + chr(10) + guia_txt) if guia_txt else ''}
{('REGISTROS 511 (observaciones):' + chr(10) + obs_txt) if obs_txt else ''}

REGISTRO 505 (uno por cada factura):
505|(num factura max 40)|(fecha aaaammdd)|(termino max 3)|(moneda max 3)|(valor moneda ext max 14)|(valor dolares max 14)|{cfg['cod_prov']}||{cfg.get('pais_moneda','USA')}|||||||||||(peso bruto 14,2)|(peso neto 14,2)|(bultos)|||USA|MEX|MEX|

REGISTRO 551 (uno por cada partida):
551||(descripcion max 250)|(no parte max 20)|(valor mercancia max 14)|(cantidad max 15)|(unidad 2 chars)|(cantidad tarifa max 19)||0|1||||(pais origen 3 letras)|(pais comprador 3 letras)|||||||||||||||||||||||||||||||(precio unitario 12,8)|(valor aduana max 12)|(valor dolares 14,2)|1|(peso neto unit 12,8)|(peso bruto unit 12,8)|(orden compra max 20)|(num factura max 15)|||0|

REGISTRO 999 (siempre al final):
999

INSTRUCCIONES:
1. Extrae TODAS las partidas de TODAS las facturas sin omitir ninguna
2. Si hay varias facturas genera un 505 por cada una seguido de sus 551
3. Devuelve ÚNICAMENTE las líneas del archivo Darwin
4. Sin explicaciones, sin markdown, sin texto extra, sin bloques de código
5. Cada registro en una línea separada
6. El archivo debe terminar con 999"""

    all_lines = []
    progress = st.progress(0, text="Procesando PDFs con Gemini...")

    for i, pdf_file in enumerate(uploaded):
        progress.progress(int(i/len(uploaded)*90),
                         text=f"Leyendo {pdf_file.name}... ({i+1}/{len(uploaded)})")
        try:
            pdf_bytes = pdf_file.read()
            b64 = base64.standard_b64encode(pdf_bytes).decode()

            response = model.generate_content([
                {"mime_type": "application/pdf", "data": b64},
                prompt
            ])

            txt = response.text.strip()
            txt = re.sub(r"```.*?```", "", txt, flags=re.DOTALL).strip()

            lines = [l for l in txt.split("\n")
                    if l.strip() and any(l.startswith(r) for r in
                    ["501","502","503","504","505","506","511","551","552",
                     "553","554","558","559","999","CCC","PPP","FFF","PAM"])]
            all_lines.extend(lines)

        except Exception as e:
            st.error(f"Error procesando {pdf_file.name}: {e}")

    progress.progress(100, text="Generando archivo...")

    if all_lines:
        # Asegurar que termina con 999
        all_lines = [l for l in all_lines if l.strip() != "999"]
        all_lines.append("999")
        txt_final = "\n".join(all_lines)

        st.divider()
        st.markdown("### ✅ ¡Tu archivo está listo!")

        facturas = sum(1 for l in all_lines if l.startswith("505"))
        partidas = sum(1 for l in all_lines if l.startswith("551"))

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="metric-card"><div class="metric-num">{facturas}</div><div class="metric-label">Facturas</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-card"><div class="metric-num">{partidas}</div><div class="metric-label">Partidas</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="metric-card"><div class="metric-num">{len(all_lines)}</div><div class="metric-label">Líneas</div></div>', unsafe_allow_html=True)

        st.markdown("")

        with st.expander("👁 Ver contenido del archivo"):
            st.code(txt_final[:3000] + ("\n..." if len(txt_final) > 3000 else ""), language="text")

        nombre = f"darwin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        st.download_button(
            "⬇️ Descargar archivo .txt para Darwin",
            data=txt_final.encode("utf-8"),
            file_name=nombre,
            mime="text/plain",
            use_container_width=True,
            type="primary"
        )
        st.success(f"✅ Deposita `{nombre}` en `Darwin\\Facturas\\In`")
    else:
        st.error("No se pudo extraer contenido del PDF. Verifica que el archivo sea legible.")
