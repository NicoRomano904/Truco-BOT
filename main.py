import discord
from discord.ext import commands
from discord.ui import Button, View
import random
import os
import webserver

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Bot listo")

games = {}

# ===== RANK =====
def get_rank(c):
    v = c["valor"]
    p = c.get("palo")

    if v == 1 and p == "espada": return 14
    if v == 1 and p == "basto": return 13
    if v == 7 and p == "espada": return 12
    if v == 7 and p == "oro": return 11
    if v == 3: return 10
    if v == 2: return 9
    if v == 1: return 8
    if v == 12: return 7
    if v == 11: return 6
    if v == 10: return 5
    if v == 7: return 4
    if v == 6: return 3
    if v == 5: return 2
    if v == 4: return 1

# ===== MAZO =====
cartas = [
    {"valor":1,"palo":"espada","emoji":"1🗡️"},
    {"valor":1,"palo":"basto","emoji":"1🌿"},
    {"valor":1,"palo":"copa","emoji":"1🍷"},
    {"valor":1,"palo":"oro","emoji":"1☀️"},
    {"valor":2,"palo":"espada","emoji":"2🗡️"},
    {"valor":2,"palo":"basto","emoji":"2🌿"},
    {"valor":2,"palo":"copa","emoji":"2🍷"},
    {"valor":2,"palo":"oro","emoji":"2☀️"},
    {"valor":3,"palo":"espada","emoji":"3🗡️"},
    {"valor":3,"palo":"basto","emoji":"3🌿"},
    {"valor":3,"palo":"copa","emoji":"3🍷"},
    {"valor":3,"palo":"oro","emoji":"3☀️"},
    {"valor":4,"palo":"espada","emoji":"4🗡️"},
    {"valor":4,"palo":"basto","emoji":"4🌿"},
    {"valor":4,"palo":"copa","emoji":"4🍷"},
    {"valor":4,"palo":"oro","emoji":"4☀️"},
    {"valor":5,"palo":"espada","emoji":"5🗡️"},
    {"valor":5,"palo":"basto","emoji":"5🌿"},
    {"valor":5,"palo":"copa","emoji":"5🍷"},
    {"valor":5,"palo":"oro","emoji":"5☀️"},
    {"valor":6,"palo":"espada","emoji":"6🗡️"},
    {"valor":6,"palo":"basto","emoji":"6🌿"},
    {"valor":6,"palo":"copa","emoji":"6🍷"},
    {"valor":6,"palo":"oro","emoji":"6☀️"},
    {"valor":7,"palo":"espada","emoji":"7🗡️"},
    {"valor":7,"palo":"basto","emoji":"7🌿"},
    {"valor":7,"palo":"copa","emoji":"7🍷"},
    {"valor":7,"palo":"oro","emoji":"7☀️"},
    {"valor":10,"palo":"espada","emoji":"10🗡️"},
    {"valor":10,"palo":"basto","emoji":"10🌿"},
    {"valor":10,"palo":"copa","emoji":"10🍷"},
    {"valor":10,"palo":"oro","emoji":"10☀️"},
    {"valor":11,"palo":"espada","emoji":"11🗡️"},
    {"valor":11,"palo":"basto","emoji":"11🌿"},
    {"valor":11,"palo":"copa","emoji":"11🍷"},
    {"valor":11,"palo":"oro","emoji":"11☀️"},
    {"valor":12,"palo":"espada","emoji":"12🗡️"},
    {"valor":12,"palo":"basto","emoji":"12🌿"},
    {"valor":12,"palo":"copa","emoji":"12🍷"},
    {"valor":12,"palo":"oro","emoji":"12☀️"}
]

