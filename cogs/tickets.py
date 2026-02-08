import discord
from discord.ext import commands
import asyncio
import datetime
import io
import aiohttp
import json
import os

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

IDS_IMUNES_BLOQUEIO = [ID_CARGO_ADM, ID_CARGO_CM, ID_CARGO_MANAGER, ID_CARGO_SETUP]
IDS_ALTA_STAFF = [ID_CARGO_HMOD, ID_CARGO_SUPERVISOR, ID_CARGO_ADM, ID_CARGO_CM, ID_CARGO_MANAGER]
IDS_PERMITIDOS_SUPORTE = [ID_CARGO_SUPORTE, ID_CARGO_ADM, ID_CARGO_CM, ID_CARGO_MANAGER]

TICKET_ENDPOINT = "https://otzrrxefahqeovfbonag.supabase.co/functions/v1/register-ticket"
STATS_FILE = "stats.json"

def carregar_stats():
    if not os.path.exists(STATS_FILE): return {}
    with open(STATS_FILE, "r") as f: return json.load(f)

def salvar_stats(data):
    with open(STATS_FILE, "w") as f: json.dump(data, f, indent=4)

def registrar_stats_local(staff_id, nota=None):
    data = carregar_stats()
    sid = str(staff_id)
    hoje = datetime.datetime.now().strftime("%Y-%m-%d")
    if sid not in data:
        data[sid] = {"total": 0, "hoje": 0, "av_count": 0, "soma": 0, "data": hoje, "primeiro": hoje, "ultimo": hoje}
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

async def registrar_ticket_site(payload):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(TICKET_ENDPOINT, json=payload, timeout=5) as response:
                return response.status
    except: return None

class ComentarioModal(discord.ui.Modal, title="Avaliação do Atendimento"):
    comentario = discord.ui.TextInput(label="Feedback", style=discord.TextStyle.paragraph, placeholder="Conte-nos como foi o seu atendimento...", required=True)
    
    def __init__(self, staff_id, nota, channel_name, channel_id, user_id):
        super().__init__()
        self.staff_id = staff_id
        self.nota = nota
        self.channel_name = channel_name
        self.channel_id = channel_id
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        registrar_stats_local(self.staff_id, self.nota)
        
        log_av = interaction.guild.get_channel(ID_CANAL_AVALIACOES)
        if log_av:
            embed = discord.Embed(title="Ticket Rating", color=COR_PLATFORM)
            embed.add_field(name="Nome do Ticket", value=f"{self.channel_name}", inline=True)
            embed.add_field(name="Channel ID", value=f"{self.channel_id}", inline=True)
            embed.add_field(name="Criado Por", value=f"<@{self.user_id}>", inline=True)
            embed.add_field(name="Claimed By", value=f"<@{self.staff_id}>", inline=True)
            embed.add_field(name="Rating", value="⭐" * int(self.nota), inline=True)
            embed.add_field(name="User Feedback", value=self.comentario.value, inline=False)
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="View Transcript", style=discord.ButtonStyle.link, url=f"https://discord.com/channels/{interaction.guild.id}/{ID_CANAL_LOG_TICKETS}"))
            view.add_item(discord.ui.Button(label="View Ticket Info", style=discord.ButtonStyle.link, url=f"https://discord.com/channels/{interaction.guild.id}/{ID_CANAL_LOG_TICKETS}"))
            
            await log_av.send(embed=embed, view=view)

        await interaction.response.send_message(f"✅ Obrigado por avaliar o atendimento de <@{self.staff_id}>", ephemeral=True)

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
            discord.SelectOption(label="⭐", value="1"),
            discord.SelectOption(label="⭐⭐", value="2"),
            discord.SelectOption(label="⭐⭐⭐", value="3"),
            discord.SelectOption(label="⭐⭐⭐⭐", value="4"),
            discord.SelectOption(label="⭐⭐⭐⭐⭐", value="5"),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.send_modal(ComentarioModal(self.staff_id, select.values[0], self.channel_name, self.channel_id, self.user_id))
        self.stop()

