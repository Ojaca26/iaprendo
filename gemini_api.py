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
    prompt_base = f"""
Crea 7 preguntas tipo test sobre el tema '{tema}' de la materia {materia} para un niño de {edad} años.
Cada pregunta debe tener 3 opciones (a, b, c). Marca la correcta agregando un asterisco (*) después de la opción correcta.
Ejemplo de respuesta esperada en JSON:
[
  {{"pregunta": "¿Qué planeta es conocido como el planeta rojo?", "opciones": ["a) Marte*", "b) Venus", "c) Júpiter"]}},
  {{"pregunta": "¿Cuál es el hueso más largo del cuerpo humano?", "opciones": ["a) Cráneo", "b) Fémur*", "c) Tibia"]}}
]
No expliques nada, solo devuelve el JSON.
"""

    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")

    for intento in range(3):  # Hasta 3 intentos
        try:
            response = model.generate_content(prompt_base)
            texto = response.text.strip()

            # 💥 Limpiar si viene dentro de ``` bloques
            if "```" in texto:
                partes = texto.split("```")
                texto = "".join(p for p in partes if not p.strip().startswith("json") and not p.strip().startswith("python")).strip()

            preguntas_json = json.loads(texto)

            # Validar estructura
            if isinstance(preguntas_json, list) and all("pregunta" in p and "opciones" in p for p in preguntas_json):
                preguntas = []
                opciones = []
                for p in preguntas_json:
                    preguntas.append(p["pregunta"])
                    opciones.append(p["opciones"])
                return preguntas, opciones
            else:
                raise ValueError("Formato JSON no válido")

        except Exception as e:
            print(f"⚠️ Intento {intento+1} fallido: {e}\nRespuesta recibida:\n{texto}")

    # Si después de 3 intentos no logró generar, devolvemos vacío
    return [], []

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