# ===== GAME =====
class TrucoGame:
    def __init__(self, creador, max_points=15):
        self.jugadores = [creador]
        self.manos = {}
        self.mazo = cartas.copy()
        random.shuffle(self.mazo)
        self.manos[creador] = [self.mazo.pop() for _ in range(3)]
        # turno and mano are indexes into self.jugadores (0 or 1)
        self.turno = 0
        self.mano = 0  # index of who is 'mano' for this round
        self.mesa = []
        self.rondas = {}
        self.puntos = {}
        self.truco_valor = 1
        # Truco state: "normal" (no canto), "truco", "retruco", "vale4"
        self.truco_estado = "normal"
        # Envido state: None, "envido", "doble", "real", "falta"
        self.envido_state = None
        self.envido_valor = 0
        # envido_history holds tuples (type, value) e.g. ('envido',2), ('real',3), ('falta',n)
        self.envido_history = []
        # control pending responses
        self.esperando_respuesta = False
        # tipo_espera: None | 'truco' | 'envido'
        self.tipo_espera = None
        # quien_responde is user id of the player who must respond
        self.quien_responde = None
        self.ganadores_manos = []
        self.manos_ganadas = {}
        self.max_points = max_points
        self.estado = "normal"
        self.envido_cantado = False
        # Truco tracking: who last cantó and who currently has right to subir
        self.truco_cantado_por = None
        self.truco_turno_subida = None
        # flag indicating a previously cantado truco was accepted
        self.truco_aceptado = False

    def agregar_jugador(self, j):
        self.jugadores.append(j)
        self.manos[j] = [self.mazo.pop() for _ in range(3)]
        self.manos_ganadas = {self.jugadores[0]:0, self.jugadores[1]:0}
        self.puntos = {self.jugadores[0]:0, self.jugadores[1]:0}

    def repartir(self):
        self.mazo = cartas.copy()
        random.shuffle(self.mazo)
        for j in self.jugadores:
            self.manos[j] = [self.mazo.pop() for _ in range(3)]
        self.mesa = []
        self.manos_ganadas = {j:0 for j in self.jugadores}
        self.ganadores_manos = []
        self.truco_valor = 1
        self.truco_estado = "normal"
        self.esperando_respuesta = False
        self.tipo_espera = None
        self.quien_responde = None
        self.estado = "normal"
        self.envido_cantado = False
        self.envido_state = None
        self.envido_valor = 0
        self.envido_history = []
        self.turno = self.mano
        self.truco_cantado_por = None
        self.truco_turno_subida = None
        self.truco_aceptado = False

    # --- helper utilities ---
    def other(self, user):
        return self.jugadores[(self.jugadores.index(user)+1)%2]

    def index_of(self, user):
        return self.jugadores.index(user)

    def mano_id(self):
        return self.jugadores[self.mano]

    def pie_id(self):
        return self.other(self.mano_id())

    def build_envido_view(self, responder_id):
        view = View()
        view.add_item(Button(label="Quiero", custom_id="quiero_envido"))
        view.add_item(Button(label="No quiero", custom_id="no_envido"))
        state = self.envido_state
        if state is None:
            view.add_item(Button(label="Envido", custom_id="envido_doble"))
            view.add_item(Button(label="Real Envido", custom_id="real_envido"))
            view.add_item(Button(label="Falta Envido", custom_id="falta_envido"))
        elif state == "envido":
            view.add_item(Button(label="Envido", custom_id="envido_doble"))
            view.add_item(Button(label="Real Envido", custom_id="real_envido"))
            view.add_item(Button(label="Falta Envido", custom_id="falta_envido"))
        elif state == "doble":
            view.add_item(Button(label="Real Envido", custom_id="real_envido"))
            view.add_item(Button(label="Falta Envido", custom_id="falta_envido"))
        elif state == "real":
            view.add_item(Button(label="Falta Envido", custom_id="falta_envido"))
        return view

    def build_truco_view(self, responder_id):
        view = View()
        view.add_item(Button(label="Quiero", custom_id="quiero_truco"))
        view.add_item(Button(label="No quiero", custom_id="no_truco"))
        # show available raises depending on current truco state and who currently may subir
        # Retruco: allowed when the current state is 'truco' (or a previously
        # accepted truco) and the responder has the right to subir
        if (self.truco_estado == "truco" or self.truco_aceptado) and self.truco_turno_subida == responder_id:
            view.add_item(Button(label="Retruco", custom_id="retruco"))
        # Vale 4: allowed when state is 'retruco' and the responder has the right to subir
        if self.truco_estado == "retruco" and self.truco_turno_subida == responder_id:
            view.add_item(Button(label="Vale 4", custom_id="vale4"))
        return view

    def jugar(self, j, i):
        carta = self.manos[j].pop(i)
        self.mesa.append((j, carta))
        return carta
        # mark that this raise has not yet been accepted

    def evaluar(self):
        (j1,c1),(j2,c2)=self.mesa[-2:]
        if get_rank(c1)>get_rank(c2): 
            self.ganadores_manos.append(j1)
            return j1
        if get_rank(c2)>get_rank(c1): 
            self.ganadores_manos.append(j2)
            return j2
        self.ganadores_manos.append(None)  # parda
        return None

    def puntos_envido(self, j):
        mano = self.manos[j]
        mejores = 0
        for i in range(len(mano)):
            for k in range(i+1,len(mano)):
                if mano[i].get("palo")==mano[k].get("palo"):
                    v1 = mano[i]["valor"] if mano[i]["valor"]<10 else 0
                    v2 = mano[k]["valor"] if mano[k]["valor"]<10 else 0
                    mejores = max(mejores, v1+v2+20)
        if mejores==0:
            mejores = max([c["valor"] if c["valor"]<10 else 0 for c in mano])
        return mejores

