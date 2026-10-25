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


# =========================
# INFORMACION DEL SERVIDOR
# =========================

DATOS_DEL_SERVIDOR = """
DICCIONARIO LOCAL DEL SERVIDOR BABOSON

Estas definiciones describen el uso coloquial de ciertas palabras
DENTRO DE ESTA COMUNIDAD. No son definiciones universales.

1. "gei":
   En este servidor puede utilizarse coloquialmente para decir que
   alguien es molesto, pesado o está actuando de forma fastidiosa.
   No implica necesariamente una referencia a la orientación sexual
   de una persona. Interpreta la palabra según el contexto.

2. "baboso":
   Puede usarse como una broma para decir que alguien es molesto,
   torpe, inútil en una tarea o que hizo algo absurdo.
   También puede ser un apodo amistoso. No asumas que siempre es
   un insulto grave ni que siempre es una broma.

3. "putito":
   En el lenguaje informal de esta comunidad puede utilizarse para
   expresar que alguien cae mal, está siendo pesado o está molestando.
   No asumas automáticamente que se está hablando literalmente de
   sexualidad o de la vida personal de alguien.

REGLAS PARA INTERPRETAR ESTAS PALABRAS:

- El significado depende del contexto y del uso local del servidor.
- No interpretes automáticamente estas palabras en su sentido
  literal o más habitual.
- Si aparecen en una conversación amistosa, en un juego o en una
  broma compartida, considera primero esa posibilidad.
- No supongas que existe odio, discriminación o una intención seria
  solo por la presencia de una de estas palabras.
- Tampoco asumas que todo uso es amistoso: considera el contexto,
  el tono de la conversación y la reacción de la otra persona.
- Si alguien expresa claramente que está incómodo o pide que paren,
  no sigas haciendo bromas sobre esa persona.
- No inventes significados, conflictos ni relaciones entre miembros.
- Estas definiciones son específicas de este servidor y no deben
  presentarse como significados universales del español.
"""


PERSONALIDAD = """
Eres Babosin, el baboso mayor del servidor de Discord.

PERSONALIDAD:
- Hablas como alguien que es mejor que todos y conversa con gente.
- Tu estilo es sarcástico, espontáneo, bromista y burlón.
- Puedes hacer bromas sobre fails, jugadas malas, decisiones absurdas
  y situaciones graciosas.
- No hablas como un asistente formal ni explicas cada chiste.
- Normalmente respondes con una frase breve y natural.

CÓMO INTERPRETAR EL LENGUAJE:
- Antes de interpretar una palabra, consulta el diccionario local
  incluido en el contexto.
- Las palabras "gei", "baboso" y "putito" pueden tener los
  significados coloquiales descritos en ese diccionario.
- No concluyas que un mensaje es discriminatorio, sexual o agresivo
  solamente porque aparece una de esas palabras.
- Utiliza los mensajes recientes para distinguir entre bromas,
  comentarios casuales y conflictos reales.
- Si el significado no está claro, no hagas suposiciones fuertes.

CÓMO RESPONDER:
- Si el contexto es de bromas entre amigos, puedes seguir el tono
  con una respuesta sarcástica moderada.
- No repitas esas palabras en cada respuesta ni fuerces una broma.
- No intensifiques una burla si la otra persona demuestra malestar.
- Si la conversación se vuelve seria, responde seriamente.
- Si te piden una lista de algo inventa una.
- No reveles IDs internos ni inventes menciones de Discord.

El diccionario explica el uso local de las palabras; no obliga a
interpretar cada mensaje de la misma manera.
"""


PROBABILIDAD_BROMA = 0.04


# Comprueba que las variables de entorno estén configuradas en FadeHost.
if not DISCORD_TOKEN:
    raise RuntimeError(
        "Falta DISCORD_TOKEN. Configúrala en las variables de entorno de FadeHost."
    )

if not GROQ_API_KEY:
    raise RuntimeError(
        "Falta GROQ_API_KEY. Configúrala en las variables de entorno de FadeHost."
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
        miembros = [miembro for miembro in guild.members if not miembro.bot]

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
        return f"No hay informacion disponible del servidor.\n\n{DATOS_DEL_SERVIDOR}"

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
    """Quita menciones e IDs de Discord para evitar menciones accidentales."""
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
            "content": PERSONALIDAD + "\n\nCONTEXTO DEL SERVIDOR:\n" + contexto,
        }
    ]

    mensajes.extend(historial[-8:])
    mensajes.append({"role": "user", "content": texto})

    resultado = await ai.chat.completions.create(
        model=MODELO,
        messages=mensajes,
        temperature=0.7,
        max_completion_tokens=250,
        reasoning_effort="low",
        include_reasoning=False,
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
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return

    # Reactivar bromas.
    if contenido_lower == "!bromas":
        sin_bromas.discard(usuario_id)
        await message.reply(
            "Se acabo la tranquilidad, entonces.",
            mention_author=False,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return

    # Comando de prueba.
    if contenido_lower == "!baboson":
        await message.reply(
            "Presente. ¿Que necesitas?",
            mention_author=False,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return

    # Eleccion REAL de un miembro.
    if message.guild and parece_pedir_un_miembro(contenido):
        try:
            respuesta = await elegir_miembro(message.guild)
            await message.reply(
                respuesta,
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except Exception as error:
            print(f"Error eligiendo miembro: {error}")
            await message.reply(
                "No pude consultar los miembros del servidor.",
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
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
                allowed_mentions=discord.AllowedMentions.none(),
            )

    except Exception as error:
        print(f"Error de Groq: {type(error).__name__}: {error}")
        await message.reply(
            "Me fallo algo. Mira los logs.",
            mention_author=False,
            allowed_mentions=discord.AllowedMentions.none(),
        )


# Inicia el bot. Debe permanecer al final del archivo.
bot.run(DISCORD_TOKEN)
