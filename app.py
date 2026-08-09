# IAprendo v3.6
import streamlit as st
from openai import OpenAI
import io, os, asyncio, tempfile, json, re

st.set_page_config(page_title="IAprendo", page_icon="🤖", layout="centered")

deepseek = OpenAI(
    api_key=st.secrets["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com"
)

st.markdown("<style>.stButton button{background:#4CAF50;color:white;font-size:1.2em;border-radius:15px;padding:15px}</style>", unsafe_allow_html=True)

for k in ['explicacion','quiz_ready','preguntas','respuestas','audio_data','refuerzo']:
    if k not in st.session_state:
        st.session_state[k] = None if k != 'quiz_ready' else False
        st.session_state['respuestas'] = []
        st.session_state['audio_data'] = None

st.title("🤖 IAprendo — Tu Profe Robot")
st.markdown("### 📚 ¡Hola! Soy **IArvis**, tu tutor IA.")

col1, col2 = st.columns(2)
with col1:
    nombre = st.text_input("🎓 ¿Cómo te llamas?", value="Amigo")
with col2:
    edad = st.slider("👶 ¿Cuántos años tienes?", 5, 14, 8)

materia = st.selectbox("📘 Materia:", ["Ciencias Naturales","Matematicas","Español","Inglés","Historia","Geografia","Tecnologia","Arte","Musica"])
tema = st.text_input("🌍 ¿Qué tema quieres aprender hoy?", placeholder="Ej: El sistema solar...")

def limpiar_para_voz(texto):
    t = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251\u2600-\u26FF\u2700-\u27BF\u2B50\u2764\uFE0F\u200D]', '', texto)
    t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)
    t = re.sub(r'\*(.+?)\*', r'\1', t)
    t = re.sub(r'`(.+?)`', r'\1', t)
    t = re.sub(r'#+\s*', '', t)
    t = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', t)
    t = re.sub(r':\w+:', '', t)
    t = re.sub(r'\n{2,}', '. ', t)
    t = re.sub(r'\n', ' ', t)
    t = re.sub(r'\s{2,}', ' ', t)
    return t.strip()

def generar_audio(texto):
    limpio = limpiar_para_voz(texto)
    try:
        import edge_tts
        async def gen():
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            comm = edge_tts.Communicate(limpio, "es-CO-GonzaloNNeural", rate="+50%")
            await comm.save(tmp.name)
            with open(tmp.name, "rb") as f:
                data = f.read()
            os.unlink(tmp.name)
            return data
        return asyncio.run(gen())
    except:
        from gtts import gTTS
        tts = gTTS(text=limpio, lang="es", slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        # Acelerar con ffmpeg: 1.5x
        raw = buf.read()
        tmp_in = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp_in.write(raw)
        tmp_in.close()
        tmp_out = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp_out.close()
        os.system(f"ffmpeg -y -i {tmp_in.name} -filter:a \"atempo=1.5\" -vn {tmp_out.name} 2>/dev/null")
        with open(tmp_out.name, "rb") as f:
            data = f.read()
        os.unlink(tmp_in.name)
        os.unlink(tmp_out.name)
        return data if data else raw

def preguntar(prompt):
    resp = deepseek.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7, max_tokens=800
    )
    return resp.choices[0].message.content

col_a, col_b = st.columns(2)
if col_a.button("🧠 ¡Explícame!", use_container_width=True) and tema:
    with st.spinner("Pensando..."):
        prompt = f"Hola {nombre} de {edad} anios. Explica el tema '{tema}' de {materia} de forma SUPER SENCILLA, divertida y visual, como si hablaras con un nino. Usa ejemplos cotidianos, analogias, emojis y maximo 4 parrafos. Que sea atractivo de leer. NO hagas la tarea."
        st.session_state.explicacion = preguntar(prompt)
        st.session_state.audio_data = None
    st.rerun()

if col_b.button("🔊 Escuchar (1.25x)", use_container_width=True, disabled=not st.session_state.explicacion):
    with st.spinner("Generando voz..."):
        st.session_state.audio_data = generar_audio(st.session_state.explicacion)
    st.rerun()

if st.session_state.explicacion:
    st.success(f"📖 {nombre}, aqui va:")
    st.markdown(st.session_state.explicacion)
    if st.session_state.audio_data:
        st.audio(st.session_state.audio_data, format="audio/mp3")
        st.caption("🎧 Audio a 1.25x (ya viene acelerado)")

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
            prompt = f"Crea 5 preguntas tipo test sobre '{tema}' de {materia} para un nino de {edad} anios. 3 opciones (A, B, C). Marca correcta con *. Devuelve SOLO JSON."
            try:
                txt = preguntar(prompt)
                if "```" in txt: txt = txt.split("```")[1].replace("json","").strip()
                st.session_state.preguntas = json.loads(txt)
                st.session_state.respuestas = [None]*5
                st.session_state.quiz_ready = True
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
            st.divider(); st.subheader("📚 Refuerzo Personalizado")
            with st.spinner("Preparando..."):
                fallos = [r[1] for r in resultados if r[0]=="❌"]
                prompt = f"Un nino de {edad} anios fallo estas preguntas sobre '{tema}':\n" + "\n".join(f"- {f}" for f in fallos) + "\n\nExplica de forma MUY SENCILLA, 2 parrafos por concepto, con ejemplos divertidos."
                st.info(preguntar(prompt))

st.divider()
st.caption("🤖 IAprendo v3.6 — Hermes + DeepSeek | 2026")
