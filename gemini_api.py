# gemini_api.py
import google.generativeai as genai
import json
import streamlit as st
import re

# Configurar API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def explicar_tema(materia, tema, edad):
    prompt = f"""
Explica de forma clara, amigable y en español para un niño de {edad} años el tema: '{tema}'
en la materia de {materia}. Usa ejemplos sencillos, emojis y termina haciendo sugerencias
para niños sobre el tema.
"""
    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
    response = model.generate_content(prompt)
    return response.text.strip()

def generar_preguntas(materia, tema, edad):
    prompt = f"""
Crea 7 preguntas tipo test sobre el tema '{tema}' de la materia {materia} para un niño de {edad} años.
Cada pregunta debe tener 3 opciones (a, b, c). La opción correcta debe ir marcada con un asterisco (*).
Devuélvelo en un JSON válido como lista de objetos:
[
  {{"pregunta": "¿...?"," "opciones": ["a) ...", "b) ...", "c) ..."], "respuesta_correcta": "a"}}
]
No expliques nada más, solo el JSON.
"""
    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
    response = model.generate_content(prompt)

    texto = response.text.strip()

    # Limpiar si viene dentro de ```
    if texto.startswith("```"):
        partes = texto.split("```")
        texto = "".join(p for p in partes if not p.strip().startswith("json") and not p.strip().startswith("python")).strip()

    try:
        # Buscar solo el primer JSON dentro del texto
        match = re.search(r"\[\s*{.*?}\s*\]", texto, re.DOTALL)
        if match:
            json_text = match.group()
            preguntas_json = json.loads(json_text)
        else:
            preguntas_json = []
            print(f"⚠️ No se encontró un JSON válido en la respuesta:\n{texto}")
    except Exception as e:
        preguntas_json = []
        print(f"⚠️ Error cargando preguntas JSON: {e}\nContenido recibido:\n{texto}")

    preguntas = []
    opciones = []

    for p in preguntas_json:
        preguntas.append(p["pregunta"])
        opciones.append(p["opciones"])

    return preguntas, opciones

def evaluar_respuestas(preguntas, respuestas, tema, materia, edad):
    prompt = f"""
Evalúa las respuestas de un niño de {edad} años sobre el tema '{tema}' en {materia}.
Para cada pregunta indica si está bien (✅) o mal (❌) y da una retroalimentación breve y motivadora.
Aquí están las respuestas:
"""
    for i, (pregunta, respuesta) in enumerate(zip(preguntas, respuestas)):
        prompt += f"\nPregunta {i+1}: {pregunta}\nRespuesta del niño: {respuesta}"

    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
    response = model.generate_content(prompt)
    return response.text.strip()

def responder_duda(pregunta, tema, materia, edad):
    prompt = f"""
Un niño de {edad} años tiene esta duda sobre el tema '{tema}' en {materia}: {pregunta}.
Respóndele de forma clara, amigable y adaptada a su edad en español.
"""
    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
    response = model.generate_content(prompt)
    return response.text.strip()
