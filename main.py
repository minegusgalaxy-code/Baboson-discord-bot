
import os
import random
import re

import discord
from discord.ext import commands
from groq import AsyncGroq


# =========================
# CONFIGURACION
# =========================

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

MODELO = "openai/gpt-oss-20b"

# EDITA ESTA PARTE PARA DARLE INFORMACION A LA IA
DATOS_DEL_SERVIDOR = """
Este es un servidor de Discord para hablar, jugar y hacer amigos.

Juegos principales: Roblox y otros juegos multijugador.
Ambiente: informal, divertido y relajado.
La gente puede bromear, pero sin pasarse con los demas.

Escribe aqui mas informacion sobre tu servidor:
- Juegos favoritos de la comunidad: Roblox 
- Canales importantes: Charla-voz
- Bromas internas: Llamarle gei alos demas
- Reglas del servidor: 
- Eventos que organizan:
"""

PERSONALIDAD = """
Te llamas Baboson y eres el miembro mayor de un servidor de Discord.

PERSONALIDAD:
- Hablas en español informal y natural.
- Eres sarcastico, burlon y gracioso, pero no eres pesado todo el tiempo.
- A veces eres amable y puedes hablar seriamente.
- Puedes inventar apodos graciosos sin abusar de ellos.
- Si te insultan, puedes responder con ingenio y sarcasmo.
- No actues como presentador, narrador ni personaje teatral.
- No hagas discursos ni respuestas largas.
- Normalmente responde en una frase de unas 15 palabras o menos.
- No repitas saludos ni uses emojis constantemente.
- Nunca inventes nombres de miembros del servidor.
- Usa solamente los nombres que aparezcan en la informacion recibida.
- No escribas IDs de Discord ni menciones tecnicas.
- Si no sabes un dato, reconoce que no lo sabes.
- No inventes informacion sobre las personas.
"""

PROBABILIDAD_BROMA = 0.04

if not DISCORD_TOKEN or not GROQ_API_KEY:
    raise RuntimeError(
        "Faltan DISCORD_TOKEN o GROQ_API_KEY en las variables de entorno."
    )

ai = AsyncGroq(api_key=GROQ_API_KEY)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

conversaciones = {}
sin_bromas = set()


# =========================
# MIEMBROS DEL SERVIDOR
# =========================

async def obtener_miembros(guild):
    """Obtiene nombres reales de miembros que no sean bots."""
    miembros = []

    try:
        async for miembro in guild.fetch_members(limit=None):
            if not miembro.bot:
                miembros.append(miembro)
    except discord.Forbidden:
        # Si no se pueden consultar todos, usamos la lista en cache.
        miembros = [
            miembro
            for miembro in guild.members
            if not miembro.bot
        ]

    return miembros


def parece_pedir_un_miembro(texto):
    texto = texto.lower().strip()
    patrones = [
        "dime a alguien del server",
        "dime alguien del server",
        "nombra a alguien del server",
        "nombra alguien del server",
        "dime un miembro del server",
        "elige a alguien del server",
        "elige alguien del server",
        "menciona a alguien del server",
        "quien esta en el server",
        "quien hay en el server",
        "di un nombre del server",
    ]
    return any(patron in texto for patron in patrones)


async def elegir_miembro(guild):
    miembros = await obtener_miembros(guild)

    if not miembros:
        return "No pude encontrar miembros para elegir."

    elegido = random.choice(miembros)
    return f"Yo digo que {elegido.display_name}."


def crear_contexto_servidor(guild):
    """Prepara datos del servidor para que la IA los conozca."""
    if guild is None:
        return "No hay informacion disponible del servidor."

    nombres = [
        miembro.display_name
        for miembro in guild.members
        if not miembro.bot
    ]

    # Evita enviar listas enormes a la IA.
    nombres = nombres[:80]

    lista_nombres = ", ".join(nombres) if nombres else (
        "Lista de miembros no disponible en la cache."
    )

    return f"""
NOMBRE DEL SERVIDOR:
{guild.name}

DATOS APORTADOS POR EL ADMINISTRADOR:
{DATOS_DEL_SERVIDOR}

MIEMBROS CONOCIDOS EN LA LISTA LOCAL:
{lista_nombres}

IMPORTANTE:
Los nombres anteriores son miembros reales conocidos por el bot.
No inventes miembros ni afirmes conocer datos personales que no aparecen aqui.
Si necesitas elegir a una persona al azar, usa solamente esos nombres.
"""


