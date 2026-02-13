import discord
from discord.ext import commands

import asyncio
import datetime
import io
import aiohttp
import json
import os


# ================= CONFIG =================

COR_PLATFORM = discord.Color.from_rgb(86, 3, 173)

BANNER_URL = "https://media.discordapp.net/attachments/1383636357745737801/1465105440789757972/bannerdestroyer.gif"

ID_CATEGORIA_TICKETS = 1357569803778392269
ID_CANAL_LOG_TICKETS = 1392528999623692460
ID_CANAL_AVALIACOES = 1385313899699765380

ID_DONO_BOT = 1304003843172077659

ID_CARGO_SETUP = 1357569800947237000
ID_CARGO_SUPORTE = 1357569800938721349
ID_CARGO_HMOD = 1431475496377389177
ID_CARGO_SUPERVISOR = 1414283452878028800
ID_CARGO_ADM = 1357569800947236998
ID_CARGO_CM = 1414283694662750268
ID_CARGO_MANAGER = 1357569800947237000

IDS_IMUNES_BLOQUEIO = [
    ID_CARGO_ADM,
    ID_CARGO_CM,
    ID_CARGO_MANAGER,
    ID_CARGO_SETUP
]

IDS_ALTA_STAFF = [
    ID_CARGO_HMOD,
    ID_CARGO_SUPERVISOR,
    ID_CARGO_ADM,
    ID_CARGO_CM,
    ID_CARGO_MANAGER
]

IDS_PERMITIDOS_SUPORTE = [
    ID_CARGO_SUPORTE,
    ID_CARGO_ADM,
    ID_CARGO_CM,
    ID_CARGO_MANAGER
]

TICKET_ENDPOINT = "https://otzrrxefahqeovfbonag.supabase.co/functions/v1/register-ticket"

STATS_FILE = "stats.json"


# ================= STATS =================

def carregar_stats():
    if not os.path.exists(STATS_FILE):
        return {}
    with open(STATS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_stats(data):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def registrar_stats(staff_id, nota=None):
    data = carregar_stats()
    sid = str(staff_id)
    hoje = datetime.datetime.now().strftime("%Y-%m-%d")

    if sid not in data:
        data[sid] = {
            "total": 0,
            "hoje": 0,
            "av_count": 0,
            "soma": 0,
            "data": hoje,
            "primeiro": hoje,
            "ultimo": hoje
        }

    if data[sid]["data"] != hoje:
        data[sid]["hoje"] = 0
        data[sid]["data"] = hoje

    if nota:
        data[sid]["av_count"] += 1
        data[sid]["soma"] += int(nota)
    else:
        data[sid]["total"] += 1
        data[sid]["hoje"] += 1
        data[sid]["ultimo"] = hoje

    salvar_stats(data)


# ================= API =================

async def registrar_ticket_site(payload):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                TICKET_ENDPOINT,
                json=payload,
                timeout=8
            ) as r:
                print(f"[API] {payload.get('action')} -> {r.status}")
                
                if r.status != 200:
                    print(f"[API DEBUG] Payload enviado:")
                    print(json.dumps(payload, indent=2, ensure_ascii=False))
                    try:
                        erro = await r.text()
                        print(f"[API DEBUG] Resposta do servidor: {erro}")
                    except:
                        pass
                
                return r.status
    except Exception as e:
        print(f"[API ERROR] {e}")
        return None


# ================= MODAL AVALIAÇÃO =================

class ComentarioModal(discord.ui.Modal, title="Avaliação do Atendimento"):
    comentario = discord.ui.TextInput(
        label="Feedback",
        style=discord.TextStyle.paragraph,
        placeholder="Conte-nos como foi o seu atendimento...",
        required=True
    )

    def __init__(self, staff_id, nota, channel_name, channel_id, user_id):
        super().__init__()
        self.staff_id = staff_id
        self.nota = nota
        self.channel_name = channel_name
        self.channel_id = channel_id
        self.user_id = user_id

    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True)
        
        registrar_stats(self.staff_id, self.nota)
        
        canal_av = interaction.client.get_channel(ID_CANAL_AVALIACOES)
        if canal_av:
            embed = discord.Embed(
                title="⭐ Nova Avaliação de Ticket",
                color=discord.Color.gold()
            )
            embed.add_field(name="Nome do Ticket", value=f"{self.channel_name}", inline=True)
            embed.add_field(name="Channel ID", value=f"{self.channel_id}", inline=True)
            embed.add_field(name="Criado Por", value=f"<@{self.user_id}>", inline=True)
            embed.add_field(name="Claimed By", value=f"<@{self.staff_id}>", inline=True)
            embed.add_field(name="Rating", value="⭐" * int(self.nota), inline=True)
            embed.add_field(name="User Feedback", value=self.comentario.value, inline=False)
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="View Transcript", style=discord.ButtonStyle.link, url=f"https://discord.com/channels/{interaction.guild.id}/{self.channel_id}"))
            
            await canal_av.send(embed=embed, view=view)
        
        await interaction.followup.send(
            f"<a:1316869378276458648:1384573961324593152> Obrigado por avaliar o atendimento de <@{self.staff_id}>",
            ephemeral=True
        )