game_views = {}

# ===== COMANDO =====
@bot.tree.command(name="truco")
async def truco(interaction: discord.Interaction, puntos: int = 15):
    # Crear la partida pero NO mostrar cartas todavía
    games[interaction.channel.id] = TrucoGame(interaction.user.id, puntos)
    game = games[interaction.channel.id]

    # Responder confirmación y botón para unirse
    view2 = View()
    view2.add_item(Button(label="Unirse", custom_id="join"))

    await interaction.response.send_message(f"🃏 Truco a {puntos} puntos. Partida creada por {interaction.user.name}.", view=view2)
    await interaction.followup.send(f"Esperando contrincante...")

# ===== INTERACCIONES =====
@bot.event
async def on_interaction(interaction):
    if interaction.type != discord.InteractionType.component:
        return

    await interaction.response.defer(ephemeral=True)

    game = games.get(interaction.channel.id)
    if not game:
        return

    cid = interaction.data["custom_id"]
    user = interaction.user.id

    # ===== JOIN =====
    if cid=="join":
        if user in game.jugadores:
            return await interaction.followup.send("Ya estás en la partida", ephemeral=True)
        if len(game.jugadores)>=2:
            return await interaction.followup.send("Llena", ephemeral=True)
        # Agregar jugador y repartir la ronda completa (3 cartas cada uno)
        game.agregar_jugador(user)
        # Repartir desde mazo completo para la ronda inicial
        game.repartir()
        game.turno = game.mano

        await interaction.followup.send("Te uniste", ephemeral=True)

        # Mensajes de unión y mostrar botón público para que cada jugador vea su mano (ephemeral al presionar)
        u1 = await bot.fetch_user(game.jugadores[0])
        u2 = await bot.fetch_user(game.jugadores[1])
        await interaction.channel.send(f"{u2.name} se unió a la sala\n{u1.name} contra {u2.name}\nPuntos: {u1.name}: {game.puntos[game.jugadores[0]]} - {u2.name}: {game.puntos[game.jugadores[1]]}")

        view_show = View()
        view_show.add_item(Button(label="Mostrar mano", custom_id="mostrar_mano"))
        await interaction.channel.send("Nueva ronda. Presionen para ver sus cartas (ephemeral):", view=view_show)
        # Announce who is mano (starter)
        await interaction.channel.send(f"Mano: <@{game.jugadores[game.mano]}>")

    # ===== CARTAS =====
    if cid.startswith("carta_"):
        i=int(cid.split("_")[1])
        # block playing if there's a pending truco or envido response
        if game.esperando_respuesta and game.tipo_espera in ("truco", "envido"):
            return await interaction.followup.send("Hay un canto pendiente. Debes responder antes de jugar.", ephemeral=True)

        if game.jugadores[game.turno]!=user:
            return await interaction.followup.send("No es tu turno", ephemeral=True)

        c=game.jugar(user,i)

        await interaction.followup.send(f"Jugaste {c['emoji']}", ephemeral=True)
        await interaction.channel.send(f"<@{user}> jugó {c['emoji']}")

        # update turn
        game.turno = (game.turno + 1) % 2

        # send updated ephemeral hand to the player who just played, so their UI reflects discarded card
        try:
            await enviar_mano(interaction, user)
        except Exception:
            pass

        if len(game.mesa) % 2 == 0:
            ganador = game.evaluar()
            mano_num = len(game.ganadores_manos)

            if ganador is None:
                # Empate (parda)
                await interaction.channel.send("🤝 Parda")

                # If first hand tied, the second round starts with 'mano'
                if mano_num == 1:
                    # Primera mano parda: la segunda ronda la inicia 'mano'.
                    game.turno = game.mano
                    # Do not auto-send 'Mostrar mano' prompt; next player should press it themselves.
                    return

                elif mano_num == 2:
                    # Segunda mano empatada: desempata por la primera mano
                    if game.ganadores_manos[0] is not None:
                        ganador_ronda = game.ganadores_manos[0]
                    else:
                        ganador_ronda = game.jugadores[game.mano]

                elif mano_num == 3:
                    # Tercera mano empatada: desempate por segunda, primera o mano
                    if game.ganadores_manos[1] is not None:
                        ganador_ronda = game.ganadores_manos[1]
                    elif game.ganadores_manos[0] is not None:
                        ganador_ronda = game.ganadores_manos[0]
                    else:
                        ganador_ronda = game.jugadores[game.mano]

                else:
                    return

                # Terminar la ronda y asignar puntos
                game.puntos[ganador_ronda] += game.truco_valor
                await interaction.channel.send(f"🔥 Ronda para <@{ganador_ronda}> (+{game.truco_valor})")
                u1 = await bot.fetch_user(game.jugadores[0])
                u2 = await bot.fetch_user(game.jugadores[1])
                await interaction.channel.send(f"{u1.name}: {game.puntos[game.jugadores[0]]} - {u2.name}: {game.puntos[game.jugadores[1]]}")

                if game.puntos[ganador_ronda] >= game.max_points:
                    await interaction.channel.send(f"🎉 <@{ganador_ronda}> ganó la partida")
                    del games[interaction.channel.id]
                    return

                # Alternar mano, repartir y NOTIFICAR sin mostrar cartas automáticamente
                game.mano = (game.mano + 1) % 2
                game.repartir()
                view = View()
                view.add_item(Button(label="Mostrar mano", custom_id="mostrar_mano"))
                await interaction.channel.send("Nueva ronda. Presionen para ver sus cartas (ephemeral):", view=view)
                await interaction.channel.send(f"Mano: <@{game.jugadores[game.mano]}>")
                return

            else:
                # Hubo ganador de la mano
                # If there was a previous parda in ganadores_manos and this is the resolving second hand,
                # the winner of this hand takes the round immediately.
                if (None in game.ganadores_manos) and len(game.ganadores_manos) >= 2:
                    ganador_ronda = ganador
                    game.puntos[ganador_ronda] += game.truco_valor
                    await interaction.channel.send(f"🔥 Ronda para <@{ganador_ronda}> (+{game.truco_valor})")
                    u1 = await bot.fetch_user(game.jugadores[0])
                    u2 = await bot.fetch_user(game.jugadores[1])
                    await interaction.channel.send(f"{u1.name}: {game.puntos[game.jugadores[0]]} - {u2.name}: {game.puntos[game.jugadores[1]]}")
                    if game.puntos[ganador_ronda] >= game.max_points:
                        await interaction.channel.send(f"🎉 <@{ganador_ronda}> ganó la partida")
                        del games[interaction.channel.id]
                        return
                    game.mano = (game.mano + 1) % 2
                    game.repartir()
                    view = View()
                    view.add_item(Button(label="Mostrar mano", custom_id="mostrar_mano"))
                    await interaction.channel.send("Nueva ronda. Presionen para ver sus cartas (ephemeral):", view=view)
                    await interaction.channel.send(f"Mano: <@{game.jugadores[game.mano]}>")
                    return

                game.manos_ganadas[ganador] = game.manos_ganadas.get(ganador, 0) + 1
                await interaction.channel.send(f"🏆 Mano para <@{ganador}>")

                # El ganador empieza la siguiente mano
                game.turno = game.jugadores.index(ganador)

                # Do not auto-send 'Mostrar mano' prompt on every turn; players open their hands when needed.
                # Solo terminar la ronda si el ganador ya tiene 2 manos ganadas
                if game.manos_ganadas[ganador] == 2:
                    game.puntos[ganador] += game.truco_valor
                    await interaction.channel.send(f"🔥 Ronda para <@{ganador}> (+{game.truco_valor})")
                    u1 = await bot.fetch_user(game.jugadores[0])
                    u2 = await bot.fetch_user(game.jugadores[1])
                    await interaction.channel.send(f"{u1.name}: {game.puntos[game.jugadores[0]]} - {u2.name}: {game.puntos[game.jugadores[1]]}")

                    if game.puntos[ganador] >= game.max_points:
                        await interaction.channel.send(f"🎉 <@{ganador}> ganó la partida")
                        del games[interaction.channel.id]
                        return
                    # Nueva ronda: alternar mano, repartir y notificar (NO mostrar manos automáticamente)
                    game.mano = (game.mano + 1) % 2
                    game.repartir()
                    view = View()
                    view.add_item(Button(label="Mostrar mano", custom_id="mostrar_mano"))
                    await interaction.channel.send("Nueva ronda. Presionen para ver sus cartas (ephemeral):", view=view)
                    await interaction.channel.send(f"Mano: <@{game.jugadores[game.mano]}>")
                    return

    # ===== TRUCO =====
    if cid=="truco":
        if game.jugadores[game.turno] != user:
            return await interaction.followup.send("No es tu turno para cantar", ephemeral=True)
        if game.esperando_respuesta:
            return await interaction.followup.send("Ya hay un canto pendiente", ephemeral=True)
        rival = game.other(user)
        game.esperando_respuesta = True
        game.tipo_espera = "truco"
        # initial truco raise
        game.truco_estado = "truco"
        game.truco_aceptado = False
        game.truco_cantado_por = user
        # the responder initially has the right to subir (they may Retruco)
        game.truco_turno_subida = rival
        game.quien_responde = rival
        view = game.build_truco_view(rival)
        await interaction.channel.send(f"<@{user}> cantó Truco. Responde <@{rival}>:", view=view)

    if cid=="quiero_truco":
        if not game.esperando_respuesta or game.tipo_espera != "truco" or game.quien_responde != user:
            return await interaction.followup.send("No es tu turno para responder", ephemeral=True)
        # set truco_valor according to current state
        if game.truco_estado == "truco":
            game.truco_valor = 2
        elif game.truco_estado == "retruco":
            game.truco_valor = 3
        elif game.truco_estado == "vale4":
            game.truco_valor = 4
        # accepted: the acceptor gains the right to subir (may Retruco later)
        game.truco_turno_subida = user
        # mark that the truco was accepted; keep state information so UIs
        # can show available raises (Retruco/Vale4) correctly
        game.truco_aceptado = True
        game.esperando_respuesta = False
        game.tipo_espera = None
        game.quien_responde = None
        await interaction.channel.send(f"<@{user}> quiso el Truco")
        # Do not send redundant ephemeral 'Tus opciones' here; players can
        # open their 'Mostrar mano' to see available responses/raises.

    if cid=="no_truco":
        if not game.esperando_respuesta or game.tipo_espera != "truco" or game.quien_responde != user:
            return await interaction.followup.send("No es tu turno para responder", ephemeral=True)
        rival = game.other(user)
        puntos_no_querer = 1 if game.truco_estado == "truco" else 2 if game.truco_estado == "retruco" else 3
        game.puntos[rival] += puntos_no_querer
        # check for game end
        if game.puntos[rival] >= game.max_points:
            await interaction.channel.send(f"🎉 <@{rival}> ganó la partida")
            del games[interaction.channel.id]
            return
        # reset truco state
        game.truco_estado = "normal"
        game.truco_aceptado = False
        game.esperando_respuesta = False
        game.tipo_espera = None
        game.quien_responde = None
        await interaction.channel.send(f"<@{user}> no quiso. Punto para <@{rival}> (+{puntos_no_querer})")
        # clear truco temporary trackers
        game.truco_cantado_por = None
        game.truco_turno_subida = None
        u1 = await bot.fetch_user(game.jugadores[0])
        u2 = await bot.fetch_user(game.jugadores[1])
        await interaction.channel.send(f"{u1.name}: {game.puntos[game.jugadores[0]]} - {u2.name}: {game.puntos[game.jugadores[1]]}")
        # Terminar ronda: alternate mano then repartir y NOTIFICAR sin mostrar cartas automáticamente
        game.mano = (game.mano + 1) % 2
        game.repartir()
        view = View()
        view.add_item(Button(label="Mostrar mano", custom_id="mostrar_mano"))
        await interaction.channel.send(f"Ronda terminada. Ganador: <@{rival}>. Presionen para ver sus cartas (ephemeral):", view=view)

    if cid=="retruco":
        # Allow retruco either as a response to a pending truco OR as an
        # immediate raise after a previously-accepted Truco if this player
        # has the right to "subir".
        allowed = False
        if game.esperando_respuesta and game.tipo_espera == "truco" and game.quien_responde == user:
            allowed = True
        elif (not game.esperando_respuesta) and game.truco_aceptado and game.truco_turno_subida == user:
            allowed = True
        if not allowed:
            return await interaction.followup.send("No es tu turno para responder", ephemeral=True)
        # Retruco: raise the level and ask the original caller to respond
        game.truco_estado = "retruco"
        game.truco_aceptado = False
        game.truco_cantado_por = user
        # after a retruco the other player must respond (typically the original caller)
        game.quien_responde = game.other(user)
        # the original caller has the right to subir (they may call Vale 4)
        game.truco_turno_subida = game.quien_responde
        game.esperando_respuesta = True
        game.tipo_espera = "truco"
        view = game.build_truco_view(game.quien_responde)
        await interaction.channel.send(f"<@{user}> cantó Retruco. Responde <@{game.quien_responde}>:", view=view)

    if cid=="vale4":
        if not game.esperando_respuesta or game.tipo_espera != "truco" or game.quien_responde != user:
            return await interaction.followup.send("No es tu turno para responder", ephemeral=True)
        # Vale 4: final raise (only allowed when turno_subida was set after Quiero to a retruco)
        game.truco_estado = "vale4"
        game.truco_aceptado = False
        game.truco_cantado_por = user
        # opponent must respond
        game.quien_responde = game.other(user)
        game.truco_turno_subida = None
        game.esperando_respuesta = True
        game.tipo_espera = "truco"
        view = game.build_truco_view(game.quien_responde)
        await interaction.channel.send(f"<@{user}> cantó Vale 4. Responde <@{game.quien_responde}>:", view=view)

    # ===== ENVIDO =====
    if cid=="envido":
        # instead of directly cantando, present a private ephemeral selector to the singer
        if game.jugadores[game.turno] != user:
            return await interaction.followup.send("No es tu turno para cantar", ephemeral=True)
        if len(game.mesa) >= 2:
            return await interaction.followup.send("No se puede cantar envido después de la primera carta", ephemeral=True)
        if game.esperando_respuesta:
            return await interaction.followup.send("Ya hay un canto pendiente", ephemeral=True)
        # ephemeral selector for envido variant
        sel = View()
        sel.add_item(Button(label="Envido", custom_id="cantar_envido_envido"))
        sel.add_item(Button(label="Real Envido", custom_id="cantar_envido_real"))
        sel.add_item(Button(label="Falta Envido", custom_id="cantar_envido_falta"))
        return await interaction.followup.send("Seleccionar opcion:", view=sel, ephemeral=True)

    if cid=="envido_doble":
        if not game.esperando_respuesta or game.tipo_espera != "envido" or game.quien_responde != user:
            return await interaction.followup.send("No es tu turno para responder", ephemeral=True)
        # raise to doble
        game.envido_state = "doble"
        game.envido_history.append(("envido", 2))
        game.envido_valor = sum(v for _,v in game.envido_history)
        # flip responder
        game.quien_responde = game.other(user)
        view = game.build_envido_view(game.quien_responde)
        await interaction.channel.send(f"<@{user}> cantó Envido. Responde <@{game.quien_responde}>:", view=view)

    # Handlers for the singer selecting the envido variant (ephemeral selector buttons)
    if cid.startswith("cantar_envido_"):
        # only allow the player whose turn it is to choose
        if game.jugadores[game.turno] != user:
            return await interaction.followup.send("No puedes cantar envido ahora", ephemeral=True)
        if game.esperando_respuesta:
            return await interaction.followup.send("Ya hay un canto pendiente", ephemeral=True)
        rival = game.other(user)
        # map custom ids
        if cid == "cantar_envido_envido":
            game.envido_state = "envido"
            game.envido_history.append(("envido", 2))
        elif cid == "cantar_envido_real":
            game.envido_state = "real"
            game.envido_history.append(("real", 3))
        elif cid == "cantar_envido_falta":
            game.envido_state = "falta"
            falta_amount = game.max_points - game.puntos.get(rival, 0)
            game.envido_history.append(("falta", falta_amount))
        else:
            return await interaction.followup.send("Opción inválida", ephemeral=True)
        game.envido_valor = sum(v for _,v in game.envido_history)
        game.envido_cantado = True
        game.esperando_respuesta = True
        game.tipo_espera = "envido"
        game.quien_responde = rival
        view = game.build_envido_view(rival)
        # use a clear label depending on which envido variant was chosen
        label = "Envido"
        if game.envido_state == "real":
            label = "Real Envido"
        elif game.envido_state == "falta":
            label = "Falta Envido"
        await interaction.channel.send(f"<@{user}> cantó {label}. Responde <@{rival}>:", view=view)
        return await interaction.followup.send(f"Cantaste {game.envido_state}", ephemeral=True)

    if cid=="real_envido":
        if not game.esperando_respuesta or game.tipo_espera != "envido" or game.quien_responde != user:
            return await interaction.followup.send("No es tu turno para responder", ephemeral=True)
        game.envido_state = "real"
        game.envido_history.append(("real", 3))
        game.envido_valor = sum(v for _,v in game.envido_history)
        game.quien_responde = game.other(user)
        view = game.build_envido_view(game.quien_responde)
        await interaction.channel.send(f"<@{user}> cantó Real Envido. Responde <@{game.quien_responde}>:", view=view)

    if cid=="falta_envido":
        if not game.esperando_respuesta or game.tipo_espera != "envido" or game.quien_responde != user:
            return await interaction.followup.send("No es tu turno para responder", ephemeral=True)
        # Falta Envido: value is remaining points to opponent
        opponent = game.other(user)
        game.envido_state = "falta"
        falta_amount = game.max_points - game.puntos[opponent]
        game.envido_history.append(("falta", falta_amount))
        game.envido_valor = sum(v for _,v in game.envido_history)
        game.quien_responde = opponent
        view = game.build_envido_view(game.quien_responde)
        await interaction.channel.send(f"<@{user}> cantó Falta Envido. Responde <@{game.quien_responde}>:", view=view)

    if cid=="quiero_envido":
        if not game.esperando_respuesta or game.tipo_espera != "envido" or game.quien_responde != user:
            return await interaction.followup.send("No es tu turno para responder", ephemeral=True)
        p1,p2 = game.jugadores
        e1 = game.puntos_envido(p1)
        e2 = game.puntos_envido(p2)
        # determine winner (mano wins ties)
        if e1 > e2:
            ganador = p1
        elif e2 > e1:
            ganador = p2
        else:
            ganador = game.mano_id()
        # determine points to award: if last canto was 'falta', award that falta amount, else award full sum
        puntos_a_dar = 0
        if len(game.envido_history) > 0 and game.envido_history[-1][0] == "falta":
            puntos_a_dar = game.envido_history[-1][1]
        else:
            puntos_a_dar = sum(v for _,v in game.envido_history)
        # award points
        game.puntos[ganador] += puntos_a_dar
        # check for game end
        if game.puntos[ganador] >= game.max_points:
            await interaction.channel.send(f"🎉 <@{ganador}> ganó la partida")
            del games[interaction.channel.id]
            return
        game.esperando_respuesta = False
        game.tipo_espera = None
        game.envido_state = None
        game.envido_history = []
        game.envido_valor = 0
        # Reveal only winner's envido and hide loser's with 'Son buenas'
        mano = game.mano_id()
        pie = game.pie_id()
        if ganador == mano:
            mano_pts = game.puntos_envido(mano)
            await interaction.channel.send(f"Envido: {mano_pts} vs Son buenas. Gana <@{ganador}> (+{puntos_a_dar})")
        else:
            pie_pts = game.puntos_envido(pie)
            await interaction.channel.send(f"Envido: Son buenas vs {pie_pts}. Gana <@{ganador}> (+{puntos_a_dar})")
        u1 = await bot.fetch_user(p1)
        u2 = await bot.fetch_user(p2)
        await interaction.channel.send(f"{u1.name}: {game.puntos[p1]} - {u2.name}: {game.puntos[p2]}")

    if cid=="no_envido":
        if not game.esperando_respuesta or game.tipo_espera != "envido" or game.quien_responde != user:
            return await interaction.followup.send("No es tu turno para responder", ephemeral=True)
        winner = game.other(user)
        # refusing: points equals the accumulated points before the last canto, or 1 if there was only one canto
        if len(game.envido_history) <= 1:
            puntos_no_quiero = 1
        else:
            puntos_no_quiero = sum(v for _,v in game.envido_history[:-1])
            if puntos_no_quiero == 0:
                puntos_no_quiero = 1
        game.puntos[winner] += puntos_no_quiero
        # check for game end
        if game.puntos[winner] >= game.max_points:
            await interaction.channel.send(f"🎉 <@{winner}> ganó la partida")
            del games[interaction.channel.id]
            return
        # capture what was the last canto to give a clearer message
        last_type = game.envido_history[-1][0] if len(game.envido_history) > 0 else "envido"
        game.esperando_respuesta = False
        game.tipo_espera = None
        game.envido_state = None
        game.envido_history = []
        game.envido_valor = 0
        # More explicit refusal message (include which canto was refused)
        label = "envido"
        if last_type == "real":
            label = "real envido"
        elif last_type == "falta":
            label = "falta envido"
        await interaction.channel.send(f"<@{user}> no quiso {label}. Punto para <@{winner}> (+{puntos_no_quiero})")
        u1 = await bot.fetch_user(game.jugadores[0])
        u2 = await bot.fetch_user(game.jugadores[1])
        await interaction.channel.send(f"{u1.name}: {game.puntos[game.jugadores[0]]} - {u2.name}: {game.puntos[game.jugadores[1]]}")

    # ===== FOLD =====
    if cid == "fold":
        rival = game.jugadores[(game.jugadores.index(user) + 1) % 2]
        game.puntos[rival] += game.truco_valor
        await interaction.followup.send("Te fuiste al mazo", ephemeral=True)
        await interaction.channel.send(f"<@{user}> se fue al mazo. Punto para <@{rival}> (+{game.truco_valor})")
        u1 = await bot.fetch_user(game.jugadores[0])
        u2 = await bot.fetch_user(game.jugadores[1])
        await interaction.channel.send(f"{u1.name}: {game.puntos[game.jugadores[0]]} - {u2.name}: {game.puntos[game.jugadores[1]]}")
        if game.puntos[rival] >= game.max_points:
            await interaction.channel.send(f"🎉 <@{rival}> ganó la partida")
            del games[interaction.channel.id]
            return
        # Terminar ronda: alternar mano y repartir (no mostrar automáticamente las manos)
        game.mano = (game.mano + 1) % 2
        game.repartir()
        view = View()
        view.add_item(Button(label="Mostrar mano", custom_id="mostrar_mano_rival"))
        await interaction.channel.send("Nueva ronda. Presionen para ver sus cartas (ephemeral):", view=view)

    # ===== LEAVE =====
    if cid == "leave":
        if user in game.jugadores:
            game.jugadores.remove(user)
            await interaction.followup.send("Dejaste la partida", ephemeral=True)
            if len(game.jugadores) <= 1:
                if len(game.jugadores) == 1:
                    winner = game.jugadores[0]
                    await interaction.channel.send(f"<@{user}> dejó la partida. <@{winner}> gana por abandono")
                else:
                    await interaction.channel.send("Partida terminada")
                del games[interaction.channel.id]

    if cid == "mostrar_mano":
        # Mostrar mano al usuario que presionó
        await enviar_mano(interaction, user)

    if cid == "mostrar_mano_rival":
        # Mostrar mano al rival
        try:
            rival = game.other(user)
            await enviar_mano(interaction, rival)
        except Exception:
            await interaction.followup.send("No se pudo mostrar la mano del rival.", ephemeral=True)

