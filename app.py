# IAprendo v5.1 — audio SIEMPRE 1.5x real (PyAV/FFmpeg embebido) + quiz robusto
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

def acelerar_audio_pyav(ruta_in, ruta_out, factor="1.5"):
    """Acelera un MP3 con FFmpeg embebido (PyAV). Funciona en Streamlit Cloud sin binarios externos."""
    import av
    inp = av.open(ruta_in)
    astream = inp.streams.audio[0]
    g = av.filter.Graph()
    src = g.add_abuffer(template=astream)
    atempo = g.add('atempo', factor)
    snk = g.add('abuffersink')
    src.link_to(atempo)
    atempo.link_to(snk)
    g.configure()
    out = av.open(ruta_out, 'w')
    ost = out.add_stream('mp3', rate=astream.codec_context.sample_rate)
    ost.layout = 'mono'
    ost.format = 's16p'
    def drain():
        frames = []
        while True:
            try:
                frames.append(g.pull())
            except (av.error.BlockingIOError, StopIteration, av.error.EOFError):
                break
        return frames
    def mux(frames):
        for f in frames:
            f.pts = None
            for p in ost.encode(f):
                out.mux(p)
    for frame in inp.decode(audio=0):
        g.push(frame)
        mux(drain())
    g.push(None)
    mux(drain())
    for p in ost.encode():
        out.mux(p)
    out.close()
    inp.close()

def generar_audio(texto):
    limpio = limpiar_para_voz(texto)
    tmp_in = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp_in.close()
    tmp_out = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp_out.close()
    try:
        # Voz natural de Edge (si responde), a velocidad normal
        import edge_tts
        async def gen():
            comm = edge_tts.Communicate(limpio, "es-CO-GonzaloNNeural")
            await comm.save(tmp_in.name)
        asyncio.run(gen())
    except Exception:
        # Fallback: Google TTS (siempre funciona)
        from gtts import gTTS
        buf = io.BytesIO()
        gTTS(text=limpio, lang="es", slow=False).write_to_fp(buf)
        buf.seek(0)
        with open(tmp_in.name, "wb") as f:
            f.write(buf.read())
    # Acelerar SIEMPRE a 1.5x con FFmpeg embebido (PyAV)
    try:
        acelerar_audio_pyav(tmp_in.name, tmp_out.name, "1.5")
        if not os.path.exists(tmp_out.name) or os.path.getsize(tmp_out.name) == 0:
            raise RuntimeError("audio vacio")
    except Exception:
        # Si PyAV falla, devolver el audio normal (mejor que nada)
        os.rename(tmp_in.name, tmp_out.name)
    with open(tmp_out.name, "rb") as f:
        data = f.read()
    for f in (tmp_in.name, tmp_out.name):
        try: os.unlink(f)
        except Exception: pass
    return data

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

if col_b.button("🔊 Escuchar (1.5x)", use_container_width=True, disabled=not st.session_state.explicacion):
    with st.spinner("Generando voz..."):
        st.session_state.audio_data = generar_audio(st.session_state.explicacion)
    st.rerun()

if st.session_state.explicacion:
    st.success(f"📖 {nombre}, aqui va:")
    st.markdown(st.session_state.explicacion)
    if st.session_state.audio_data:
        st.audio(st.session_state.audio_data, format="audio/mp3")
        st.caption("🎧 Audio acelerado 1.5x (ya viene rápido)")

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
                datos = json.loads(txt)
                # Normalizar: puede venir como lista o dict con clave 'preguntas'
                if isinstance(datos, dict):
                    datos = datos.get("preguntas") or datos.get("questions") or list(datos.values())
                preguntas = []
                for q in datos:
                    if isinstance(q, str):
                        continue
                    pregunta = q.get("pregunta") or q.get("question") or ""
                    opciones = q.get("opciones") or q.get("options") or []
                    correcta = q.get("correcta") or q.get("answer") or q.get("correct") or ""
                    # Si la correcta viene marcada con * dentro de las opciones
                    if not correcta:
                        for op in opciones:
                            if isinstance(op, str) and "*" in op:
                                correcta = op.replace("*", "").strip()
                                break
                    opciones = [str(op).replace("*", "").strip() for op in opciones]
                    if pregunta and opciones:
                        preguntas.append({"pregunta": pregunta, "opciones": opciones, "correcta": str(correcta).strip()})
                st.session_state.preguntas = preguntas
                st.session_state.respuestas = [None]*len(preguntas)
                st.session_state.quiz_ready = bool(preguntas)
            except:
                st.error("Error. Intenta de nuevo.")
                st.session_state.quiz_ready = False

if st.session_state.quiz_ready and st.session_state.preguntas:
    st.markdown("### 📝 Responde las 5 preguntas:")
    for i, q in enumerate(st.session_state.preguntas):
        st.markdown(f"**{i+1}. {q['pregunta']}**")
        st.session_state.respuestas[i] = st.radio("Selecciona:", q['opciones'], key=f"q_{i}", index=None)
    
    if st.button("✅ ¡Revisar!", use_container_width=True):
        def _norm(s):
            s = s.strip()
            m = re.match(r'^([A-D])\s*[).:]\s*', s)
            if m:
                return m.group(1).upper(), re.sub(r'^[A-D]\s*[).:]\s*', '', s).strip().lower()
            if len(s) == 1 and s.upper() in "ABCD":
                return s.upper(), ""
            return None, s.lower()
        def es_correcta(i, q):
            sel = st.session_state.respuestas[i]
            if not sel: return False
            c = q['correcta'].strip()
            sl, stx = _norm(sel)
            cl, ctx = _norm(c)
            if cl and sl and cl == sl:
                return True
            if cl and not ctx:  # la correcta es solo la letra (ej: "A")
                return sl == cl
            if ctx and stx:
                return stx == ctx or stx.startswith(ctx) or ctx.startswith(stx) or sel.strip() == c
            return sel.strip() == c
        correctas = sum(1 for i,q in enumerate(st.session_state.preguntas) if es_correcta(i,q))
        resultados = []
        for i, q in enumerate(st.session_state.preguntas):
            ok = es_correcta(i,q)
            resultados.append(( "✅" if ok else "❌", q['pregunta'], "¡Bien!" if ok else f"Era {q['correcta']})"))
        
        total = len(st.session_state.preguntas)
        st.markdown(f"## 📊 {correctas}/{total}")
        if correctas == total: st.balloons(); st.success(f"🌟🌟🌟 ¡PERFECTO {nombre}!")
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
st.caption("🤖 IAprendo v5.1 — Hermes + DeepSeek | 2026")
