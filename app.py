# IAprendo v2.0 — Tu tutor IA educativo con voz
import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import io, os, json

# Config
st.set_page_config(page_title="IAprendo 🎓", page_icon="🤖", layout="centered")
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Estilos para niños
st.markdown("""
<style>
    .big { font-size: 1.4em; }
    .correct { color: green; font-weight: bold; }
    .wrong { color: red; }
    .stButton button { background: #4CAF50; color: white; font-size: 1.2em; border-radius: 15px; padding: 15px; }
</style>
""", unsafe_allow_html=True)

# Init session
for k in ['explicacion','quiz_ready','preguntas','respuestas','evaluado','refuerzo']:
    if k not in st.session_state:
        st.session_state[k] = None if k != 'quiz_ready' else False
        st.session_state['respuestas'] = []
        st.session_state['evaluado'] = False

st.title("🤖 IAprendo — Tu Profe Robot")
st.markdown("### 📚 ¡Hola! Soy **IArvis**, tu tutor IA. Te explico, te escucho y jugamos.")

# ── Paso 1: Datos ──
col1, col2 = st.columns(2)
with col1:
    nombre = st.text_input("🎓 ¿Cómo te llamas?", value="Amigo")
with col2:
    edad = st.slider("👶 ¿Cuántos años tienes?", 5, 14, 8)

materia = st.selectbox("📘 Materia:", ["Ciencias Naturales","Matemáticas","Español","Inglés","Historia","Geografía","Tecnología","Arte","Música"])
tema = st.text_input("🌍 ¿Qué tema quieres aprender hoy?", placeholder="Ej: El sistema solar, las fracciones...")

# ── Función: Texto a Voz ──
def texto_a_voz(texto):
    tts = gTTS(text=texto, lang="es", slow=False, tld="com.mx")
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf

# ── Paso 2: Explicación ──
if st.button("🧠 ¡Explícame!", use_container_width=True) and tema:
    with st.spinner("Pensando la mejor explicación..."):
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = f"Hola {nombre} de {edad} años. Explica el tema '{tema}' de {materia} de forma SUPER SENCILLA, como si hablaras con un niño. Usa ejemplos divertidos, analogías con cosas cotidianas, emojis, y máximo 4 párrafos. NO hagas la tarea, solo explica para que entienda."
        resp = model.generate_content(prompt)
        st.session_state.explicacion = resp.text
    
    st.success(f"📖 {nombre}, aquí va:")
    st.markdown(st.session_state.explicacion)
    
    # Botón de audio
    if st.button("🔊 Escuchar explicación", use_container_width=True):
        audio = texto_a_voz(st.session_state.explicacion)
        st.audio(audio, format="audio/mp3")
        st.caption("🎧 Subí el volumen y escuchá tranquilo")

# ── Paso 3: Preguntas del niño ──
if st.session_state.explicacion:
    st.divider()
    st.subheader("💬 ¿Tienes dudas? Pregúntame lo que quieras")
    duda = st.text_input("Escribe tu pregunta aquí...", key="duda_input")
    if st.button("🤔 Responder", use_container_width=True) and duda:
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = f"{nombre} ({edad} años) pregunta sobre '{tema}' de {materia}: {duda}. Responde de forma súper simple, un solo párrafo, con un ejemplo concreto."
        resp = model.generate_content(prompt)
        st.info(resp.text)

    # ── Paso 4: Quiz ──
    st.divider()
    st.subheader("🏆 ¡Demuestra lo que aprendiste!")
    
    if st.button("🚀 ¡Quiero el reto!", use_container_width=True):
        with st.spinner("Preparando preguntas..."):
            model = genai.GenerativeModel("gemini-2.0-flash")
            prompt = f"Crea 5 preguntas tipo test sobre '{tema}' de {materia} para un niño de {edad} años. 3 opciones cada una (A, B, C). Marca la correcta con *. Devuelve SOLO JSON: [{{"pregunta":"...","opciones":["A) ...","B) ...","C) ..."],"correcta":"A"}}]"
            try:
                resp = model.generate_content(prompt)
                txt = resp.text.strip()
                if "```" in txt:
                    txt = txt.split("```")[1].replace("json","").strip()
                qdata = json.loads(txt)
                st.session_state.preguntas = qdata
                st.session_state.respuestas = [None]*5
                st.session_state.quiz_ready = True
                st.session_state.evaluado = False
            except:
                st.error("Error generando preguntas. Intenta de nuevo.")
                st.session_state.quiz_ready = False

# ── Mostrar quiz ──
if st.session_state.quiz_ready and st.session_state.preguntas:
    st.markdown("### 📝 Responde las 5 preguntas:")
    for i, q in enumerate(st.session_state.preguntas):
        st.markdown(f"**{i+1}. {q['pregunta']}**")
        st.session_state.respuestas[i] = st.radio(
            f"Selecciona:", q['opciones'],
            key=f"q_{i}", index=None
        )
    
    if st.button("✅ ¡Revisar mis respuestas!", use_container_width=True):
        correctas = 0
        resultados = []
        for i, q in enumerate(st.session_state.preguntas):
            respuesta_dada = st.session_state.respuestas[i]
            correcta = q['correcta']
            if respuesta_dada and respuesta_dada.startswith(correcta):
                correctas += 1
                resultados.append(("✅", q['pregunta'], "¡Bien!"))
            else:
                resultados.append(("❌", q['pregunta'], f"Era {correcta})"))
        
        st.session_state.evaluado = True
        st.markdown(f"## 📊 Resultado: {correctas}/5")
        
        if correctas == 5:
            st.balloons()
            st.success(f"🌟🌟🌟 ¡PERFECTO {nombre}! ¡Eres un genio!")
        elif correctas >= 3:
            st.info(f"🌟 ¡Muy bien {nombre}! Vas por buen camino.")
        else:
            st.warning(f"💪 No te preocupes {nombre}, vamos a repasar juntos.")
        
        # Mostrar resultados
        for icono, pregunta, mensaje in resultados:
            st.markdown(f"{icono} **{pregunta}** — {mensaje}")
        
        # ── Paso 5: Refuerzo ──
        if correctas < 5:
            st.divider()
            st.subheader("📚 Refuerzo Personalizado")
            with st.spinner("Preparando material de refuerzo..."):
                model = genai.GenerativeModel("gemini-2.0-flash")
                fallos = [r[1] for r in resultados if r[0]=="❌"]
                fallos_txt = "\n".join(f"- {f}" for f in fallos)
                prompt = f"Un niño de {edad} años falló estas preguntas sobre '{tema}' ({materia}):\n{fallos_txt}\n\nExplica de nuevo esos conceptos de forma MUY SENCILLA (máximo 2 párrafos por concepto), con ejemplos divertidos y emojis. Que el niño entienda dónde se equivocó y cómo recordarlo mejor."
                resp = model.generate_content(prompt)
                st.session_state.refuerzo = resp.text
                st.info(st.session_state.refuerzo)

st.divider()
st.caption("🤖 IAprendo v2.0 — Hecho con cariño por Hermes + Gemini | 2026")
