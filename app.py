# IAprendo v3.0 — Tutor IA con DeepSeek
import streamlit as st
from openai import OpenAI
import edge_tts
import io, json

st.set_page_config(page_title="IAprendo", page_icon="🤖", layout="centered")

deepseek = OpenAI(
    api_key=st.secrets["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com"
)

st.markdown("<style>.stButton button{background:#4CAF50;color:white;font-size:1.2em;border-radius:15px;padding:15px}</style>", unsafe_allow_html=True)

for k in ['explicacion','quiz_ready','preguntas','respuestas','evaluado','refuerzo']:
    if k not in st.session_state:
        st.session_state[k] = None if k != 'quiz_ready' else False
        st.session_state['respuestas'] = []
        st.session_state['evaluado'] = False

st.title("🤖 IAprendo — Tu Profe Robot")
st.markdown("### 📚 ¡Hola! Soy **IArvis**, tu tutor IA.")

col1, col2 = st.columns(2)
with col1:
    nombre = st.text_input("🎓 ¿Cómo te llamas?", value="Amigo")
with col2:
    edad = st.slider("👶 ¿Cuántos años tienes?", 5, 14, 8)

materia = st.selectbox("📘 Materia:", ["Ciencias Naturales","Matematicas","Español","Inglés","Historia","Geografia","Tecnologia","Arte","Musica"])
tema = st.text_input("🌍 ¿Qué tema quieres aprender hoy?", placeholder="Ej: El sistema solar...")

def texto_a_voz(texto):
    import tempfile, base64, asyncio
    async def generar():
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        comm = edge_tts.Communicate(texto, "es-CO-GonzaloNNeural")
        await comm.save(tmp.name)
        return tmp.name
    archivo = asyncio.run(generar())
    with open(archivo, "rb") as f:
        data = f.read()
    import os; os.unlink(archivo)
    buf = io.BytesIO(data)
    buf.seek(0)
    return buf

def preguntar(prompt):
    resp = deepseek.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=800
    )
    return resp.choices[0].message.content

if st.button("🧠 ¡Explícame!", use_container_width=True) and tema:
    with st.spinner("Pensando..."):
        prompt = f"Hola {nombre} de {edad} anios. Explica el tema '{tema}' de {materia} de forma SUPER SENCILLA, como si hablaras con un nino. Usa ejemplos divertidos, analogias con cosas cotidianas, emojis, maximo 4 parrafos. NO hagas la tarea."
        st.session_state.explicacion = preguntar(prompt)
    st.success(f"📖 {nombre}, aqui va:")
    st.markdown(st.session_state.explicacion)
    if st.button("🔊 Escuchar explicacion", use_container_width=True):
        st.audio(texto_a_voz(st.session_state.explicacion), format="audio/mp3")

if st.session_state.explicacion:
    st.divider()
    st.subheader("💬 ¿Tienes dudas?")
    duda = st.text_input("Escribe tu pregunta aqui...", key="duda")
    if st.button("🤔 Responder", use_container_width=True) and duda:
        prompt = f"{nombre} ({edad} anios) pregunta sobre '{tema}': {duda}. Responde super simple, un solo parrafo, con un ejemplo concreto."
        st.info(preguntar(prompt))

    st.divider()
    st.subheader("🏆 ¡Demuestra lo que aprendiste!")
    if st.button("🚀 ¡Quiero el reto!", use_container_width=True):
        with st.spinner("Preparando preguntas..."):
            prompt = f"Crea 5 preguntas tipo test sobre '{tema}' de {materia} para un nino de {edad} anios. 3 opciones (A, B, C). Marca correcta con *. Devuelve SOLO JSON: [{{\"pregunta\":\"...\",\"opciones\":[\"A) ...\",\"B) ...\",\"C) ...\"],\"correcta\":\"A\"}}]"
            try:
                txt = preguntar(prompt)
                if "```" in txt:
                    txt = txt.split("```")[1].replace("json","").strip()
                st.session_state.preguntas = json.loads(txt)
                st.session_state.respuestas = [None]*5
                st.session_state.quiz_ready = True
                st.session_state.evaluado = False
            except:
                st.error("Error. Intenta de nuevo.")
                st.session_state.quiz_ready = False

if st.session_state.quiz_ready and st.session_state.preguntas:
    st.markdown("### 📝 Responde las 5 preguntas:")
    for i, q in enumerate(st.session_state.preguntas):
        st.markdown(f"**{i+1}. {q['pregunta']}**")
        st.session_state.respuestas[i] = st.radio("Selecciona:", q['opciones'], key=f"q_{i}", index=None)
    
    if st.button("✅ ¡Revisar!", use_container_width=True):
        correctas = sum(1 for i,q in enumerate(st.session_state.preguntas) if st.session_state.respuestas[i] and st.session_state.respuestas[i].startswith(q['correcta']))
        resultados = []
        for i, q in enumerate(st.session_state.preguntas):
            ok = st.session_state.respuestas[i] and st.session_state.respuestas[i].startswith(q['correcta'])
            resultados.append(("✅" if ok else "❌", q['pregunta'], "¡Bien!" if ok else f"Era {q['correcta']})"))
        
        st.markdown(f"## 📊 {correctas}/5")
        if correctas == 5: st.balloons(); st.success(f"🌟🌟🌟 ¡PERFECTO {nombre}!")
        elif correctas >= 3: st.info(f"🌟 ¡Muy bien {nombre}!")
        else: st.warning(f"💪 A repasar, {nombre}!")
        
        for icono, pregunta, mensaje in resultados:
            st.markdown(f"{icono} **{pregunta}** — {mensaje}")
        
        if correctas < 5:
            st.divider()
            st.subheader("📚 Refuerzo Personalizado")
            with st.spinner("Preparando..."):
                fallos = [r[1] for r in resultados if r[0]=="❌"]
                prompt = f"Un nino de {edad} anios fallo estas preguntas sobre '{tema}':\n" + "\n".join(f"- {f}" for f in fallos) + "\n\nExplica esos conceptos de forma MUY SENCILLA, 2 parrafos por concepto, con ejemplos divertidos."
                st.info(preguntar(prompt))

st.divider()
st.caption("🤖 IAprendo v3.0 — Hermes + DeepSeek | 2026")
