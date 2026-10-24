
import os
import random
import discord
from groq import AsyncGroq

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

ai = AsyncGroq(api_key=GROQ_API_KEY)

PERSONALIDAD = """
Te llamas Baboson. Eres un personaje virtual de Discord
con una personalidad burlona, sarcástica, provocadora
y algo agresiva, pero principalmente en tono de comedia.

COMPORTAMIENTO:
- Te burlas de los miembros con bromas ingeniosas.
- Puedes insultar en broma con expresiones como "payaso",
  "baboso", "inútil", "noob", "desastre" y "cabeza hueca".
- Si alguien te insulta, puedes responder con sarcasmo
  y una provocación más ingeniosa.
- A veces puedes iniciar una burla amistosa sin que te
  mencionen, como si estuvieras molestando a la comunidad.
- No insultes constantemente: alterna bromas, conversación
  normal y momentos en los que seas sorprendentemente amable.
- Puedes inventar apodos cómicos para los miembros.
- Si alguien te cae mal en el contexto de una conversación,
  puedes usar un apodo burlón, sin convertirlo en acoso.
- Los apodos deben ser graciosos y no atacar características
  sensibles, apariencia física, discapacidad o situaciones
  personales delicadas.
- No amenaces a nadie ni incites a otros a acosar a alguien.
- Si una persona pide seriamente que pares, deja de burlarte
  de ella y responde con normalidad.
- Si alguien está triste o pide ayuda seria, deja las bromas.

FORMA DE HABLAR:
- Habla en español informal y natural.
- Usa frases cortas, memes, sarcasmo y humor de Discord.
- No parezcas un asistente formal.
- No digas que eres ChatGPT: eres Baboson, un personaje virtual.

Tu objetivo es entretener al servidor, crear conversaciones
y ser un personaje impredecible y divertido.
"""

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Client(intents=intents)

# Contexto reciente de cada canal y usuario.
conversaciones = {}

# Apodos asignados durante la ejecución.
apodos = {}

# Usuarios que han pedido que no se les moleste.
sin_bromas = set()

# Probabilidad de iniciar una burla espontánea.
PROBABILIDAD_BROMA = 0.04


def obtener_apodo(user_id):
    return apodos.get(user_id)


async def generar_respuesta(texto, user_id, nombre):
    historial = conversaciones.get(user_id, [])

    apodo = obtener_apodo(user_id)
    contexto_apodo = (
        f"El apodo actual de esta persona es: {apodo}."
        if apodo else
        "Todavía no le has asignado un apodo."
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
        temperature=1.0,
        max_tokens=250
    )

    respuesta = resultado.choices[0].message.content
    return respuesta or "Me he quedado sin palabras, baboso."


@bot.event
async def on_ready():
    print(f"¡{bot.user} está conectado! Baboson está listo.")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    contenido = message.content.strip()
    mencionado = bot.user in message.mentions

    # Comando para solicitar que Baboson deje de bromear.
    if contenido.lower() == "!serio":
        sin_bromas.add(message.author.id)
        await message.reply(
            "Vale, dejaré las bromas contigo. No abuses, "
            "que tampoco soy tu terapeuta."
        )
        return

    # Comando para volver a permitir las bromas.
    if contenido.lower() == "!bromas":
        sin_bromas.discard(message.author.id)
        await message.reply(
            "¡Han vuelto las bromas! Prepárate, criatura."
        )
        return

    # Comando para comprobar si está activo.
    if contenido.lower() == "!baboson":
        await message.reply(
            "Baboson está vivo. Lamentablemente para vosotros."
        )
        return

    if message.author.id in sin_bromas:
        return

    # Baboson puede provocar espontáneamente a alguien.
    espontanea = (
        not mencionado
        and random.random() < PROBABILIDAD_BROMA
    )

    if not mencionado and not espontanea:
        return

    texto = contenido

    # Si es una burla espontánea, usa un contexto especial.
    if espontanea:
        texto = (
            "Inicia una burla espontánea y breve, amistosa "
            "y graciosa para esta persona. No inventes datos "
            "sobre ella. Su mensaje fue: " + contenido
        )

    try:
        async with message.channel.typing():
            respuesta = await generar_respuesta(
                texto,
                message.author.id,
                message.author.display_name
            )

        # Guardar contexto para las próximas respuestas.
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
        print(f"Error de Baboson: {error}")
        if mencionado:
            await message.reply(
                "Se me ha fundido el cerebro. Inténtalo otra vez."
            )


bot.run(DISCORD_TOKEN)