class ReivindicarView(discord.ui.View):
    def __init__(self, usuario_id=None, tipo=None, staff_id=None):
        super().__init__(timeout=None)
        self.usuario_id = usuario_id
        self.tipo = tipo
        self.staff_id = staff_id

    @discord.ui.button(label="Reivindicar", style=discord.ButtonStyle.success, emoji="🛡️", custom_id="btn_claim_perma")
    async def reivindicar(self, interaction: discord.Interaction, button: discord.ui.Button):
        ids_permitidos = IDS_PERMITIDOS_SUPORTE if self.tipo == "suporte" else IDS_ALTA_STAFF
        pode_reivindicar = interaction.user.id == ID_DONO_BOT or any(role.id in ids_permitidos for role in interaction.user.roles)

        if not pode_reivindicar:
            return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

        if not interaction.response.is_done():
            await interaction.response.defer()
            
        self.staff_id = interaction.user.id
        
        if self.tipo == "suporte":
            cargo_suporte = interaction.guild.get_role(ID_CARGO_SUPORTE)
            if cargo_suporte:
                await interaction.channel.set_permissions(cargo_suporte, view_channel=True, send_messages=False)
        else:
            cargo_sup = interaction.guild.get_role(ID_CARGO_SUPERVISOR)
            cargo_hmod = interaction.guild.get_role(ID_CARGO_HMOD)
            if cargo_sup:
                await interaction.channel.set_permissions(cargo_sup, view_channel=True, send_messages=False)
            if cargo_hmod:
                await interaction.channel.set_permissions(cargo_hmod, view_channel=True, send_messages=False)

        for id_imune in IDS_IMUNES_BLOQUEIO:
            cargo_imune = interaction.guild.get_role(id_imune)
            if cargo_imune:
                await interaction.channel.set_permissions(cargo_imune, view_channel=True, send_messages=True, attach_files=True)

        await interaction.channel.set_permissions(interaction.user, view_channel=True, send_messages=True, attach_files=True)
        
        asyncio.create_task(registrar_ticket_site({
            "action": "claim", "discord_channel_id": str(interaction.channel.id),
            "assigned_to": str(interaction.user.id), "assigned_username": interaction.user.name
        }))

        button.disabled = True
        button.label = "Reivindicado"
        await interaction.edit_original_response(view=self)
        await interaction.channel.send(f"🛡️ Atendimento iniciado por <@{interaction.user.id}>")

    @discord.ui.button(label="Unclaim", style=discord.ButtonStyle.secondary, emoji="🔄", custom_id="btn_unclaim_perma")
    async def unclaim(self, interaction: discord.Interaction, button: discord.ui.Button):
        pode_unclaim = (self.staff_id and interaction.user.id == self.staff_id) or \
                       interaction.user.id == ID_DONO_BOT or \
                       any(role.id in IDS_IMUNES_BLOQUEIO for role in interaction.user.roles)

        if not pode_unclaim:
            if not interaction.response.is_done():
                return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return

        if not interaction.response.is_done():
            await interaction.response.defer()
            
        self.staff_id = None

        if self.tipo == "suporte":
            cargo_suporte = interaction.guild.get_role(ID_CARGO_SUPORTE)
            if cargo_suporte:
                await interaction.channel.set_permissions(cargo_suporte, view_channel=True, send_messages=True)
        else:
            cargo_sup = interaction.guild.get_role(ID_CARGO_SUPERVISOR)
            cargo_hmod = interaction.guild.get_role(ID_CARGO_HMOD)
            if cargo_sup:
                await interaction.channel.set_permissions(cargo_sup, view_channel=True, send_messages=True)
            if cargo_hmod:
                await interaction.channel.set_permissions(cargo_hmod, view_channel=True, send_messages=True)

        for item in self.children:
            if item.custom_id == "btn_claim_perma":
                item.disabled = False
                item.label = "Reivindicar"
        
        await interaction.edit_original_response(view=self)
        await interaction.channel.send("🔄 A equipe agora pode interagir novamente")

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_close_perma")
    async def fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        pode_fechar = (self.staff_id and interaction.user.id == self.staff_id) or \
                      interaction.user.id == ID_DONO_BOT or \
                      any(role.id in IDS_IMUNES_BLOQUEIO for role in interaction.user.roles)

        if not pode_fechar:
            return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

        await interaction.response.send_message("🔒 Fechando canal e enviando avaliação para a DM")

        data_abertura = "N/A"
        if interaction.channel.topic and "Aberto: " in interaction.channel.topic:
            data_abertura = interaction.channel.topic.split("Aberto: ")[1]
        
        data_fechamento = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        autor_ticket = f"<@{self.usuario_id}>" if self.usuario_id else "Desconhecido"
        reivindicado_por = f"<@{self.staff_id}>" if self.staff_id else "Ninguém"

        mensagens = []
        async for msg in interaction.channel.history(limit=None, oldest_first=True):
            time_str = msg.created_at.strftime('%d/%m %H:%M')
            mensagens.append(f"[{time_str}] {msg.author}: {msg.content}")
        buffer = io.BytesIO("\n".join(mensagens).encode("utf-8"))

        log_canal = interaction.guild.get_channel(ID_CANAL_LOG_TICKETS)
        if log_canal:
            embed_log = discord.Embed(title="Ticket Fechado", color=COR_PLATFORM)
            embed_log.add_field(name="Nome do Ticket", value=f"`{interaction.channel.name}`", inline=True)
            embed_log.add_field(name="Autor do Ticket", value=autor_ticket, inline=True)
            embed_log.add_field(name="Fechado por", value=f"<@{interaction.user.id}>", inline=True)
            embed_log.add_field(name="Claimed By", value=reivindicado_por, inline=True)
            embed_log.add_field(name="Data de Abertura", value=data_abertura, inline=True)
            embed_log.add_field(name="Data de encerramento", value=data_fechamento, inline=True)
            
            file = discord.File(fp=buffer, filename=f"log-{interaction.channel.name}.txt")
            await log_canal.send(embed=embed_log, file=file)

        if self.usuario_id and self.staff_id:
            try:
                user = await interaction.client.fetch_user(self.usuario_id)
                e_dm = discord.Embed(title="Avalie nosso atendimento", description=f"Seu ticket em **{interaction.guild.name}** foi finalizado por <@{self.staff_id}>.\nComo você avalia o suporte recebido?", color=COR_PLATFORM)
                await user.send(embed=e_dm, view=AvaliacaoDMView(self.staff_id, interaction.channel.name, interaction.channel.id, self.usuario_id))
            except: pass

        registrar_stats_local(self.staff_id)
        await registrar_ticket_site({"action": "resolve", "discord_channel_id": str(interaction.channel.id)})
        await registrar_ticket_site({"action": "close", "discord_channel_id": str(interaction.channel.id)})

        await asyncio.sleep(2)
        await interaction.channel.delete()

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Suporte", style=discord.ButtonStyle.secondary, emoji="🛠️", custom_id="btn_suporte")
    async def suporte(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.criar_ticket(interaction, "suporte", ID_CARGO_SUPORTE, IDS_PERMITIDOS_SUPORTE)

    @discord.ui.button(label="Denúncia", style=discord.ButtonStyle.secondary, emoji="🚨", custom_id="btn_denuncia")
    async def denuncia(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.criar_ticket(interaction, "denuncia", ID_CARGO_SUPERVISOR, IDS_ALTA_STAFF)

    async def criar_ticket(self, interaction, tipo, cargo_ping_id, ids_visualizacao):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        categoria = guild.get_channel(ID_CATEGORIA_TICKETS)
        nome_canal = f"{tipo}-{interaction.user.name}".lower().replace(" ", "-")
        
        existente = discord.utils.get(guild.channels, name=nome_canal)
        if existente:
            return await interaction.followup.send(f"Você já tem um ticket em {existente.mention}", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        for id_cargo in ids_visualizacao:
            cargo = guild.get_role(id_cargo)
            if cargo:
                overwrites[cargo] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        canal = await guild.create_text_channel(
            name=nome_canal, 
            category=categoria, 
            overwrites=overwrites,
            topic=f"Dono: {interaction.user.id} | Tipo: {tipo} | Aberto: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        
        asyncio.create_task(registrar_ticket_site({
            "action": "open", "discord_channel_id": str(canal.id),
            "discord_user_id": str(interaction.user.id), "discord_username": interaction.user.name,
            "subject": f"Ticket de {tipo}", "priority": "medium"
        }))

        embed = discord.Embed(
            title=f"Atendimento - {tipo.upper()}", 
            description=f"Olá <@{interaction.user.id}>,\ndescreva seu problema para que nós possamos resolver o mais rápido possível.", 
            color=COR_PLATFORM
        )
        embed.set_image(url=BANNER_URL)
        
        await canal.send(content=f"<@&{cargo_ping_id}>", embed=embed, view=ReivindicarView(interaction.user.id, tipo))
        await interaction.followup.send(f"Ticket criado: {canal.mention}", ephemeral=True)

class ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="setup_ticket", description="Envia o painel de tickets")
    async def setup_ticket(self, ctx):
        tem_permissao = ctx.author.id == ID_DONO_BOT or any(role.id == ID_CARGO_SETUP for role in ctx.author.roles)
        if not tem_permissao:
            return await ctx.send("❌ Sem permissão.", ephemeral=True)

        embed = discord.Embed(
            title="Platform Destroyer | Tickets",
            description=(
                "Para redirecionarmos mais eficientemente o seu atendimento, siga estes parâmetros!\n\n"
                "**🛠️ Suporte:**\n"
                "• Destinado à tirar dúvidas e reportar erros nas scripts!\n\n"
                "**🚨 Denúncia:**\n"
                "• Destinado à denúncia de membros!\n\n"
                ""
                "Pedimos encarecidamente que não abram tickets com o intuito de brincadeiras.\n"
                "Sejam empáticos com o próximo."
            ),
            color=COR_PLATFORM
        )
        embed.set_image(url=BANNER_URL)
        await ctx.send(embed=embed, view=TicketView())

    @commands.hybrid_command(name="ticketstats", description="Vê as estatísticas de tickets de um staff")
    async def ticketstats(self, ctx, staff: discord.Member = None):
        staff = staff or ctx.author
        data = carregar_stats()
        sid = str(staff.id)

        if sid not in data:
            return await ctx.send(f"❌ <@{staff.id}> não possui estatísticas registradas.", ephemeral=True)

        s = data[sid]
        total = s.get("total", 0)
        hoje = s.get("hoje", 0)
        av_count = s.get("av_count", 0)
        soma = s.get("soma", 0)
        media = round(soma / av_count, 2) if av_count > 0 else 0
        primeiro = s.get("primeiro", "N/A")
        ultimo = s.get("ultimo", "N/A")

        embed = discord.Embed(title=f"Estatísticas de @{staff.name}", color=COR_PLATFORM)
        embed.set_thumbnail(url=staff.display_avatar.url)
        
        embed.add_field(name="<:Ticket:1385488194631499910> | Tickets Totais", value=f"{total}", inline=False)
        embed.add_field(name="<:Clock:1385489000248119476> | Tickets Hoje", value=f"{hoje}", inline=False)
        embed.add_field(name="<:Owner:1385488264789491782> | Avaliações Recebidas", value=f"{av_count}", inline=False)
        embed.add_field(name="<:School:1385488266928722022> | Média de Avaliações", value=f"{media}/5", inline=False)
        
        embed.add_field(name="<:g_arrow_PD:1384562807369895946> | Primeiro Ticket", value=f"{primeiro}", inline=False)
        embed.add_field(name="<:g_arrow_PD:1384562807369895946> | Último Ticket", value=f"{ultimo}", inline=False)
        
        embed.add_field(name="<:ticketa:1385848537618583713> Estatísticas Diárias", value=f"Total de tickets hoje: {hoje}", inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    bot.add_view(TicketView())
    bot.add_view(ReivindicarView())
    await bot.add_cog(ticket(bot))











