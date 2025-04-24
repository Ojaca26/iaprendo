# app.py
import streamlit as st
from gemini_api import explicar_tema, generar_preguntas, evaluar_respuesta, responder_duda
import pyttsx3

st.set_page_config(page_title="IAprendo – Tu tutor IA educativo", layout="centered")
st.title("Bienvenido a IAprendo")

st.image("Imagen_IAprendo.png", width=200)

st.markdown("""
### 👋 ¡Hola! Soy **IAprendo**, tu profe robot educativo
Estoy aquí para explicarte los temas de clase de una forma divertida, fácil y con dibujos 🧠🎨

Primero necesito saber:
""")

edad = st.number_input("¿Cuántos años tienes?", min_value=5, max_value=14, step=1)
materia = st.selectbox("Elige una materia para aprender hoy:", [
    "Ciencias", "Matemáticas", "Español", "Inglés", "Religión",
    "Historia", "Tecnología", "Arte", "Ética", "Música"
])
tema = st.text_input("¿Qué tema estás viendo en clase?")

if st.button("¡Explícame el tema!") and tema:
    explicacion, imagen_url = explicar_tema(materia, tema, edad)
    st.session_state.explicacion = explicacion
    st.session_state.tema_listo = True

if st.session_state.get("tema_listo"):
    st.markdown("### 📘 Respuesta de IAprendo")
    st.write(st.session_state.explicacion)
    st.image(f"https://source.unsplash.com/featured/?{tema},educacion,niños", caption=f"Imagen educativa sobre: {tema}")

    if st.button("🔊 Leer en voz alta"):
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.say(st.session_state.explicacion)
        engine.runAndWait()

    st.markdown("---")
    st.subheader("💬 ¿Tienes alguna duda o quieres saber más sobre este tema?")
    duda = st.text_input("Escríbela aquí y presiona Enter o clic en el botón:")
    if st.button("Responder duda") and duda:
        respuesta = responder_duda(duda, tema, materia, edad)
        st.success(respuesta)

    st.markdown("---")
    st.subheader("🎯 ¡Hora de poner en práctica lo aprendido!")

    if st.button("Iniciar actividad interactiva"):
        st.session_state.preguntas, st.session_state.opciones = generar_preguntas(materia, tema, edad)
        st.session_state.respuestas = [""] * len(st.session_state.preguntas)

if "preguntas" in st.session_state and "opciones" in st.session_state:
    for i, (pregunta, opciones) in enumerate(zip(st.session_state.preguntas, st.session_state.opciones)):
        st.markdown(f"**{i+1}. {pregunta}**")
        st.session_state.respuestas[i] = st.radio("", opciones, key=f"pregunta_{i}")

    if st.button("Evaluar mis respuestas"):
        resultado, plan = evaluar_respuesta(
            st.session_state.preguntas,
            st.session_state.respuestas,
            tema, materia, edad
        )
        st.markdown("### 📝 Resultado")
        st.write(resultado)
        if plan:
            st.warning(plan)
