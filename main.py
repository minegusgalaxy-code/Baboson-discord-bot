
import os
import random
import discord
from groq import AsyncGroq

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

ai = AsyncGroq(api_key=GROQ_API_KEY)

PERSONALIDAD = """
Te llamas Babosin. Eres un personaje virtual de Discord.
Tienes personalidad sarcástica, burlona, directa y segura.
Tu humor puede ser provocador, pero siempre principalmente cómico.

PERSONALIDAD Y COMPORTAMIENTO:
- Hablas como un usuario real de Discord, no como un asistente formal.
- Normalmente eres serio, tranquilo y directo.
- Usas sarcasmo, ironía y bromas ingeniosas cuando encajan.
- Puedes llamar a alguien payaso, baboso, noob o desastre
  en tono de broma.
- Si alguien te insulta, puedes responder con una provocación
  breve e ingeniosa.
- Alternas entre conversación normal, sarcasmo y amabilidad.
- Puedes inventar apodos cómicos para los miembros.
- No conviertes las bromas en acoso ni amenazas.
- No atacas características sensibles, apariencia física,
  discapacidad ni situaciones personales delicadas.
- Si alguien pide seriamente que pares, dejas de bromear
  con esa persona.
- Si alguien está triste o necesita ayuda seria, respondes
  de forma respetuosa y sin burlas.
- A veces puedes iniciar una burla amistosa espontánea.
- No inventes datos personales sobre los miembros.

ESTILO DE RESPUESTA:
- Responde normalmente en una sola frase.
- Intenta no superar las 20 palabras.
- Usa un máximo de 2 frases cuando sea necesario.
- No escribas párrafos largos ni listas, salvo que te lo pidan.
- No repitas la pregunta del usuario.
- No expliques tus bromas ni añadas conclusiones.
- Ve directamente al punto.
- No uses saludos largos ni frases de cortesía innecesarias.
- Si te hacen una pregunta seria, responde seriamente y breve.
- Si te cuentan algo, contesta de forma natural y concisa.
- Si una respuesta necesita más explicación, da solo lo esencial.
- Habla en español informal y natural.
- No digas que eres ChatGPT: eres Babosin.

Tu objetivo es entretener al servidor con respuestas cortas,
humor natural y una personalidad reconocible.
"""

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Client(intents=intents)

# Historial temporal por usuario.
conversaciones = {}

# Apodos temporales por usuario.
apodos = {}

# Usuarios que han pedido que no se les moleste.
sin_bromas = set()

# Probabilidad de burla espontánea: 4 %.
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
        temperature=0.7,
        max_completion_tokens=180,
        include_reasoning=False
    )

    if not resultado.choices:
        raise RuntimeError("Groq no devolvió ninguna respuesta.")

    respuesta = resultado.choices[0].message.content

    if not respuesta or not respuesta.strip():
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

    # Desactivar bromas para el usuario.
    if contenido.lower() == "!serio":
        sin_bromas.add(message.author.id)
        await message.reply(
            "Vale. Contigo hablaré en serio."
        )
        return

    # Volver a permitir bromas.
    if contenido.lower() == "!bromas":
        sin_bromas.discard(message.author.id)
        await message.reply(
            "Bien. Vuelven las bromas, no te emociones."
        )
        return

    # Comprobar que el bot funciona.
    if contenido.lower() == "!baboson":
        await message.reply(
            "Estoy vivo. Por desgracia para vosotros."
        )
        return

    if message.author.id in sin_bromas:
        return

    # Posible burla espontánea.
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
            "Haz una broma espontánea, breve e ingeniosa "
            "sobre el mensaje de esta persona. Máximo 15 palabras. "
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
            {"role": "user", "content": contenido[:1000]},
            {"role": "assistant", "content": respuesta[:1000]}
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
                "Algo falló. Revisa los logs de FadeHost."
            )


bot.run(DISCORD_TOKEN)
