import streamlit as st
import anthropic
import base64, re, json
from datetime import datetime

st.set_page_config(page_title="Conversor Darwin", page_icon="🛃", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
* { font-family: 'Inter', sans-serif; }

.step-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 100%);
    color: white; padding: 18px 24px; border-radius: 12px;
    margin-bottom: 20px;
}
.step-header h2 { color: white; margin: 0; font-size: 20px; }
.step-header p  { color: #b8d4f0; margin: 4px 0 0 0; font-size: 13px; }

.mode-card {
    border: 2px solid #e2e8f0; border-radius: 12px;
    padding: 20px; text-align: center; cursor: pointer;
    transition: all 0.2s;
}
.mode-card:hover { border-color: #2d6a9f; background: #f0f7ff; }
.mode-card.active { border-color: #2d6a9f; background: #ebf4ff; }
.mode-icon { font-size: 40px; margin-bottom: 8px; }
.mode-title { font-weight: 600; font-size: 16px; color: #1e3a5f; }
.mode-desc  { font-size: 12px; color: #64748b; margin-top: 4px; }

.option-btn {
    width: 100%; padding: 14px; border: 2px solid #e2e8f0;
    border-radius: 10px; background: white; cursor: pointer;
    font-size: 15px; text-align: left; margin-bottom: 8px;
    display: flex; align-items: center; gap: 12px;
}
.option-btn:hover  { border-color: #2d6a9f; background: #f0f7ff; }
.option-btn.active { border-color: #2d6a9f; background: #ebf4ff; font-weight: 600; }

.info-tip {
    background: #f0f9ff; border-left: 3px solid #0ea5e9;
    padding: 10px 14px; border-radius: 6px; font-size: 13px;
    color: #0c4a6e; margin: 8px 0;
}
.success-msg {
    background: #f0fdf4; border-left: 3px solid #22c55e;
    padding: 10px 14px; border-radius: 6px; font-size: 13px;
    color: #15803d; margin: 8px 0;
}
.error-msg {
    background: #fef2f2; border-left: 3px solid #ef4444;
    padding: 10px 14px; border-radius: 6px; font-size: 13px;
    color: #991b1b; margin: 8px 0;
}
.warn-msg {
    background: #fffbeb; border-left: 3px solid #f59e0b;
    padding: 10px 14px; border-radius: 6px; font-size: 13px;
    color: #92400e; margin: 4px 0;
}
.field-label {
    font-size: 13px; font-weight: 500; color: #374151;
    margin-bottom: 4px; display: flex; align-items: center; gap: 6px;
}
.obl-dot { color: #ef4444; font-size: 16px; line-height: 1; }
.opc-tag { background: #f1f5f9; color: #64748b; font-size: 10px;
           padding: 1px 6px; border-radius: 4px; }
.adv-field {
    background: #fafafa; border: 1px solid #e2e8f0;
    border-radius: 8px; padding: 14px; margin-bottom: 10px;
}
.adv-field-label {
    font-size: 11px; color: #6b7280; font-weight: 500;
    text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;
}
.metric-card {
    background: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 16px; text-align: center;
}
.metric-num   { font-size: 28px; font-weight: 700; color: #1e3a5f; }
.metric-label { font-size: 12px; color: #64748b; margin-top: 2px; }
.progress-bar {
    height: 6px; background: #e2e8f0; border-radius: 3px;
    overflow: hidden; margin: 12px 0;
}
.progress-fill {
    height: 100%; background: linear-gradient(90deg,#2d6a9f,#0ea5e9);
    border-radius: 3px; transition: width 0.4s;
}
.section-divider {
    border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;
}
</style>
""", unsafe_allow_html=True)

# ─── DATOS ────────────────────────────────────────────────────────────────────

TRANSPORTE_OPTS = {
    "🚛 Camión / Autotransporte": "1",
    "🚂 Tren / Ferroviario": "2",
    "🚢 Barco / Marítimo": "3",
    "✈️ Avión / Aéreo": "4",
    "🔧 Ductos / Tuberías": "5",
    "📦 Cable eléctrico": "6",
    "📮 Correo / Paquetería": "7",
    "🚶 Peatonal": "8",
    "🔁 Otro": "99",
}

OPERACION_OPTS = {
    "📥 Importación — Mercancía que ENTRA a México": "1",
    "📤 Exportación — Mercancía que SALE de México": "2",
}

TIPO_ARCHIVO_OPTS = {
    "📄 Pedimento": "P",
    "🚢 Embarque": "E",
    "📦 Consolidado": "C",
}

CLAVE_DOC_OPTS = {
    "A1 — Importación definitiva": "A1",
    "H2 — Importación temporal (IMMEX)": "H2",
    "IN — Internación temporal": "IN",
    "RT — Retorno de exportación temporal": "RT",
    "A4 — Reimportación": "A4",
    "Otra (escribir manualmente)": "OTRA",
}

UNIDAD_MAP = {
    "PZA":"01","PIEZA":"01","EA":"01","PC":"01","PCS":"01","UN":"01","UND":"01","UNIDAD":"01",
    "PAR":"03","PR":"03","PAR":"03",
    "ROL":"04","ROLLO":"04",
    "PAQ":"06","PAQUETE":"06","PK":"06",
    "KG":"07","KGS":"07",
    "LT":"08","LTS":"08",
    "MT":"10","MTS":"10",
    "CJA":"11","CAJA":"11",
    "JGO":"13","JUEGO":"13",
}

ORIGEN_MAP = {
    "CHINA":"CHN","CHN":"CHN","TAIWUAN":"TWN",
    "TAIWAN":"TWN","TWN":"TWN",
    "TAILANDIA":"THA","THAILAND":"THA","THA":"THA",
    "USA":"USA","ESTADOS UNIDOS":"USA","EUA":"USA",
    "MEXICO":"MEX","MÉXICO":"MEX","MEX":"MEX",
    "VIETNAM":"VNM","VNM":"VNM",
    "INDONESIA":"IDN","IDN":"IDN",
    "INDIA":"IND","IND":"IND",
    "COREA":"KOR","KOR":"KOR",
    "JAPON":"JPN","JAPÓN":"JPN","JPN":"JPN",
    "CANADA":"CAN","CANADÁ":"CAN","CAN":"CAN",
    "BRASIL":"BRA","BRA":"BRA",
    "ALEMANIA":"DEU","DEU":"DEU",
}

def trunc(val, maxlen):
    s = str(val) if val is not None else ""
    return s[:maxlen] if maxlen > 0 else s

def origen_code(o):
    return ORIGEN_MAP.get(str(o).upper().strip(), str(o)[:3].upper() if o else "")

def pdf_b64(fb):
    return base64.standard_b64encode(fb).decode("utf-8")

# ─── EXTRACCIÓN ───────────────────────────────────────────────────────────────

def extract_pdf(client, pdf_bytes, ctx):
    b64 = pdf_b64(pdf_bytes)
    prompt = f"""Extrae datos de esta factura para el sistema aduanal Darwin de México.
Código importador: {ctx.get('cod_imp','')}
Código proveedor: {ctx.get('cod_prov','')}

Devuelve SOLO JSON válido sin markdown:
{{
  "enc_peso_bruto": "0.000",
  "enc_bultos": "0",
  "imp_nombre": "",
  "imp_calle": "",
  "imp_ciudad": "",
  "imp_cp": "",
  "imp_estado": "",
  "imp_pais": "MEX",
  "imp_rfc": "",
  "prov_nombre": "",
  "prov_irs": "",
  "prov_calle": "",
  "prov_ciudad": "",
  "prov_cp": "",
  "prov_pais": "USA",
  "prov_vinculacion": "0",
  "guia_numero": "",
  "guia_tipo": "M",
  "trans_codigo": "",
  "trans_vehiculo": "",
  "trans_pais": "",
  "observaciones": [],
  "facturas": [
    {{
      "numero": "",
      "fecha": "AAAAMMDD",
      "termino": "FOB",
      "moneda": "USD",
      "valor_moneda_ext": 0.00,
      "valor_dolares": 0.00,
      "peso_bruto": 0.00,
      "peso_neto": 0.00,
      "bultos": 0,
      "origen_mercancia": "USA",
      "descargo_mercancia": "MEX",
      "destino_mercancia": "MEX",
      "observaciones": "",
      "partidas": [
        {{
          "fraccion": "",
          "descripcion": "",
          "no_parte": "",
          "valor_mercancia": 0.00,
          "cantidad_comercial": 0,
          "unidad_medida": "01",
          "cantidad_tarifa": 0,
          "vinculacion": "0",
          "metodo_valoracion": "1",
          "marca": "",
          "modelo": "",
          "pais_origen": "CHN",
          "pais_comprador": "USA",
          "precio_unitario": 0.00,
          "valor_aduana": 0.00,
          "valor_dolares": 0.00,
          "umt": "1",
          "peso_neto_unitario": 0.000,
          "peso_bruto_unitario": 0.000,
          "orden_compra": "",
          "num_factura": "",
          "guia_master": "",
          "guia_house": "",
          "rendimiento_ieps": "0"
        }}
      ]
    }}
  ]
}}

Reglas:
- unidad_medida: 01=PZA/EA, 03=PAR/PR, 04=ROL, 06=PAQ/PK
- pais_origen/pais_comprador: 3 letras (CHN TWN THA USA MEX VNM IDN)
- fecha: AAAAMMDD sin guiones ni espacios
- valor_mercancia = precio extendido total de la partida
- num_factura en partida = número del 505 padre
- Extrae TODAS las partidas sin omitir ninguna"""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        messages=[{
            "role": "user",
            "content": [
                {"type":"document","source":{"type":"base64","media_type":"application/pdf","data":b64}},
                {"type":"text","text":prompt}
            ]
        }]
    )
    raw = re.sub(r"```json|```","", resp.content[0].text.strip()).strip()
    return json.loads(raw)

# ─── GENERADOR DARWIN ─────────────────────────────────────────────────────────

def build_darwin(data, cfg, modo_agente=False):
    lines = []
    warns = []
    errs  = []

    cod_imp  = trunc(cfg.get("cod_imp",""), 10)
    cod_prov = trunc(cfg.get("cod_prov",""), 10)

    def row(vals):
        return "|".join(str(v) if v is not None else "" for v in vals)

    def chk_obl(reg, campo, val):
        if not str(val).strip():
            errs.append(f"En el registro **{reg}**: falta el campo obligatorio «{campo}»")

    # CCC (solo si hay datos del importador nuevos)
    if cfg.get("incluir_ccc") and data.get("imp_nombre"):
        chk_obl("CCC","Nombre del importador", data.get("imp_nombre",""))
        chk_obl("CCC","RFC", data.get("imp_rfc",""))
        lines.append(row([
            "CCC", cod_imp,
            trunc(data.get("imp_nombre",""), 120),
            "","",
            trunc(data.get("imp_calle",""), 80),
            "","",
            trunc(data.get("imp_ciudad",""), 80),
            trunc(data.get("imp_cp",""), 10),
            trunc(data.get("imp_estado",""), 3),
            trunc(data.get("imp_pais","MEX"), 3),
            "","",
            trunc(data.get("imp_rfc",""), 13),
            trunc(data.get("imp_curp",""), 18),
            "","",""
        ]))

    # 501
    chk_obl("501","Código del Importador", cod_imp)
    chk_obl("501","Peso Bruto", data.get("enc_peso_bruto","0"))
    chk_obl("501","Número de bultos", data.get("enc_bultos","0"))

    lines.append(row([
        "501",
        trunc(cfg.get("tipo_op","1"), 1),
        trunc(cfg.get("clave_doc","A1"), 2),
        trunc(cfg.get("num_pedimento",""), 7),
        cod_imp,
        trunc(cfg.get("fletes",""), 12),
        trunc(cfg.get("seguros",""), 12),
        trunc(cfg.get("embalajes",""), 12),
        "","",
        trunc(data.get("enc_peso_bruto","0"), 14),
        trunc(data.get("enc_bultos","0"), 12),
        trunc(cfg.get("transporte","3"), 1),
        "","",
        trunc(cfg.get("zona","1"), 2),
        trunc(cfg.get("referencia",""), 20),
        "",
        trunc(cfg.get("tipo_archivo","P"), 1),
        trunc(cfg.get("pais_moneda","USA"), 3),
        "","","","",
        trunc(cfg.get("marcas",""), 35),
        ""
    ]))

    # 502 Transportista
    if cfg.get("incluir_502") and data.get("trans_codigo"):
        lines.append(row([
            "502",
            trunc(data.get("trans_codigo",""), 6),
            trunc(data.get("trans_vehiculo",""), 17),
            trunc(data.get("trans_pais",""), 3),
            ""
        ]))

    # 503 Guía
    if cfg.get("guia_numero"):
        lines.append(row([
            "503",
            trunc(cfg.get("guia_numero",""), 20),
            trunc(cfg.get("guia_tipo","M"), 1)
        ]))

    # 511 Observaciones pedimento
    for obs in cfg.get("observaciones_ped", []):
        if obs.strip():
            lines.append(row(["511", trunc(obs, 120)]))

    # PPP (solo si hay datos del proveedor nuevos)
    if cfg.get("incluir_ppp") and data.get("prov_nombre"):
        chk_obl("PPP","Nombre del proveedor", data.get("prov_nombre",""))
        lines.append(row([
            "PPP",
            cod_prov,
            trunc(data.get("prov_irs",""), 17),
            trunc(data.get("prov_nombre",""), 120),
            "","",
            trunc(data.get("prov_calle",""), 80),
            "","",
            trunc(data.get("prov_cp",""), 10),
            trunc(data.get("prov_ciudad",""), 80),
            trunc(data.get("prov_pais","USA"), 3),
            "",
            trunc(data.get("prov_vinculacion","0"), 1)
        ]))

    # 505 + 551
    for fac in data.get("facturas", []):
        num_fac = trunc(fac.get("numero",""), 40)
        chk_obl("505","Número de factura", num_fac)
        chk_obl("505","Fecha de factura", fac.get("fecha",""))
        chk_obl("505","Código del Proveedor", cod_prov)
        chk_obl("505","Valor de la factura", str(fac.get("valor_dolares","0")))

        lines.append(row([
            "505",
            num_fac,
            trunc(fac.get("fecha",""), 8),
            trunc(fac.get("termino","FOB"), 3),
            trunc(fac.get("moneda","USD"), 3),
            trunc(str(fac.get("valor_moneda_ext","0")), 14),
            trunc(str(fac.get("valor_dolares","0")), 14),
            cod_prov,
            "",
            trunc(cfg.get("pais_moneda","USA"), 3),
            "","","","",
            "","","","",
            trunc(fac.get("observaciones",""), 120),
            trunc(str(fac.get("peso_bruto","0")), 14),
            trunc(str(fac.get("peso_neto","0")), 14),
            trunc(str(fac.get("bultos","0")), 10),
            "","","",
            trunc(fac.get("origen_mercancia","USA"), 3),
            trunc(fac.get("descargo_mercancia","MEX"), 3),
            trunc(fac.get("destino_mercancia","MEX"), 3),
        ]))

        for p in fac.get("partidas", []):
            no_parte = trunc(p.get("no_parte",""), 20)
            chk_obl("551","Valor de mercancía", str(p.get("valor_mercancia","0")))
            chk_obl("551","Cantidad comercial", str(p.get("cantidad_comercial","0")))
            chk_obl("551","País de origen", p.get("pais_origen",""))

            lines.append(row([
                "551",
                trunc(p.get("fraccion",""), 8),
                trunc(p.get("descripcion",""), 250),
                no_parte,
                trunc(str(p.get("valor_mercancia","0")), 14),
                trunc(str(p.get("cantidad_comercial","0")), 15),
                trunc(str(p.get("unidad_medida","01")), 2),
                trunc(str(p.get("cantidad_tarifa","0")), 19),
                "","0","1",
                trunc(p.get("marca",""), 80),
                trunc(p.get("modelo",""), 80),
                trunc(p.get("pais_origen",""), 3),
                trunc(p.get("pais_comprador",""), 3),
                "","","","","","","","","","","",
                "","","","","","","","","","","",
                trunc(str(p.get("precio_unitario","0")), 12),
                trunc(str(p.get("valor_aduana","0")), 12),
                trunc(str(p.get("valor_dolares","0")), 14),
                trunc(str(p.get("umt","1")), 1),
                trunc(str(p.get("peso_neto_unitario","0")), 12),
                trunc(str(p.get("peso_bruto_unitario","0")), 12),
                trunc(p.get("orden_compra",""), 20),
                trunc(p.get("num_factura", fac.get("numero","")), 15),
                trunc(p.get("guia_master",""), 20),
                trunc(p.get("guia_house",""), 20),
                trunc(str(p.get("rendimiento_ieps","0")), 15),
            ]))

    lines.append("999")
    return "\n".join(lines), errs, warns

# ══════════════════════════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════════════════════════

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://www.anthropic.com/favicon.ico", width=24)
    st.markdown("### Darwin Conversor")
    st.caption("Versión 2.0 — Layout Vanguardia Tecnologías")
    st.divider()
    api_key = st.text_input(
        "🔑 API Key de Anthropic",
        type="password",
        help="Obtén tu clave en console.anthropic.com"
    )
    if api_key:
        st.markdown('<div style="color:#16a34a;font-size:12px">✅ API Key configurada</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#dc2626;font-size:12px">⚠️ Ingresa tu API Key</div>',
                    unsafe_allow_html=True)
    st.divider()
    st.caption("El archivo generado va en:\n`Darwin\\Facturas\\In`\n\nFormato: pipe `|`\nCierre: registro `999`")

# ─── TÍTULO ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="step-header">
  <h2>🛃 Conversor de Facturas → Darwin</h2>
  <p>Convierte tus facturas PDF al formato que necesita Darwin para procesar el pedimento aduanal</p>
</div>
""", unsafe_allow_html=True)

# ─── SELECTOR DE MODO ─────────────────────────────────────────────────────────
st.markdown("### ¿Quién eres?")
st.caption("Elige el modo según tu rol. Cada uno muestra solo lo que necesitas.")

col1, col2 = st.columns(2)
with col1:
    modo_usuario = st.button("👤 Soy usuario / capturista\nSolo subo facturas",
                              use_container_width=True)
with col2:
    modo_agente = st.button("🏛️ Soy agente aduanal\nNecesito control completo",
                             use_container_width=True)

if "modo" not in st.session_state:
    st.session_state.modo = None
if modo_usuario:
    st.session_state.modo = "usuario"
if modo_agente:
    st.session_state.modo = "agente"

if not st.session_state.modo:
    st.markdown("""
    <div class="info-tip">
    👆 Selecciona tu modo para comenzar.<br><br>
    <b>Modo Usuario:</b> Solo necesitas subir el PDF. Los campos técnicos ya están configurados.<br>
    <b>Modo Agente Aduanal:</b> Acceso completo a todos los campos del Layout Darwin.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

modo = st.session_state.modo
st.markdown(f"**Modo activo:** {'👤 Usuario / Capturista' if modo=='usuario' else '🏛️ Agente Aduanal'}")
st.divider()

cfg = {}

# ══════════════════════════════════════════════════════════════════════════════
# MODO USUARIO
# ══════════════════════════════════════════════════════════════════════════════
if modo == "usuario":

    # PASO 1 — Datos básicos
    st.markdown("### 📋 Paso 1 — Datos de tu empresa y proveedor")
    st.caption("Estos códigos los da tu agente aduanal. Si no los tienes, pregúntale.")

    col1, col2 = st.columns(2)
    with col1:
        cod_imp = st.text_input(
            "🏭 Código de tu empresa en Darwin",
            max_chars=10,
            placeholder="Ej: FEMCO",
            help="Tu agente aduanal te dio este código al registrar tu empresa en Darwin."
        )
        if cod_imp:
            st.markdown(f'<div class="success-msg">✅ Empresa: <b>{cod_imp.upper()}</b></div>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<div class="warn-msg">Pregunta a tu agente aduanal cuál es tu código en Darwin</div>',
                        unsafe_allow_html=True)

    with col2:
        cod_prov = st.text_input(
            "🏢 Código del proveedor en Darwin",
            max_chars=10,
            placeholder="Ej: RELIAN",
            help="Código del proveedor del que recibes la mercancía."
        )
        if cod_prov:
            st.markdown(f'<div class="success-msg">✅ Proveedor: <b>{cod_prov.upper()}</b></div>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<div class="warn-msg">Pregunta a tu agente aduanal el código de este proveedor</div>',
                        unsafe_allow_html=True)

    cfg["cod_imp"]  = cod_imp.upper() if cod_imp else ""
    cfg["cod_prov"] = cod_prov.upper() if cod_prov else ""

    st.divider()

    # PASO 2 — ¿Cómo llega la mercancía?
    st.markdown("### 🚢 Paso 2 — ¿Cómo llega la mercancía a México?")
    st.caption("Selecciona el medio de transporte principal.")

    trans_sel = st.radio(
        "Medio de transporte",
        list(TRANSPORTE_OPTS.keys()),
        index=2,
        label_visibility="collapsed"
    )
    cfg["transporte"] = TRANSPORTE_OPTS[trans_sel]

    st.divider()

    # PASO 3 — ¿Tienes número de guía?
    st.markdown("### 📦 Paso 3 — Número de guía o manifiesto *(opcional)*")
    st.caption("El número que viene en el conocimiento de embarque, guía aérea o carta porte.")

    tiene_guia = st.toggle("Tengo número de guía o manifiesto")
    if tiene_guia:
        col1, col2 = st.columns([3,1])
        with col1:
            cfg["guia_numero"] = st.text_input("Número de guía", max_chars=20,
                                                placeholder="Ej: 4653939")
        with col2:
            tipo_g = st.selectbox("Tipo", ["🗂 Maestra","📄 Doméstica"])
            cfg["guia_tipo"] = "M" if "Maestra" in tipo_g else "D"
    else:
        cfg["guia_numero"] = ""
        cfg["guia_tipo"]   = "M"

    st.divider()

    # PASO 4 — PDF
    st.markdown("### 📄 Paso 4 — Sube tu(s) factura(s)")
    st.caption("Puedes subir la factura original en inglés y/o la traducción en español. Se procesan juntas.")

    uploaded = st.file_uploader(
        "Arrastra los archivos aquí o haz clic para seleccionar",
        type=["pdf"],
        accept_multiple_files=True
    )
    if uploaded:
        st.markdown(f'<div class="success-msg">✅ {len(uploaded)} archivo(s) listo(s)</div>',
                    unsafe_allow_html=True)

    # Defaults para campos técnicos
    cfg["tipo_op"]      = "1"
    cfg["clave_doc"]    = "A1"
    cfg["zona"]         = "1"
    cfg["tipo_archivo"] = "P"
    cfg["pais_moneda"]  = "USA"
    cfg["referencia"]   = ""
    cfg["marcas"]       = ""
    cfg["fletes"]       = ""
    cfg["seguros"]      = ""
    cfg["embalajes"]    = ""
    cfg["num_pedimento"]= ""
    cfg["incluir_ccc"]  = False
    cfg["incluir_ppp"]  = False
    cfg["incluir_502"]  = False
    cfg["observaciones_ped"] = []

# ══════════════════════════════════════════════════════════════════════════════
# MODO AGENTE ADUANAL
# ══════════════════════════════════════════════════════════════════════════════
elif modo == "agente":

    st.markdown("### 🏛️ Configuración completa — Agente Aduanal")
    st.caption("Acceso a todos los campos del Layout de Factura Electrónica de Vanguardia Tecnologías.")

    # ── Registros a incluir ──────────────────────────────────────────────────
    with st.expander("① Registros a incluir en el archivo", expanded=True):
        st.caption("Los registros OBL siempre se generan. Activa los opcionales según tu operación.")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Siempre incluidos (OBL)**")
            st.markdown("✅ `501` Encabezado general")
            st.markdown("✅ `505` Datos de facturas")
            st.markdown("✅ `551` Partidas de cada factura")
            st.markdown("✅ `999` Fin de archivo")
        with col2:
            st.markdown("**Opcionales — activa los que apliquen**")
            cfg["incluir_ccc"]  = st.toggle("**CCC** — Registrar importador nuevo en Darwin",
                                             help="Cuando el importador NO está dado de alta en Darwin. Va antes del 501.")
            cfg["incluir_ppp"]  = st.toggle("**PPP** — Registrar proveedor nuevo en Darwin",
                                             help="Cuando el proveedor NO está dado de alta en Darwin. Va antes del 505.")
            cfg["incluir_502"]  = st.toggle("**502** — Datos del transportista",
                                             help="Código del transportista, vehículo y país.")
            incluir_503 = st.toggle("**503** — Guía / Manifiesto",
                                    help="Número de guía o manifiesto de transporte.")
            incluir_511 = st.toggle("**511** — Observaciones al pedimento",
                                    help="Observaciones a nivel pedimento (máx. 120 chars por renglón).")

    # ── Códigos ──────────────────────────────────────────────────────────────
    with st.expander("② Códigos de Importador y Proveedor (OBL)", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="adv-field-label">Campo 5 — Registro 501 | Máx. 10 chars | OBL</div>',
                        unsafe_allow_html=True)
            cod_imp = st.text_input("Código del Importador *", max_chars=10, key="ag_codimp",
                                     placeholder="FEMCO")
            cfg["cod_imp"] = cod_imp.upper() if cod_imp else ""
            if cfg["cod_imp"]:
                st.caption(f"✅ {cfg['cod_imp']} — {len(cfg['cod_imp'])}/10 chars")
            else:
                st.caption("⚠️ OBL — requerido")

        with col2:
            st.markdown('<div class="adv-field-label">Campo 8 — Registro 505 | Máx. 10 chars | OBL</div>',
                        unsafe_allow_html=True)
            cod_prov = st.text_input("Código del Proveedor *", max_chars=10, key="ag_codprov",
                                      placeholder="RELIAN")
            cfg["cod_prov"] = cod_prov.upper() if cod_prov else ""
            if cfg["cod_prov"]:
                st.caption(f"✅ {cfg['cod_prov']} — {len(cfg['cod_prov'])}/10 chars")
            else:
                st.caption("⚠️ OBL — requerido")

    # ── Registro 501 ─────────────────────────────────────────────────────────
    with st.expander("③ Registro 501 — Encabezado general", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="adv-field-label">Campo 2 | Máx. 1 char | OBL</div>', unsafe_allow_html=True)
            tipo_op_sel = st.selectbox("Tipo de operación *",
                                        list(OPERACION_OPTS.keys()), key="ag_tipoop")
            cfg["tipo_op"] = OPERACION_OPTS[tipo_op_sel]

            st.markdown('<div class="adv-field-label">Campo 3 | Máx. 2 chars | OBL</div>', unsafe_allow_html=True)
            clave_doc_sel = st.selectbox("Clave de Documento *",
                                          list(CLAVE_DOC_OPTS.keys()), key="ag_cladoc")
            if clave_doc_sel == "Otra (escribir manualmente)":
                cfg["clave_doc"] = st.text_input("Escribe la clave", max_chars=2, key="ag_cladoc_manual")
            else:
                cfg["clave_doc"] = CLAVE_DOC_OPTS[clave_doc_sel]

            st.markdown('<div class="adv-field-label">Campo 4 | Máx. 7 chars | OPC</div>', unsafe_allow_html=True)
            cfg["num_pedimento"] = st.text_input("Número de pedimento (OPC)", max_chars=7, key="ag_nped")

            st.markdown('<div class="adv-field-label">Campo 13 | Máx. 1 char | OBL</div>', unsafe_allow_html=True)
            trans_sel = st.selectbox("Transporte de entrada *",
                                      list(TRANSPORTE_OPTS.keys()), index=2, key="ag_trans")
            cfg["transporte"] = TRANSPORTE_OPTS[trans_sel]

        with col2:
            st.markdown('<div class="adv-field-label">Campo 16 | Máx. 2 chars | OBL</div>', unsafe_allow_html=True)
            cfg["zona"] = st.text_input("Destino o Zona *", value="1", max_chars=2, key="ag_zona",
                                         help="1=Resto del país 2=Franja/Región Fronteriza")

            st.markdown('<div class="adv-field-label">Campo 19 | Máx. 1 char | OPC</div>', unsafe_allow_html=True)
            tipo_arch_sel = st.selectbox("Tipo de Archivo",
                                          list(TIPO_ARCHIVO_OPTS.keys()), key="ag_tarch")
            cfg["tipo_archivo"] = TIPO_ARCHIVO_OPTS[tipo_arch_sel]

            st.markdown('<div class="adv-field-label">Campo 20 | Máx. 3 chars | OPC</div>', unsafe_allow_html=True)
            cfg["pais_moneda"] = st.text_input("País Moneda", value="USA", max_chars=3, key="ag_pmon")

            st.markdown('<div class="adv-field-label">Campo 17 | Máx. 20 chars | OPC</div>', unsafe_allow_html=True)
            cfg["referencia"] = st.text_input("Referencia", max_chars=20, key="ag_ref")

            st.markdown('<div class="adv-field-label">Campo 25 | Máx. 35 chars | OPC</div>', unsafe_allow_html=True)
            cfg["marcas"] = st.text_input("Marcas, Números y Bultos", max_chars=35, key="ag_marc")

        st.markdown("**Incrementables / Deducibles (OPC)**")
        col1,col2,col3 = st.columns(3)
        with col1:
            cfg["fletes"] = st.text_input("Fletes (campo 6) | máx 12", max_chars=12, key="ag_flet")
        with col2:
            cfg["seguros"] = st.text_input("Seguros (campo 7) | máx 12", max_chars=12, key="ag_seg")
        with col3:
            cfg["embalajes"] = st.text_input("Embalajes (campo 8) | máx 12", max_chars=12, key="ag_emb")

    # ── Guía 503 ─────────────────────────────────────────────────────────────
    if incluir_503:
        with st.expander("④ Registro 503 — Guía / Manifiesto", expanded=True):
            col1, col2 = st.columns([3,1])
            with col1:
                st.markdown('<div class="adv-field-label">Campo 2 | Máx. 20 chars | OBL</div>',
                            unsafe_allow_html=True)
                cfg["guia_numero"] = st.text_input("Número de Guía o Manifiesto *",
                                                    max_chars=20, key="ag_guia")
            with col2:
                st.markdown('<div class="adv-field-label">Campo 3 | 1 char | OBL</div>',
                            unsafe_allow_html=True)
                tipo_g = st.selectbox("Tipo *", ["M — Maestra","D — Doméstica"], key="ag_tguia")
                cfg["guia_tipo"] = tipo_g[0]
    else:
        cfg["guia_numero"] = ""
        cfg["guia_tipo"] = "M"

    # ── Observaciones 511 ────────────────────────────────────────────────────
    if incluir_511:
        with st.expander("⑤ Registro 511 — Observaciones al pedimento", expanded=False):
            st.caption("Máximo 120 caracteres por renglón. Agrega uno por línea.")
            obs_text = st.text_area("Observaciones (una por renglón)", height=100,
                                     key="ag_obs",
                                     help="Cada renglón genera un registro 511 separado")
            cfg["observaciones_ped"] = [l for l in obs_text.split("\n") if l.strip()]
    else:
        cfg["observaciones_ped"] = []

    # ── PDF ──────────────────────────────────────────────────────────────────
    st.markdown("### 📄 Subir facturas PDF")
    uploaded = st.file_uploader(
        "Arrastra uno o varios archivos PDF",
        type=["pdf"],
        accept_multiple_files=True,
        key="ag_pdf"
    )
    if uploaded:
        st.markdown(f'<div class="success-msg">✅ {len(uploaded)} archivo(s) listo(s)</div>',
                    unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# GENERAR — AMBOS MODOS
# ══════════════════════════════════════════════════════════════════════════════

st.divider()
if modo == "usuario":
    st.markdown("### 🚀 Paso 5 — Generar archivo para Darwin")
else:
    st.markdown("### 🚀 Generar archivo para Darwin")

faltantes = []
if not api_key:        faltantes.append("API Key de Anthropic (panel izquierdo)")
if not cfg.get("cod_imp"):  faltantes.append("Código de tu empresa")
if not cfg.get("cod_prov"): faltantes.append("Código del proveedor")
if not uploaded:            faltantes.append("Archivo PDF")

if faltantes:
    for f in faltantes:
        st.markdown(f'<div class="warn-msg">⚠️ Falta: <b>{f}</b></div>', unsafe_allow_html=True)
    st.button("Generar archivo .txt", use_container_width=True, type="primary", disabled=True)
else:
    if st.button("✅ Generar archivo .txt para Darwin",
                 use_container_width=True, type="primary"):

        client = anthropic.Anthropic(api_key=api_key)

        merged = {
            "enc_peso_bruto":"0","enc_bultos":"0",
            "imp_nombre":"","imp_calle":"","imp_ciudad":"","imp_cp":"",
            "imp_estado":"","imp_pais":"MEX","imp_rfc":"","imp_curp":"",
            "prov_nombre":"","prov_irs":"","prov_calle":"","prov_ciudad":"",
            "prov_cp":"","prov_pais":"USA","prov_vinculacion":"0",
            "trans_codigo":"","trans_vehiculo":"","trans_pais":"",
            "observaciones":[],"facturas":[]
        }

        prog = st.progress(0)
        status = st.empty()

        for i, pdf_file in enumerate(uploaded):
            pct = int((i / len(uploaded)) * 90)
            prog.progress(pct)
            status.markdown(f'<div class="info-tip">🔍 Leyendo <b>{pdf_file.name}</b>... ({i+1}/{len(uploaded)})</div>',
                            unsafe_allow_html=True)
            try:
                ext = extract_pdf(client, pdf_file.read(), cfg)

                # Merge peso / bultos
                if ext.get("enc_peso_bruto","0") not in ("0","","0.000"):
                    merged["enc_peso_bruto"] = ext["enc_peso_bruto"]
                if ext.get("enc_bultos","0") not in ("0",""):
                    merged["enc_bultos"] = ext["enc_bultos"]

                # Merge texto
                for k in ["imp_nombre","imp_calle","imp_ciudad","imp_cp","imp_estado",
                           "imp_pais","imp_rfc","imp_curp",
                           "prov_nombre","prov_irs","prov_calle","prov_ciudad",
                           "prov_cp","prov_pais","prov_vinculacion",
                           "trans_codigo","trans_vehiculo","trans_pais"]:
                    if ext.get(k) and not merged.get(k):
                        merged[k] = ext[k]

                merged["observaciones"] += ext.get("observaciones",[])

                for fac in ext.get("facturas",[]):
                    fac["cod_proveedor"] = cfg["cod_prov"]
                    merged["facturas"].append(fac)

            except Exception as e:
                st.error(f"No pude leer {pdf_file.name}: {e}")

        prog.progress(95)
        status.markdown('<div class="info-tip">⚙️ Generando archivo Darwin...</div>',
                        unsafe_allow_html=True)

        if merged["facturas"]:
            txt, errs, warns = build_darwin(merged, cfg, modo=="agente")
            prog.progress(100)
            status.empty()

            # Resultado
            st.markdown("---")
            st.markdown("### ✅ ¡Tu archivo está listo!")

            c1,c2,c3 = st.columns(3)
            with c1:
                st.markdown(f'<div class="metric-card"><div class="metric-num">{len(merged["facturas"])}</div><div class="metric-label">Facturas procesadas</div></div>', unsafe_allow_html=True)
            with c2:
                partidas = sum(len(f.get("partidas",[])) for f in merged["facturas"])
                st.markdown(f'<div class="metric-card"><div class="metric-num">{partidas}</div><div class="metric-label">Partidas extraídas</div></div>', unsafe_allow_html=True)
            with c3:
                lineas = len(txt.split("\n"))
                st.markdown(f'<div class="metric-card"><div class="metric-num">{lineas}</div><div class="metric-label">Líneas en el archivo</div></div>', unsafe_allow_html=True)

            st.markdown("")

            if errs:
                with st.expander(f"🔴 {len(errs)} problema(s) encontrado(s) — revisa antes de usar", expanded=True):
                    for e in errs:
                        st.markdown(f'<div class="error-msg">❌ {e}</div>', unsafe_allow_html=True)
                    st.caption("Estos campos son obligatorios en Darwin. El archivo se generó pero puede ser rechazado.")

            if warns:
                with st.expander(f"⚠️ {len(warns)} aviso(s)"):
                    for w in warns:
                        st.markdown(f'<div class="warn-msg">{w}</div>', unsafe_allow_html=True)

            if not errs:
                st.markdown('<div class="success-msg">🎉 Todo correcto. El archivo está listo para Darwin.</div>',
                            unsafe_allow_html=True)

            with st.expander("👁 Ver contenido del archivo"):
                st.code(txt[:2000] + ("\n..." if len(txt) > 2000 else ""), language="text")

            nombre = f"darwin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            st.download_button(
                "⬇️ Descargar archivo para Darwin",
                data=txt.encode("utf-8"),
                file_name=nombre,
                mime="text/plain",
                use_container_width=True,
                type="primary"
            )

            if modo == "usuario":
                st.info(f"📁 Guarda el archivo `{nombre}` y entrégalo a tu agente aduanal, o deposítalo en `Darwin\\Facturas\\In`")
            else:
                st.info(f"📁 Deposita `{nombre}` en `Darwin\\Facturas\\In`")
        else:
            prog.progress(100)
            status.empty()
            st.error("No pude extraer facturas del PDF. Verifica que el archivo sea legible y contenga datos de factura.")
