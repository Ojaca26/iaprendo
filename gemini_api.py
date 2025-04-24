# gemini_api.py
import google.generativeai as genai

genai.configure(api_key="AIzaSyBvzG0m2tILEkX-4D0uwjJjo3qTLrWg1Vs")

def explicar_tema(materia, tema, edad):
    prompt = f"""
    Explica de forma clara y didáctica para un niño de {edad} años el tema: '{tema}'
    en la materia de {materia}. Usa ejemplos fáciles, emojis, y termina sugiriendo
    una imagen representativa para niños sobre el tema.
    """
    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
    response = model.generate_content(prompt)
    texto = response.text

    imagen_url = None  # Se omite generación de imagen por modelo deprecado

    return texto, imagen_url

def generar_preguntas(materia, tema, edad):
    prompt = f"Crea 3 preguntas fáciles y divertidas para un niño de {edad} años sobre el tema '{tema}' en la materia {materia}."
    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
    response = model.generate_content(prompt)
    return [p.strip() for p in response.text.split("\n") if p.strip()]

def evaluar_respuesta(preguntas, respuestas, tema, materia, edad):
    prompt = f"""
    Evalúa las respuestas de un niño de {edad} años al tema '{tema}' en {materia}.
    Especifica si respondió bien o no y crea un breve plan de refuerzo si se detectan errores.
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
    Un niño de {edad} años tiene una duda sobre el tema '{tema}' en la materia {materia}.
    La pregunta es: "{pregunta}".
    Respóndele de forma clara, amigable y adaptada para su edad, usando ejemplos o emojis si es posible.
    """
    model = genai.GenerativeModel(model_name="models/gemini-2.5-pro-preview-03-25")
    response = model.generate_content(prompt)
    return response.text