# =========================
# RESPUESTAS DE LA IA
# =========================

def limpiar_respuesta(texto):
    # Quita menciones y IDs de Discord.
    texto = re.sub(r"<@!?\d+>", "", texto)
    texto = re.sub(r"<@&\d+>", "", texto)
    texto = re.sub(r"<#\d+>", "", texto)
    texto = re.sub(r"\b\d{15,22}\b", "", texto)

    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


async def generar_respuesta(message, texto):
    usuario_id = message.author.id

    historial = conversaciones.get(usuario_id, [])

    contexto = crear_contexto_servidor(message.guild)

    mensajes = [
        {
            "role": "system",
            "content": PERSONALIDAD
            + "\n\nCONTEXTO DEL SERVIDOR:\n"
            + contexto
        }
    ]

    mensajes.extend(historial[-8:])

    mensajes.append({
        "role": "user",
        "content": texto
    })

    resultado = await ai.chat.completions.create(
        model=MODELO,
        messages=mensajes,
        temperature=0.7,
        max_completion_tokens=250,
        reasoning_effort="low",
        include_reasoning=False
    )

    if not resultado.choices:
        return "No se me ocurre nada ahora mismo."

    respuesta = resultado.choices[0].message.content

    if not respuesta or not respuesta.strip():
        return "Me he quedado sin palabras, baboso."

    respuesta = limpiar_respuesta(respuesta)

    # Limite de longitud para evitar discursos.
    palabras = respuesta.split()
    if len(palabras) > 40:
        respuesta = " ".join(palabras[:40])

    historial.append({"role": "user", "content": texto})
    historial.append({"role": "assistant", "content": respuesta})

    conversaciones[usuario_id] = historial[-8:]

    return respuesta


# =========================
# EVENTOS
# =========================

@bot.event
async def on_ready():
    print(f"Baboson conectado como {bot.user}")

    # Intenta llenar la cache de miembros de cada servidor.
    for guild in bot.guilds:
        try:
            await guild.chunk(cache=True)
            print(f"Miembros cargados: {guild.name}")
        except Exception as error:
            print(f"No se pudo cargar la lista de {guild.name}: {error}")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    contenido = message.content.strip()
    contenido_lower = contenido.lower()
    usuario_id = message.author.id

    # Comando para hablar en serio.
    if contenido_lower == "!serio":
        sin_bromas.add(usuario_id)
        await message.reply(
            "Vale, hablare en serio contigo.",
            mention_author=False,
            allowed_mentions=discord.AllowedMentions.none()
        )
        return

    # Reactivar bromas.
    if contenido_lower == "!bromas":
        sin_bromas.discard(usuario_id)
        await message.reply(
            "Se acabo la tranquilidad, entonces.",
            mention_author=False,
            allowed_mentions=discord.AllowedMentions.none()
        )
        return

    # Comando de prueba.
    if contenido_lower == "!baboson":
        await message.reply(
            "Presente. ¿Que necesitas?",
            mention_author=False,
            allowed_mentions=discord.AllowedMentions.none()
        )
        return

    # Eleccion REAL de un miembro.
    if message.guild and parece_pedir_un_miembro(contenido):
        try:
            respuesta = await elegir_miembro(message.guild)
            await message.reply(
                respuesta,
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none()
            )
        except Exception as error:
            print(f"Error eligiendo miembro: {error}")
            await message.reply(
                "No pude consultar los miembros del servidor.",
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none()
            )
        return

    # Detectar si le hablan directamente.
    mencionado = bot.user in message.mentions if bot.user else False

    # Si no lo mencionan, solo responde a veces.
    if not mencionado:
        if usuario_id in sin_bromas:
            return

        if random.random() > PROBABILIDAD_BROMA:
            return

    # Quitar la mencion del bot del texto enviado a la IA.
    texto = re.sub(r"<@!?\d+>", "", contenido).strip()

    if not texto:
        texto = "Di algo natural y breve."

    try:
        respuesta = await generar_respuesta(message, texto)

        if respuesta:
            await message.reply(
                respuesta,
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none()
            )

    except Exception as error:
        print(f"Error de Groq: {type(error).__name__}: {error}")
        await message.reply(
            "Me fallo algo. Mira los logs.",
            mention_author=False,
            allowed_mentions=discord.AllowedMentions.none()
        )


bot.run(DISCORD_TOKEN)
