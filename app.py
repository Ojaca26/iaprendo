# app.py
import streamlit as st
from gtts import gTTS
from gemini_api import explicar_tema, generar_preguntas, evaluar_respuestas, responder_duda
import io
import os

st.set_page_config(page_title="IAprendo – Tu tutor IA educativo", layout="centered")
st.title("Bienvenidos a IAprendo")

st.image("imagen_materias.png", width=700)

st.markdown("""
### 👋 ¡Hola! Soy **IArvis**, tu profe robot educativo 🤖
Estoy aquí para explicarte los temas de clase de una forma divertida, fácil y con dibujos 🧠🎨

Primero necesito saber:
""")

# --- Datos del niño ---
nombre = st.text_input("🎓 ¿Cómo te llamas?") or "Explorador"
edad = st.number_input("👶 ¿Cuántos años tienes?", min_value=5, max_value=14, step=1)
materia = st.selectbox("📈 Elige una materia para aprender hoy:", [
    "Ciencias", "Matemáticas", "Español", "Inglés", "Religión",
    "Historia", "Tecnología", "Arte", "Sociales", "Música", "Deportes"
])
tema = st.text_input("🌍 ¿Qué tema estás viendo en clase?")

# --- Explicación del tema ---
if st.button("¡Explícame el tema!") and tema:
    explicacion = explicar_tema(nombre, materia, tema, edad)
    st.session_state.explicacion = explicacion
    st.session_state.tema_listo = True

if st.session_state.get("tema_listo"):
    st.markdown(f"### 📚 Hola **{nombre}**, aquí está la explicación:")
    st.write(st.session_state.explicacion)

    # Reproducir voz si está en local
    if os.getenv("LOCAL_ENV") == "1":
        if st.button("🔊 Leer en voz alta"):
            tts = gTTS(text=st.session_state.explicacion, lang="es", slow=False)
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            audio_fp.seek(0)
            st.audio(audio_fp, format="audio/mp3")
            st.info("🎧 Si quieres, puedes acelerar el audio desde el reproductor (por ejemplo, a velocidad 1.25x). ¡Tú decides!")

    st.markdown("---")
    st.subheader("💬 ¡Hazme una pregunta si quieres saber más!")
    duda = st.text_input("👫 Escribe tu duda aquí:")
    if st.button("Responder duda") and duda:
        respuesta = responder_duda(nombre, duda, tema, materia, edad)
        st.success(respuesta)

    st.markdown("---")
    st.subheader("🏆 ¡Reto de 7 preguntas para demostrar lo aprendido!")

    if st.button("🚀 Iniciar Reto Interactivo"):
        with st.spinner("⏳ Estoy preparando tus preguntas, un momento por favor..."):
            st.session_state.preguntas, st.session_state.respuestas_correctas = generar_preguntas(materia, tema, edad)
            st.session_state.respuestas_usuario = [""] * len(st.session_state.preguntas)
            st.session_state.reto_en_progreso = True

# --- Reto en progreso ---
if st.session_state.get("reto_en_progreso"):
    if not st.session_state.preguntas:
        st.error("⚠️ No se pudieron generar preguntas. Intenta de nuevo o cambia el tema.")
        st.session_state.reto_en_progreso = False
    else:
        st.success("✅ ¡Preguntas generadas! ¡Mucha suerte!")

        st.markdown("### 🖋️ Responde las siguientes preguntas:")
        for i, pregunta in enumerate(st.session_state.preguntas):
            st.markdown(f"**{i+1}. {pregunta}**")
            st.session_state.respuestas_usuario[i] = st.radio(
                "Selecciona una opción:",
                ["Sí", "No"],
                key=f"pregunta_{i}"
            )

        if st.button("Evaluar mis respuestas"):
            respuestas_correctas = 0

            for resp_usuario, resp_correcta in zip(st.session_state.respuestas_usuario, st.session_state.respuestas_correctas):
                if resp_usuario.strip().lower() == resp_correcta.strip().lower():
                    respuestas_correctas += 1

            st.markdown("### 📜 Resultado del Reto")
            st.success(f"Respondiste correctamente {respuestas_correctas} de 7 preguntas.")

            if respuestas_correctas >= 6:
                st.success(f"🌟🌟🌟 ¡Excelente {nombre}! ¡Eres un campeón!")
            elif respuestas_correctas >= 4:
                st.info(f"🌟🌟 Muy bien {nombre}, sigue esforzándote.")
            else:
                st.warning(f"😅 No te preocupes {nombre}, vamos a reforzar un poco más.")

            # Activar plan de refuerzo si tuvo menos de 7 aciertos
            if respuestas_correctas < 7:
                plan_refuerzo = evaluar_respuestas(
                    st.session_state.preguntas,
                    st.session_state.respuestas_usuario,
                    tema, materia, edad
                )
                st.markdown("---")
                st.subheader("📊 Plan de Refuerzo Personalizado")
                st.info(plan_refuerzo)

            st.session_state.reto_en_progreso = False
