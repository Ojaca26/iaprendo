# gemini_api.py
import google.generativeai as genai
import json
import streamlit as st

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def explicar_tema(materia, tema, edad):
    prompt = f"""
Explica de forma clara, amigable y en español para un niño de {edad} años el tema: '{tema}'
en la materia de {materia}. Usa ejemplos sencillos, emojis y termina sugiriendo
una imagen representativa para niños sobre el tema.
"""
    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
    response = model.generate_content(prompt)
    texto = response.text
    imagen_url = f"https://source.unsplash.com/featured/?{tema},educacion,niños"
    return texto, imagen_url

def generar_preguntas(materia, tema, edad):
    prompt = f"""
Crea 7 preguntas interactivas sobre el tema '{tema}' de la materia {materia} para un niño de {edad} años.
Redáctalas totalmente en español. Para cada pregunta, incluye tres opciones de respuesta (a, b, c), y marca la correcta con un asterisco (*).
Devuelve el resultado en formato JSON como lista de objetos: 
{{"pregunta": "...", "opciones": ["a) ...", "b) ...", "c) ..."], "correcta": "opción correcta sin asterisco"}}
"""
    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
    response = model.generate_content(prompt)

    try:
        preguntas_json = json.loads(response.text)
    except:
        preguntas_json = []

    preguntas = [p["pregunta"] for p in preguntas_json]
    opciones = [p["opciones"] for p in preguntas_json]
    return preguntas, opciones

def evaluar_respuesta(preguntas, respuestas, tema, materia, edad):
    prompt = f"""
Evalúa las respuestas de un niño de {edad} años al tema '{tema}' en {materia}.
Indica si respondió bien o mal en cada caso. Luego sugiere un plan de refuerzo si hay errores.
"""
    for p, r in zip(preguntas, respuestas):
        prompt += f"\nPregunta: {p}\nRespuesta del niño: {r}"

    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
    response = model.generate_content(prompt)
    resultado = response.text
    plan = "🎯 Plan de refuerzo incluido" if "refuerzo" in resultado.lower() else None
    return resultado, plan

def responder_duda(pregunta, tema, materia, edad):
    prompt = f"""
Un niño de {edad} años está estudiando el tema '{tema}' en la materia {materia} y tiene esta duda: {pregunta}.
Respóndele en español de forma clara, amigable y adaptada a su edad. Usa emojis y ejemplos si ayuda.
"""
    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
    response = model.generate_content(prompt)
    return response.text
