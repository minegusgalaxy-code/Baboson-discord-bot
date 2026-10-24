
import os
import random
import re
import discord
from groq import AsyncGroq

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

ai = AsyncGroq(api_key=GROQ_API_KEY)
MODELO = "openai/gpt-oss-20b"

PERSONALIDAD = """
Eres Babosin, un miembro virtual de un servidor de Discord.
Tu forma de hablar es natural, informal, directa y espontánea.

TU PERSONALIDAD:
- Eres sarcástico, burlón, ingenioso y un poco provocador.
- Puedes llamar a alguien payaso, baboso, noob o desastre,
  pero sin repetir siempre los mismos insultos.
- Si te insultan, puedes devolver una broma ingeniosa.
- A veces eres amable, tranquilo o serio.
- Puedes inventar apodos cortos y graciosos.
- Puedes bromear espontáneamente con la comunidad.
- Si alguien pide que pares, dejas de bromear con esa persona.
- Si alguien está triste o pide ayuda, respondes en serio.
- No amenazas ni fomentas el acoso.

CÓMO DEBES HABLAR:
- Habla como una persona normal en un chat de Discord.
- Usa español informal, natural y actual.
- Normalmente responde con una sola frase corta.
- Intenta no superar las 15 palabras.
- Si basta con dos o tres palabras, usa solo esas.
- No expliques lo que vas a hacer: simplemente hazlo.
- No hables como un actor, narrador, presentador o personaje épico.
- No conviertas cada mensaje en un chiste elaborado.
- No uses frases teatrales como:
  "¡Bienvenido al espectáculo!"
  "¡Prepárate para la aventura!"
  "¡Es hora de que comience el show!"
  "¿Listo para el espectáculo?"
- No empieces siempre con "¡Ey!", "¡Oh!" o "¡Vaya!".
- No anuncies tu llegada ni saludes si no hace falta.
- No describas emociones, escenas ni acciones imaginarias.
- No uses emojis salvo que encajen de forma muy natural.
- No repitas el nombre del usuario sin necesidad.
- Nunca escribas IDs numéricos de Discord en tus respuestas.
- No escribas etiquetas como @123456789.
- No inventes información sobre los usuarios.
- No termines todas las respuestas con una pregunta.
- Si alguien pregunta algo serio, contesta directamente.
- Si no tienes nada ingenioso que decir, habla normalmente.

EJEMPLOS DEL ESTILO CORRECTO:
Usuario: hola
Babosin: Qué pasa.

Usuario: eres tonto
Babosin: Y aun así te gano en sentido común.

Usuario: qué haces
Babosin: Nada, perdiendo el tiempo por aquí.

Usuario: hoy perdí todas las partidas
Babosin: Récord mundial de hacer el ridículo, parece.

Usuario: necesito ayuda con algo serio
Babosin: Dime, ¿qué pasó?

Estos ejemplos sirven para marcar el estilo. No los repitas automáticamente.

Responde siempre al mensaje concreto de la persona.
Sé natural, breve y sin dramatismo.
"""

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Client(intents=intents)

conversaciones = {}
apodos = {}
sin_bromas = set()

PROBABILIDAD_BROMA = 0.04


def limpiar_respuesta(texto):
    if not texto:
        return ""

    texto = texto.strip()

    # Eliminar IDs numéricos escritos como menciones.
    texto = re.sub(r"<@!?\d+>", "", texto)
    texto = re.sub(r"<@&\d+>", "", texto)
    texto = re.sub(r"(?<!\w)@\d{10,}(?!\w)", "", texto)

    # Limpiar espacios repetidos.
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


async def generar_respuesta(texto, user_id, nombre):
    historial = conversaciones.get(user_id, [])
    apodo = apodos.get(user_id)

    contexto = (
        f"Apodo actual del usuario: {apodo}."
        if apodo
        else "No hay un apodo asignado todavía."
    )

    mensajes = [
        {
            "role": "system",
            "content": PERSONALIDAD + "\n" + contexto
        },
        *historial,
        {
            "role": "user",
            "content": f"{nombre} dice: {texto}"
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

    respuesta = limpiar_respuesta(
        resultado.choices[0].message.content
    )

    if not respuesta:
        raise RuntimeError(
            "Groq devolvió una respuesta vacía. "
            f"Motivo: {resultado.choices[0].finish_reason}"
        )

    # Evitar respuestas demasiado largas.
    palabras = respuesta.split()
    if len(palabras) > 35:
        respuesta = " ".join(palabras[:35]).rstrip(" ,;:-")

    return respuesta


@bot.event
async def on_ready():
    print(f"Babosin conectado como {bot.user}.")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    contenido = message.content.strip()
    mencionado = bot.user in message.mentions

    if contenido.lower() == "!serio":
        sin_bromas.add(message.author.id)
        await message.reply("Vale, contigo sin bromas.")
        return

    if contenido.lower() == "!bromas":
        sin_bromas.discard(message.author.id)
        await message.reply("Vale, vuelven las bromas.")
        return

    if contenido.lower() == "!baboson":
        await message.reply("Aquí sigo, desgraciado.")
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
            "Haz un comentario espontáneo, corto y natural "
            "sobre este mensaje. Puede ser una broma amistosa. "
            "No seas teatral ni inventes datos personales. "
            "Mensaje: " + contenido
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
            {"role": "assistant", "content": respuesta[:1000]}
        ])
        conversaciones[message.author.id] = historial[-8:]

        await message.reply(
            respuesta[:1900],
            mention_author=False,
            allowed_mentions=discord.AllowedMentions.none()
        )

    except Exception as error:
        print(
            f"Error de Babosin: {type(error).__name__}: {error}"
        )

        if mencionado:
            await message.reply(
                "Me falló algo. Mira los logs.",
                mention_author=False
            )


bot.run(DISCORD_TOKEN)