# ================= VIEW AVALIAÇÃO DM =================

class AvaliacaoDMView(discord.ui.View):
    def __init__(self, staff_id, channel_name, channel_id, user_id):
        super().__init__(timeout=86400)
        self.staff_id = staff_id
        self.channel_name = channel_name
        self.channel_id = channel_id
        self.user_id = user_id

    @discord.ui.select(
        placeholder="Escolha uma nota de 1 a 5",
        options=[
            discord.SelectOption(label="1 Estrela", value="1", emoji="⭐"),
            discord.SelectOption(label="2 Estrelas", value="2", emoji="⭐"),
            discord.SelectOption(label="3 Estrelas", value="3", emoji="⭐"),
            discord.SelectOption(label="4 Estrelas", value="4", emoji="⭐"),
            discord.SelectOption(label="5 Estrelas", value="5", emoji="⭐"),
        ]
    )
    async def select_callback(self, interaction, select):
        await interaction.response.send_modal(
            ComentarioModal(
                self.staff_id,
                select.values[0],
                self.channel_name,
                self.channel_id,
                self.user_id
            )
        )


# ================= VIEW REIVINDICAR (COM LOGS) =================

class ReivindicarView(discord.ui.View):
    def __init__(self, user_id=None, tipo=None, staff_id=None):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.tipo = tipo
        self.staff_id = staff_id
    
    async def enviar_log_ticket(self, interaction, acao, cor, detalhes=None):
        """Envia logs do ticket para o canal configurado"""
        canal_log = interaction.client.get_channel(ID_CANAL_LOG_TICKETS)
        if not canal_log:
            return
        
        embed = discord.Embed(
            title=f"📋 Log de Ticket - {acao.upper()}",
            color=cor,
            timestamp=datetime.datetime.now()
        )
        
        embed.add_field(name="Canal", value=f"{interaction.channel.mention} (`{interaction.channel.id}`)", inline=False)
        embed.add_field(name="Tipo", value=self.tipo or "Desconhecido", inline=True)
        embed.add_field(name="Dono", value=f"<@{self.user_id}>" if self.user_id else "Desconhecido", inline=True)
        
        if acao == "claim":
            embed.add_field(name="Reivindicado por", value=f"<@{self.staff_id}>", inline=True)
        
        elif acao == "unclaim":
            embed.add_field(name="Unclaimed por", value=f"<@{interaction.user.id}>", inline=True)
        
        elif acao == "close":
            embed.add_field(name="Fechado por", value=f"<@{interaction.user.id}>", inline=True)
            if self.staff_id:
                embed.add_field(name="Atendente", value=f"<@{self.staff_id}>", inline=True)
        
        if detalhes:
            embed.add_field(name="Detalhes", value=detalhes, inline=False)
        
        await canal_log.send(embed=embed)

    @discord.ui.button(
        label="Reivindicar",
        style=discord.ButtonStyle.success,
        emoji="🛡️",
        custom_id="ticket_claim"
    )
    async def claim(self, interaction, button):
        await interaction.response.defer()

        if self.staff_id:
            return await interaction.followup.send(
                f"<a:c_negativo:1384563046944608369> Já está em atendimento por <@{self.staff_id}>",
                ephemeral=True
            )

        permitidos = IDS_PERMITIDOS_SUPORTE if self.tipo == "suporte" else IDS_ALTA_STAFF
        if not (interaction.user.id == ID_DONO_BOT or any(r.id in permitidos for r in interaction.user.roles)):
            return await interaction.followup.send("<a:c_negativo:1384563046944608369> Sem permissão.", ephemeral=True)

        self.staff_id = interaction.user.id

        await registrar_ticket_site({
            "action": "claim",
            "discord_channel_id": str(interaction.channel.id),
            "discord_user_id": str(self.staff_id)
        })

        # LOG DO CLAIM
        await self.enviar_log_ticket(interaction, "claim", discord.Color.blue())

        button.disabled = True
        button.label = f"Reivindicado por {interaction.user.display_name}"
        await interaction.edit_original_response(view=self)

        await interaction.channel.send(f"<:Shield:1385488234137784391> Atendimento iniciado por <@{interaction.user.id}>")

    @discord.ui.button(
        label="Unclaim",
        style=discord.ButtonStyle.secondary,
        emoji="🔄",
        custom_id="ticket_unclaim"
    )
    async def unclaim(self, interaction, button):
        await interaction.response.defer()

        if not (interaction.user.id == self.staff_id or 
                interaction.user.id == ID_DONO_BOT or 
                any(r.id in IDS_IMUNES_BLOQUEIO for r in interaction.user.roles)):
            return await interaction.followup.send("<a:c_negativo:1384563046944608369> Sem permissão.", ephemeral=True)

        # LOG DO UNCLAIM (antes de alterar)
        await self.enviar_log_ticket(interaction, "unclaim", discord.Color.orange())

        self.staff_id = None

        await registrar_ticket_site({
            "action": "unclaim",
            "discord_channel_id": str(interaction.channel.id)
        })

        for child in self.children:
            if child.custom_id == "ticket_claim":
                child.disabled = False
                child.label = "Reivindicar"

        await interaction.edit_original_response(view=self)
        await interaction.channel.send("<a:1316869378276458648:1384573961324593152> A equipe agora pode interagir novamente")

    @discord.ui.button(
        label="Fechar Ticket",
        style=discord.ButtonStyle.danger,
        emoji="<:cad:1470892720846409780>",
        custom_id="ticket_close"
    )
    async def close(self, interaction, button):
        await interaction.response.defer()

        canal = interaction.channel
        tipo_ticket = None
        if canal.topic:
            for parte in canal.topic.split("|"):
                if "Tipo:" in parte:
                    tipo_ticket = parte.replace("Tipo:", "").strip()
                    break
        
        tem_permissao = False
        
        if interaction.user.id == self.staff_id:
            tem_permissao = True
            
        elif interaction.user.id == ID_DONO_BOT:
            tem_permissao = True
          
        elif any(r.id in IDS_IMUNES_BLOQUEIO for r in interaction.user.roles):
            tem_permissao = True
        
        elif tipo_ticket == "suporte" and any(r.id == ID_CARGO_SUPORTE for r in interaction.user.roles):
            tem_permissao = True
        
        if not tem_permissao:
            return await interaction.followup.send(
                f"<a:c_negativo:1384563046944608369> Sem permissão para fechar este ticket.\n"
                f"{'Apenas equipe de alta patente pode fechar denúncias.' if tipo_ticket == 'denuncia' else 'Você não tem permissão.'}",
                ephemeral=True
            )
        
        # LOG DO CLOSE (antes de deletar!)
        await self.enviar_log_ticket(interaction, "close", discord.Color.red())
        
        await registrar_ticket_site({
            "action": "close",
            "discord_channel_id": str(interaction.channel.id),
            "discord_user_id": str(interaction.user.id),  
            "assigned_to": str(self.staff_id) if self.staff_id else None  
        })

        if self.staff_id:
            registrar_stats(self.staff_id)

        await interaction.channel.send("<:cad:1470892720846409780> Fechando canal e enviando avaliação para a DM")

        if self.user_id and self.staff_id:
            try:
                user = await interaction.client.fetch_user(self.user_id)
                embed_dm = discord.Embed(
                    title="Avalie nosso atendimento",
                    description=f"Seu ticket em **{interaction.guild.name}** foi finalizado por <@{self.staff_id}>.\nComo você avalia o suporte recebido?",
                    color=COR_PLATFORM
                )
                await user.send(embed=embed_dm, view=AvaliacaoDMView(
                    self.staff_id,
                    interaction.channel.name,
                    interaction.channel.id,
                    self.user_id
                ))
            except Exception as e:
                print(f"❌ Erro ao enviar DM: {e}")

        await asyncio.sleep(2)
        await interaction.channel.delete()


