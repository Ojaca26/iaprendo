# app.py
import streamlit as st
from gemini_api import explicar_tema, generar_preguntas, evaluar_respuestas, responder_duda
import pyttsx3
import random

st.set_page_config(page_title="IAprendo – Tu tutor IA educativo", layout="centered")
st.title("Bienvenidos a IAprendo")

st.image("imagen_materias.png", width=700)

# --- Inicializar variables de session_state ---
if "preguntas" not in st.session_state:
    st.session_state.preguntas = []
if "opciones" not in st.session_state:
    st.session_state.opciones = []
if "respuestas" not in st.session_state:
    st.session_state.respuestas = []
if "reto_en_progreso" not in st.session_state:
    st.session_state.reto_en_progreso = False
if "tema_listo" not in st.session_state:
    st.session_state.tema_listo = False

st.markdown("""
### 👋 ¡Hola! Soy **IArvis**, tu profe robot educativo 🤖
Estoy aquí para explicarte los temas de clase de una forma divertida, fácil y con dibujos 🦱🎨

Primero necesito saber:
""")

edad = st.number_input("¿Cuántos años tienes?", min_value=5, max_value=14, step=1)
materia = st.selectbox("Elige una materia para aprender hoy:", [
    "Ciencias", "Matemáticas", "Español", "Inglés", "Religión",
    "Historia", "Tecnología", "Arte", "Ética", "Música", "Deportes"
])
tema = st.text_input("¿Qué tema estás viendo en clase?")

if st.button("¡Explícame el tema!") and tema:
    explicacion = explicar_tema(materia, tema, edad)
    st.session_state.explicacion = explicacion
    st.session_state.tema_listo = True

if st.session_state.tema_listo:
    st.markdown("### 📘 Explicación del Tema")
    st.write(st.session_state.explicacion)

    if st.button("🔊 Leer en voz alta"):
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.say(st.session_state.explicacion)
        engine.runAndWait()

    st.markdown("---")
    st.subheader("💬 ¿Quieres saber más sobre este tema o dudas? Escríbeme, te contesto una a una👍")
    duda = st.text_input("Pregunta:")
    if st.button("Responder duda") and duda:
        respuesta = responder_duda(duda, tema, materia, edad)
        st.success(respuesta)

    st.markdown("---")
    st.subheader("🎯 ¡Reto de 7 preguntas para demostrar lo aprendido!")

    if st.button("Iniciar Reto Interactivo"):
        st.session_state.preguntas, st.session_state.opciones = generar_preguntas(materia, tema, edad)
        st.session_state.respuestas = ["" for _ in st.session_state.preguntas]
        st.session_state.reto_en_progreso = True

if st.session_state.reto_en_progreso:
    if not st.session_state.preguntas:
        st.error("⚠️ No se pudieron generar preguntas. Intenta de nuevo o cambia el tema.")
        st.session_state.reto_en_progreso = False
    else:
        st.markdown("### 🎓 Responde las siguientes preguntas:")

        for i, (pregunta, opciones) in enumerate(zip(st.session_state.preguntas, st.session_state.opciones)):
            st.markdown(f"**{i+1}. {pregunta}**")
            st.session_state.respuestas[i] = st.radio("", opciones, key=f"pregunta_{i}")

        if st.button("Evaluar mis respuestas"):
            resultado = evaluar_respuestas(
                st.session_state.preguntas,
                st.session_state.respuestas,
                tema, materia, edad
            )

            st.markdown("### 📝 Resultado del Reto")
            st.write(resultado)

            correctas = sum(1 for r in st.session_state.respuestas if "*" in r)

            st.markdown("---")
            st.subheader("🏆 Resultado Final:")

            if correctas >= 6:
                st.success(f"🌟🌟🌟 ¡Excelente! Respondiste {correctas} de 7 correctamente. ¡Eres un campeón!")
            elif correctas >= 4:
                st.success(f"🌟🌟 Muy bien! Respondiste {correctas} de 7 correctamente. Sigue así.")
            elif correctas >= 1:
                st.info(f"🌟 Buen intento. Respondiste {correctas} de 7 correctamente. ¡Podemos reforzar juntos!")
            else:
                st.warning("😅 No te preocupes, ¡vamos a aprender juntos desde el principio!")

            st.session_state.reto_en_progreso = False
