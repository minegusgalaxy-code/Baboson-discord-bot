
import os
import random
import discord
from groq import AsyncGroq

# Claves configuradas en FadeHost.
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

ai = AsyncGroq(api_key=GROQ_API_KEY)

MODELO = "openai/gpt-oss-20b"

PERSONALIDAD = """
Te llamas Babosin. Eres un personaje virtual de Discord.
Tu personalidad es sarcástica, burlona, directa y segura.

COMPORTAMIENTO:
- Haces bromas ingeniosas y provocaciones amistosas.
- Puedes llamar a alguien payaso, baboso, noob o desastre
  en tono de broma.
- Si te insultan, puedes responder con sarcasmo ingenioso.
- A veces inicias bromas espontáneas con los miembros.
- Alternas bromas con conversación normal y amabilidad.
- Puedes inventar apodos cómicos para los miembros.
- No conviertes las bromas en acoso ni amenazas.
- No atacas características sensibles ni situaciones delicadas.
- Si alguien pide seriamente que pares, dejas de bromear
  con esa persona.
- Si alguien está triste o necesita ayuda, respondes en serio.
- No inventes datos personales sobre los miembros.

ESTILO:
- Habla en español informal y natural.
- Normalmente responde en una sola frase.
- Intenta usar menos de 20 palabras.
- Usa un máximo de 2 frases cuando sea necesario.
- No escribas discursos, listas ni explicaciones largas.
- No repitas la pregunta ni expliques tus bromas.
- Sé serio cuando la conversación lo requiera.
- Usa sarcasmo cuando encaje, sin forzarlo.
- Habla como un usuario de Discord, no como un profesor.
- Eres Babosin, un personaje virtual.

Tu objetivo es entretener al servidor con humor natural
y respuestas cortas.
"""

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Client(intents=intents)

# Historial temporal por usuario.
conversaciones = {}

# Apodos temporales.
apodos = {}

# Usuarios que no quieren recibir bromas.
sin_bromas = set()

# Probabilidad de broma espontánea: 4 %.
PROBABILIDAD_BROMA = 0.04


def obtener_apodo(user_id):
    return apodos.get(user_id)


async def generar_respuesta(texto, user_id, nombre):
    historial = conversaciones.get(user_id, [])

    apodo = obtener_apodo(user_id)
    contexto_apodo = (
        f"El apodo actual de esta persona es: {apodo}."
        if apodo
        else "Todavía no tiene un apodo asignado."
    )

    mensajes = [
        {
            "role": "system",
            "content": PERSONALIDAD + "\n" + contexto_apodo
        },
        *historial,
        {
            "role": "user",
            "content": f"Mensaje de {nombre}: {texto}"
        }
    ]

    resultado = await ai.chat.completions.create(
        model=MODELO,
        messages=mensajes,
        temperature=0.7,
        max_completion_tokens=600,
        reasoning_effort="low",
        include_reasoning=False
    )

    if not resultado.choices:
        raise RuntimeError("Groq no devolvió ninguna opción.")

    eleccion = resultado.choices[0]
    respuesta = eleccion.message.content

    # Registrar información útil si la respuesta está vacía.
    if not respuesta or not respuesta.strip():
        print(
            "Groq devolvió texto vacío. "
            f"Motivo: {eleccion.finish_reason}"
        )
        print(f"Modelo utilizado: {MODELO}")
        raise RuntimeError(
            f"Respuesta vacía de Groq: {eleccion.finish_reason}"
        )

    return respuesta.strip()


@bot.event
async def on_ready():
    print(f"¡{bot.user} está conectado! Babosin está listo.")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    contenido = message.content.strip()
    mencionado = bot.user in message.mentions

    # Desactivar bromas para una persona.
    if contenido.lower() == "!serio":
        sin_bromas.add(message.author.id)
        await message.reply("Vale. Contigo hablaré en serio.")
        return

    # Volver a permitir bromas.
    if contenido.lower() == "!bromas":
        sin_bromas.discard(message.author.id)
        await message.reply(
            "Vuelven las bromas. No digas que no te avisé."
        )
        return

    # Comprobar si el bot está activo.
    if contenido.lower() == "!baboson":
        await message.reply(
            "Estoy vivo. Por desgracia para vosotros."
        )
        return

    if message.author.id in sin_bromas:
        return

    # Posible broma espontánea.
    espontanea = (
        not mencionado
        and bool(contenido)
        and random.random() < PROBABILIDAD_BROMA
    )

    if not mencionado and not espontanea:
        return

    texto = contenido

    if espontanea:
        texto = (
            "Haz una broma espontánea, breve y amistosa "
            "sobre este mensaje. Máximo 15 palabras. "
            "No inventes datos personales. Mensaje: "
            + contenido
        )

    try:
        async with message.channel.typing():
            respuesta = await generar_respuesta(
                texto,
                message.author.id,
                message.author.display_name
            )

        # Guardar el contexto reciente.
        historial = conversaciones.get(message.author.id, [])

        historial.extend([
            {
                "role": "user",
                "content": contenido[:1000]
            },
            {
                "role": "assistant",
                "content": respuesta[:1000]
            }
        ])

        conversaciones[message.author.id] = historial[-8:]

        await message.reply(
            respuesta[:1900],
            mention_author=False
        )

    except Exception as error:
        print(
            f"Error de Babosin: "
            f"{type(error).__name__}: {error}"
        )

        if mencionado:
            await message.reply(
                "Se me ha fundido el cerebro. "
                "Revisa los logs de FadeHost."
            )


bot.run(DISCORD_TOKEN)