# ================= VIEW PRINCIPAL =================

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Suporte",
        style=discord.ButtonStyle.secondary,
        emoji="<:Hammer:1385488289233899630>",
        custom_id="open_suporte"
    )
    async def suporte(self, interaction, button):
        await self.criar_ticket(interaction, "suporte", ID_CARGO_SUPORTE, IDS_PERMITIDOS_SUPORTE)

    @discord.ui.button(
        label="Denúncia",
        style=discord.ButtonStyle.secondary,
        emoji="<a:denuncia:1384574096557346916>",
        custom_id="open_denuncia"
    )
    async def denuncia(self, interaction, button):
        await self.criar_ticket(interaction, "denuncia", ID_CARGO_SUPERVISOR, IDS_ALTA_STAFF)

    async def criar_ticket(self, interaction, tipo, cargo_ping_id, cargos_permitidos):
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        categoria = guild.get_channel(ID_CATEGORIA_TICKETS)
        
        nome = f"{tipo}-{interaction.user.name}".lower().replace(" ", "-")
        
        tickets_abertos = 0
        for channel in categoria.channels:
            if channel.topic and f"Dono: {interaction.user.id}" in channel.topic:
                tickets_abertos += 1
        
        if tickets_abertos >= 1:
            return await interaction.followup.send(
                f"<a:c_negativo:1384563046944608369> Você já possui **{tickets_abertos} ticket(s)** aberto(s). Feche-o(s) antes de abrir outro.",
                ephemeral=True
            )
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }
        
        for role_id in cargos_permitidos:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        
        canal = await guild.create_text_channel(
            name=nome,
            category=categoria,
            overwrites=overwrites,
            topic=f"Dono: {interaction.user.id} | Tipo: {tipo} | Aberto: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        
        await registrar_ticket_site({
            "action": "open",
            "discord_channel_id": str(canal.id),
            "discord_user_id": str(interaction.user.id)
        })
        
        # LOG DO OPEN
        canal_log = interaction.client.get_channel(ID_CANAL_LOG_TICKETS)
        if canal_log:
            embed_log = discord.Embed(
                title="📋 Log de Ticket - ABERTO",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            embed_log.add_field(name="Canal", value=f"{canal.mention} (`{canal.id}`)", inline=False)
            embed_log.add_field(name="Tipo", value=tipo, inline=True)
            embed_log.add_field(name="Aberto por", value=f"<@{interaction.user.id}>", inline=True)
            embed_log.add_field(name="Dono", value=f"<@{interaction.user.id}>", inline=True)
            await canal_log.send(embed=embed_log)
        
        embed = discord.Embed(
            title=f"Atendimento - {tipo.upper()}",
            description=f"Olá <@{interaction.user.id}>,\ndescreva seu problema para que nós possamos resolver o mais rápido possível.",
            color=COR_PLATFORM
        )
        embed.set_image(url=BANNER_URL)
        
        cargo_ping = guild.get_role(cargo_ping_id)
        await canal.send(
            content=f"{cargo_ping.mention}" if cargo_ping else None,
            embed=embed,
            view=ReivindicarView(interaction.user.id, tipo),
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
        
        await interaction.followup.send(f"Ticket criado: {canal.mention}", ephemeral=True)


# ================= COG =================

class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="setup_ticket", description="Envia o painel de tickets")
    async def setup_ticket(self, ctx):
        if not (ctx.author.id == ID_DONO_BOT or any(r.id == ID_CARGO_SETUP for r in ctx.author.roles)):
            return await ctx.send("<a:c_negativo:1384563046944608369> Sem permissão.", ephemeral=True)

        embed = discord.Embed(
            title="Platform Destroyer | Tickets",
            description=(
                "Para redirecionarmos mais eficientemente o seu atendimento, siga estes parâmetros!\n\n"
                "**<:Hammer:1385488289233899630> Suporte:**\n"
                "• Destinado à tirar dúvidas e reportar erros nas scripts!\n\n"
                "**<a:denuncia:1384574096557346916> Denúncia:**\n"
                "• Destinado à denúncia de membros!\n\n"
                "Pedimos encarecidamente que não abram tickets com o intuito de brincadeiras.\n"
                "Sejam empáticos com o próximo."
            ),
            color=COR_PLATFORM
        )
        embed.set_image(url=BANNER_URL)
        await ctx.send(embed=embed, view=TicketView())


# ================= SETUP =================

async def setup(bot):
    bot.add_view(TicketView())
    bot.add_view(ReivindicarView())
    await bot.add_cog(Ticket(bot))
    print("✅ Sistema de tickets carregado com sucesso!")
