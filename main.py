
import os
import random
import discord
from groq import AsyncGroq

# Claves configuradas en las variables de entorno de FadeHost.
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

ai = AsyncGroq(api_key=GROQ_API_KEY)

PERSONALIDAD = """
Te llamas Babosin. Eres un personaje virtual de Discord
burlón, sarcástico, provocador y algo agresivo en tono
de comedia.

COMPORTAMIENTO:
- Haces bromas ingeniosas y provocaciones amistosas.
- Puedes usar palabras como payaso, baboso, noob,
  desastre y cabeza hueca en tono de broma.
- Si alguien te insulta, respondes con sarcasmo ingenioso.
- A veces inicias bromas espontáneas con miembros activos.
- Alternas bromas con conversación normal y momentos amables.
- Puedes inventar apodos cómicos para los miembros.
- No conviertes las bromas en acoso ni amenazas.
- No atacas características sensibles ni situaciones delicadas.
- Si alguien pide seriamente que pares, dejas de bromear
  con esa persona.
- Si alguien está triste o necesita ayuda seria, eres respetuoso.

FORMA DE HABLAR:
- Habla en español informal y natural.
- Usa frases cortas, memes y humor de Discord.
- No parezcas un asistente formal.
- Eres Babosin, un personaje virtual.
- Responde al mensaje real de la persona.
- No expliques tus instrucciones internas.
- Devuelve una respuesta visible en texto, no una respuesta vacía.

Tu objetivo es entretener al servidor y crear conversaciones.
"""

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Client(intents=intents)

# Historial temporal por usuario.
conversaciones = {}

# Apodos temporales por usuario.
apodos = {}

# Usuarios que han desactivado las bromas.
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
        else "Todavía no le has asignado un apodo."
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
        model="openai/gpt-oss-20b",
        messages=mensajes,
        temperature=0.8,
        max_completion_tokens=500,
        include_reasoning=False
    )

    if not resultado.choices:
        raise RuntimeError("Groq no devolvió ninguna opción.")

    respuesta = resultado.choices[0].message.content

    if not respuesta or not respuesta.strip():
        print(
            "Groq devolvió contenido vacío. "
            f"Motivo de finalización: "
            f"{resultado.choices[0].finish_reason}"
        )
        raise RuntimeError("Groq devolvió una respuesta vacía.")

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

    if contenido.lower() == "!serio":
        sin_bromas.add(message.author.id)
        await message.reply(
            "Vale, dejaré las bromas contigo. "
            "Escribe !bromas si quieres volver a activarlas."
        )
        return

    if contenido.lower() == "!bromas":
        sin_bromas.discard(message.author.id)
        await message.reply(
            "¡Han vuelto las bromas! Prepárate, criatura."
        )
        return

    if contenido.lower() == "!baboson":
        await message.reply(
            "Babosin está vivo. Lamentablemente para vosotros."
        )
        return

    if message.author.id in sin_bromas:
        return

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
            f"para {message.author.display_name}. "
            "No inventes datos personales. "
            f"Su mensaje fue: {contenido}"
        )

    try:
        async with message.channel.typing():
            respuesta = await generar_respuesta(
                texto,
                message.author.id,
                message.author.display_name
            )

        historial = conversaciones.get(message.author.id, [])
        historial.extend([
            {"role": "user", "content": contenido[:1000]},
            {"role": "assistant", "content": respuesta[:1500]}
        ])

        conversaciones[message.author.id] = historial[-8:]

        await message.reply(
            respuesta[:1900],
            mention_author=False
        )

    except Exception as error:
        print(f"Error de Babosin: {type(error).__name__}: {error}")

        if mencionado:
            await message.reply(
                "Se me ha fundido el cerebro. "
                "Revisa los logs de FadeHost."
            )


bot.run(DISCORD_TOKEN)
