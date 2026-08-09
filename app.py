# IAprendo v5.3 — audio 1.5x con 3 planes (edge-tts → gTTS multi-dominio → voz navegador)
import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import io, os, asyncio, tempfile, json, re
st.set_page_config(page_title="IAprendo", page_icon="🤖", layout="centered")

deepseek = OpenAI(
    api_key=st.secrets["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com"
)

st.markdown("<style>.stButton button{background:#4CAF50;color:white;font-size:1.2em;border-radius:15px;padding:15px}</style>", unsafe_allow_html=True)

for k in ['explicacion','quiz_ready','preguntas','respuestas','audio_data','refuerzo','audio_errores']:
    if k not in st.session_state:
        st.session_state[k] = None if k != 'quiz_ready' else False
        st.session_state['respuestas'] = []
        st.session_state['audio_data'] = None
        st.session_state['audio_errores'] = None

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
    """Genera voz y la acelera a 1.5x. Prueba edge-tts, luego gTTS con varios dominios.
    Devuelve (bytes_audio o None, lista de errores para diagnostico)."""
    import time
    limpio = limpiar_para_voz(texto)
    errores = []

    def acelerar(ruta_in):
        tmp_out = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp_out.close()
        try:
            acelerar_audio_pyav(ruta_in, tmp_out.name, "1.5")
            if not os.path.exists(tmp_out.name) or os.path.getsize(tmp_out.name) == 0:
                raise RuntimeError("audio vacio tras acelerar")
            with open(tmp_out.name, "rb") as f:
                data = f.read()
            os.unlink(ruta_in)
            os.unlink(tmp_out.name)
            return data
        except Exception as e:
            errores.append(f"pyav: {str(e)[:80]}")
            with open(ruta_in, "rb") as f:
                data = f.read()
            os.unlink(ruta_in)
            return data  # audio normal (mejor que nada)

    # Intento 1: edge-tts (voz natural Gonzalo), 2 reintentos
    for intento in range(2):
        tmp_in = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp_in.close()
        try:
            import edge_tts
            async def gen():
                comm = edge_tts.Communicate(limpio, "es-CO-GonzaloNNeural")
                await comm.save(tmp_in.name)
            asyncio.run(gen())
            if os.path.getsize(tmp_in.name) > 100:
                return acelerar(tmp_in.name)
            raise RuntimeError("edge-tts devolvio audio vacio")
        except Exception as e:
            errores.append(f"edge-tts: {str(e)[:80]}")
            try: os.unlink(tmp_in.name)
            except Exception: pass
            time.sleep(1.5)

    # Intento 2: gTTS con varios dominios (Google bloquea algunos desde datacenters)
    for tld in ("es", "com.mx", "com"):
        for intento in range(2):
            tmp_in = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp_in.close()
            try:
                from gtts import gTTS
                buf = io.BytesIO()
                gTTS(text=limpio, lang="es", slow=False, tld=tld).write_to_fp(buf)
                buf.seek(0)
                with open(tmp_in.name, "wb") as f:
                    f.write(buf.read())
                if os.path.getsize(tmp_in.name) > 100:
                    return acelerar(tmp_in.name)
                raise RuntimeError("gTTS devolvio audio vacio")
            except Exception as e:
                errores.append(f"gTTS({tld}): {str(e)[:80]}")
                try: os.unlink(tmp_in.name)
                except Exception: pass
                time.sleep(1)

    return None, errores

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
        st.session_state.audio_errores = None
    st.rerun()

if col_b.button("🔊 Escuchar (1.5x)", use_container_width=True, disabled=not st.session_state.explicacion):
    with st.spinner("Generando voz..."):
        resultado = generar_audio(st.session_state.explicacion)
        if isinstance(resultado, tuple):
            st.session_state.audio_data, st.session_state.audio_errores = resultado
        else:
            st.session_state.audio_data = resultado
            st.session_state.audio_errores = []
    st.rerun()

if st.session_state.explicacion:
    st.success(f"📖 {nombre}, aqui va:")
    st.markdown(st.session_state.explicacion)
    if st.session_state.audio_data:
        st.audio(st.session_state.audio_data, format="audio/mp3")
        st.caption("🎧 Audio acelerado 1.5x (ya viene rápido)")
    elif st.session_state.get("audio_errores") is not None:
        # Plan C: voz del navegador (Web Speech API) - no depende de servidores
        texto_js = json.dumps(st.session_state.explicacion)
        st.components.v1.html(f"""
        <style>
          .btn-voz {{ background:#4CAF50; color:white; font-size:1.2em; border:none;
                       border-radius:15px; padding:15px 30px; cursor:pointer; width:100%; }}
          .btn-voz:hover {{ background:#45a049; }}
        </style>
        <button class="btn-voz" onclick="leer()">🔊 Escuchar (1.5x)</button>
        <p style="color:#666;font-size:0.85em;text-align:center;margin-top:6px">
          Voz del dispositivo (los servidores de voz están saturados)
        </p>
        <script>
        function leer(){{
          const t = {texto_js};
          if (!('speechSynthesis' in window)) {{ alert('Tu navegador no soporta voz.'); return; }}
          speechSynthesis.cancel();
          const u = new SpeechSynthesisUtterance(t);
          u.lang = 'es-CO';
          u.rate = 1.5;
          u.pitch = 1.0;
          speechSynthesis.speak(u);
        }}
        </script>
        """, height=110)
        st.caption("⚠️ No se pudo generar el archivo de voz (servidores externos bloqueados). Usa el botón de arriba.")

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
                    correcta = q.get("correcta") or q.get("answer") or q.get("correct") or ""
                    opciones = q.get("opciones") or q.get("options") or []
                    # opciones puede ser dict {"A": "Venus"}, lista, o string multilinea
                    if isinstance(opciones, dict):
                        opciones = [f"{k}) {v}" if not str(v).lstrip().upper().startswith(str(k).upper() + ")") else str(v) for k, v in opciones.items()]
                    elif isinstance(opciones, str):
                        opciones = [o.strip() for o in opciones.replace("\r","").split("\n") if o.strip()] or [opciones]
                    elif isinstance(opciones, (list, tuple)):
                        opciones = [str(o) for o in opciones]
                    else:
                        opciones = []
                    # Si la correcta viene marcada con * dentro de las opciones
                    if not correcta:
                        for op in opciones:
                            if isinstance(op, str) and "*" in op:
                                correcta = op.replace("*", "").strip()
                                break
                    opciones = [str(op).replace("*", "").strip() for op in opciones if str(op).strip()]
                    # Asegurar prefijo de letra si las opciones vienen sin él
                    opciones_final = []
                    for idx, op in enumerate(opciones):
                        if not re.match(r'^[A-D]\s*[).:]', op):
                            op = f"{chr(65+idx)}) {op}"
                        opciones_final.append(op)
                    # Limpiar correcta: "B)" -> "B"
                    correcta = re.sub(r'^([A-D])\s*[).:]?\s*$', r'\1', str(correcta).strip())
                    if pregunta and opciones_final:
                        preguntas.append({"pregunta": pregunta, "opciones": opciones_final, "correcta": correcta})
                st.session_state.preguntas = preguntas
                st.session_state.respuestas = [None]*len(preguntas)
                st.session_state.quiz_ready = bool(preguntas)
                if not preguntas:
                    st.error("No se pudieron leer las preguntas. Intenta de nuevo.")
            except:
                st.error("Error. Intenta de nuevo.")
                st.session_state.quiz_ready = False

if st.session_state.quiz_ready and st.session_state.preguntas:
    total = len(st.session_state.preguntas)
    st.markdown(f"### 📝 Responde las {total} preguntas:")
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
            # Mostrar la opcion completa como respuesta correcta (no solo la letra)
            correcta_texto = q['correcta'].strip()
            for op in q['opciones']:
                if _norm(op)[0] and _norm(op)[0] == _norm(correcta_texto)[0]:
                    correcta_texto = op
                    break
            resultados.append(( "✅" if ok else "❌", q['pregunta'], "¡Bien!" if ok else f"Era {correcta_texto}"))
        
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
st.caption("🤖 IAprendo v5.3 — Hermes + DeepSeek | 2026")
