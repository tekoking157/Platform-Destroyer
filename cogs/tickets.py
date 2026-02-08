import discord
from discord.ext import commands
import asyncio
import datetime
import io
import aiohttp

COR_PLATFORM = discord.Color.from_rgb(86, 3, 173)
BANNER_URL = "https://media.discordapp.net/attachments/1383636357745737801/1465105440789757972/bannerdestroyer.gif"
ID_CATEGORIA_TICKETS = 1357569803778392269
ID_CANAL_LOG_TICKETS = 1392528999623692460 

ID_DONO_BOT = 1304003843172077659
ID_CARGO_SETUP = 1357569800947237000

ID_CARGO_SUPORTE = 1357569800938721349
ID_CARGO_HMOD = 1431475496377389177
ID_CARGO_SUPERVISOR = 1414283452878028800
ID_CARGO_ADM = 1357569800947236998
ID_CARGO_CM = 1414283694662750268
ID_CARGO_MANAGER = 1357569800947237000

IDS_ALTA_STAFF = [ID_CARGO_HMOD, ID_CARGO_SUPERVISOR, ID_CARGO_ADM, ID_CARGO_CM, ID_CARGO_MANAGER]
IDS_PERMITIDOS_SUPORTE = [ID_CARGO_SUPORTE, ID_CARGO_ADM, ID_CARGO_CM, ID_CARGO_MANAGER]

TICKET_ENDPOINT = "https://otzrrxefahqeovfbonag.supabase.co/functions/v1/register-ticket"

async def registrar_ticket_site(payload):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(TICKET_ENDPOINT, json=payload, timeout=10) as response:
                return response.status
    except: return None

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
            return await interaction.response.send_message("❌ Você não tem permissão para reivindicar este ticket.", ephemeral=True)

        await interaction.response.defer()
        
        self.staff_id = interaction.user.id
        await interaction.channel.set_permissions(interaction.user, view_channel=True, send_messages=True, attach_files=True)

        await registrar_ticket_site({
            "action": "claim", "discord_channel_id": str(interaction.channel.id),
            "assigned_to": str(interaction.user.id), "assigned_username": interaction.user.name
        })

        button.disabled = True
        button.label = "Reivindicado"
        await interaction.edit_original_response(view=self)
        await interaction.channel.send(f"🛡️ Atendimento iniciado por {interaction.user.mention}")

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_close_perma")
    async def fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        ids_permitidos = IDS_PERMITIDOS_SUPORTE if self.tipo == "suporte" else IDS_ALTA_STAFF
        pode_fechar = (self.staff_id and interaction.user.id == self.staff_id) or \
                      interaction.user.id == ID_DONO_BOT or \
                      any(role.id in ids_permitidos for role in interaction.user.roles)

        if not pode_fechar:
            return await interaction.response.send_message("❌ Você não tem permissão para fechar este ticket.", ephemeral=True)

        await interaction.response.send_message("💾 Salvando logs e fechando em 5 segundos...")
        
        data_abertura = "N/A"
        if interaction.channel.topic and "Aberto: " in interaction.channel.topic:
            data_abertura = interaction.channel.topic.split("Aberto: ")[1]
        
        data_fechamento = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        autor_ticket = f"<@{self.usuario_id}>" if self.usuario_id else "Desconhecido"
        reivindicado_por = f"<@{self.staff_id}>" if self.staff_id else "Ninguém"
        
        log_canal = interaction.guild.get_channel(ID_CANAL_LOG_TICKETS)
        mensagens = []
        async for msg in interaction.channel.history(limit=None, oldest_first=True):
            time_str = msg.created_at.strftime('%d/%m %H:%M')
            mensagens.append(f"[{time_str}] {msg.author}: {msg.content}")
        
        buffer = io.BytesIO("\n".join(mensagens).encode("utf-8"))
        
        if log_canal:
            embed_log = discord.Embed(title="Ticket Fechado", color=COR_PLATFORM)
            embed_log.add_field(name="Nome do Ticket", value=f"`{interaction.channel.name}`", inline=True)
            embed_log.add_field(name="Autor do Ticket", value=autor_ticket, inline=True)
            embed_log.add_field(name="Fechado por", value=interaction.user.mention, inline=True)
            embed_log.add_field(name="Claimed By", value=reivindicado_por, inline=True)
            embed_log.add_field(name="Data de Abertura", value=data_abertura, inline=True)
            embed_log.add_field(name="Data de encerramento", value=data_fechamento, inline=True)
            embed_log.add_field(name="Motivo para fechar o Ticket", value="No Reason Provided", inline=False)
            
            file = discord.File(fp=buffer, filename=f"log-{interaction.channel.name}.txt")
            await log_canal.send(embed=embed_log, file=file)

        await registrar_ticket_site({"action": "resolve", "discord_channel_id": str(interaction.channel.id)})
        await registrar_ticket_site({"action": "close", "discord_channel_id": str(interaction.channel.id)})

        await asyncio.sleep(5)
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
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        categoria = guild.get_channel(ID_CATEGORIA_TICKETS)
        nome_canal = f"{tipo}-{interaction.user.name}".lower().replace(" ", "-")
        
        existente = discord.utils.get(guild.channels, name=nome_canal)
        if existente:
            return await interaction.followup.send(f"Você já tem um ticket em {existente.mention}.", ephemeral=True)

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
        
        await registrar_ticket_site({
            "action": "open", "discord_channel_id": str(canal.id),
            "discord_user_id": str(interaction.user.id), "discord_username": interaction.user.name,
            "subject": f"Ticket de {tipo}", "priority": "medium"
        })

        embed = discord.Embed(
            title=f"Atendimento - {tipo.upper()}", 
            description=f"Olá {interaction.user.mention},\ndescreva seu problema para que nós possamos resolver o mais rápido possível.", 
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
            return await ctx.send("❌ Você não tem permissão.", ephemeral=True)

        embed = discord.Embed(
            title="Platform Destroyer | Tickets",
            description=(
                "Para redirecionarmos mais eficientemente o seu atendimento, siga estes parâmetros!\n\n"
                "**🛠️ Suporte:**\n"
                "• Destinado à tirar dúvidas e reportar erros nas scripts!\n\n"
                "**🚨 Denúncia:**\n"
                "• Destinado à denúncia de membros!\n\n"
                "Pedimos encarecidamente que não abram tickets com o intuito de brincadeiras.\n"
                "Sejam empáticos com o próximo."
            ),
            color=COR_PLATFORM
        )
        embed.set_image(url=BANNER_URL)
        await ctx.send(embed=embed, view=TicketView())

async def setup(bot):
    bot.add_view(TicketView())
    bot.add_view(ReivindicarView())
    await bot.add_cog(ticket(bot))
    