async def enviar_mano(interaction, j):
    game = games[interaction.channel.id]

    view=View()
    # defensive: ensure j is a valid key in game.manos
    if j not in game.manos:
        # try converting if j is a discord object
        try:
            jid = getattr(j, "id", None)
            if jid and jid in game.manos:
                j = jid
            else:
                return await interaction.followup.send("No estás en la partida.", ephemeral=True)
        except Exception:
            return await interaction.followup.send("No estás en la partida.", ephemeral=True)

    for i,c in enumerate(game.manos[j]):
        view.add_item(Button(label=c["emoji"],custom_id=f"carta_{i}"))

    # If there's a pending Truco response and this player must respond,
    # show the truco response buttons (Quiero/No quiero and raises if allowed).
    if game.esperando_respuesta and game.tipo_espera == "truco" and game.quien_responde == j:
        truco_view = game.build_truco_view(j)
        for child in truco_view.children:
            view.add_item(child)
    else:
        # regular Truco button to initiate. If a previously-called Truco
        # was already accepted, show 'Retruco' as the available raise label
        # (the handler will enforce who may actually play it).
        if game.truco_aceptado:
            view.add_item(Button(label="Retruco", custom_id="retruco"))
        else:
            view.add_item(Button(label="Truco",custom_id="truco"))

    # If there's a pending Envido response and this player must respond,
    # show the envido response buttons (Quiero/No quiero and variants if allowed).
    if game.esperando_respuesta and game.tipo_espera == "envido" and game.quien_responde == j:
        en_view = game.build_envido_view(j)
        for child in en_view.children:
            view.add_item(child)
    else:
        # regular Envido button to initiate
        view.add_item(Button(label="Envido",custom_id="envido"))

    view.add_item(Button(label="Me voy al mazo",custom_id="fold"))
    view.add_item(Button(label="Dejar partida",custom_id="leave"))

    await interaction.followup.send("Tus cartas:",view=view,ephemeral=True)

if not DISCORD_TOKEN:
    print("ERROR: DISCORD_TOKEN no está definido. Define la variable de entorno antes de ejecutar.")
    raise SystemExit(1)

webserver.keep_alive()

try:
    bot.run(DISCORD_TOKEN)
except Exception as e:
    print("Error iniciando el bot:", e)
    raise