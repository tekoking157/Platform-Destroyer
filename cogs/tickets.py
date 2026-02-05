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
ID_CARGO_REIVINDICAR = 1357569800938721349
IDS_ALTA_STAFF = [1357569800947236998, 1414283694662750268, 1357569800947237000]

TICKET_ENDPOINT = "https://otzrrxefahqeovfbonag.supabase.co/functions/v1/register-ticket"

async def registrar_ticket_site(payload):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(TICKET_ENDPOINT, json=payload, timeout=10) as response:
                return response.status
    except: return None

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Suporte", style=discord.ButtonStyle.secondary, emoji="🛠️", custom_id="btn_suporte")
    async def suporte(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.criar_ticket(interaction, "suporte")

    @discord.ui.button(label="Denúncia", style=discord.ButtonStyle.secondary, emoji="🚨", custom_id="btn_denuncia")
    async def denuncia(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.criar_ticket(interaction, "denuncia")

    async def criar_ticket(self, interaction, tipo):
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

        cargo_suporte = guild.get_role(ID_CARGO_REIVINDICAR)
        if cargo_suporte:
            overwrites[cargo_suporte] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        
        for id_staff in IDS_ALTA_STAFF:
            cargo_alta = guild.get_role(id_staff)
            if cargo_alta:
                overwrites[cargo_alta] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        canal = await guild.create_text_channel(
            name=nome_canal, 
            category=categoria, 
            overwrites=overwrites,
            topic=f"Dono: {interaction.user.id} | Tipo: {tipo}"
        )
        
        await registrar_ticket_site({
            "action": "open", "discord_channel_id": str(canal.id),
            "discord_user_id": str(interaction.user.id), "discord_username": interaction.user.name,
            "subject": f"Ticket de {tipo}", "priority": "medium"
        })

        embed = discord.Embed(title=f"Atendimento - {tipo.upper()}", color=COR_PLATFORM)
        embed.description = f"Olá {interaction.user.mention}, descreva seu problema abaixo e aguarde um moderador."
        embed.set_image(url=BANNER_URL)
        
        await canal.send(embed=embed, view=ReivindicarView(interaction.user.id))
        await interaction.followup.send(f"Ticket criado: {canal.mention}", ephemeral=True)

class ReivindicarView(discord.ui.View):
    def __init__(self, usuario_id=None):
        super().__init__(timeout=None)
        self.usuario_id = usuario_id

    @discord.ui.button(label="Reivindicar", style=discord.ButtonStyle.success, emoji="🛡️", custom_id="btn_claim_perma")
    async def reivindicar(self, interaction: discord.Interaction, button: discord.ui.Button):
        pode_reivindicar = interaction.user.id == ID_DONO_BOT or \
                           any(role.id == ID_CARGO_REIVINDICAR for role in interaction.user.roles) or \
                           any(role.id in IDS_ALTA_STAFF for role in interaction.user.roles)

        if not pode_reivindicar:
            return await interaction.response.send_message("❌ Você não tem permissão para reivindicar.", ephemeral=True)

        await interaction.response.defer()
        
        dono_id = self.usuario_id
        if not dono_id and interaction.channel.topic:
            try: dono_id = int(interaction.channel.topic.split("|")[0].split(": ")[1])
            except: dono_id = 0

        await registrar_ticket_site({
            "action": "claim", "discord_channel_id": str(interaction.channel.id),
            "assigned_to": str(interaction.user.id), "assigned_username": interaction.user.name
        })

        view = FecharTicketView(interaction.user.id)
        await interaction.message.delete()
        await interaction.channel.send(f"🛡️ Atendimento iniciado por {interaction.user.mention}", view=view)

class FecharTicketView(discord.ui.View):
    def __init__(self, staff_id=None):
        super().__init__(timeout=None)
        self.staff_id = staff_id

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_close_perma")
    async def fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        es_alta_staff = any(role.id in IDS_ALTA_STAFF for role in interaction.user.roles)
        pode_fechar = interaction.user.id == self.staff_id or \
                      interaction.user.id == ID_DONO_BOT or \
                      es_alta_staff

        if not pode_fechar:
            return await interaction.response.send_message("❌ Apenas o responsável ou Alta Staff podem fechar.", ephemeral=True)

        await interaction.response.send_message("💾 Salvando logs e fechando em 5 segundos...")
        
        await registrar_ticket_site({"action": "resolve", "discord_channel_id": str(interaction.channel.id)})
        await registrar_ticket_site({"action": "close", "discord_channel_id": str(interaction.channel.id)})

        log_canal = interaction.guild.get_channel(ID_CANAL_LOG_TICKETS)
        mensagens = []
        async for msg in interaction.channel.history(limit=None, oldest_first=True):
            mensagens.append(f"[{msg.created_at.strftime('%d/%m %H:%M')}] {msg.author}: {msg.content}")
        
        buffer = io.BytesIO("\n".join(mensagens).encode("utf-8"))
        if log_canal:
            await log_canal.send(
                f"📝 **Log de Ticket**\nCanal: `{interaction.channel.name}`\nFechado por: {interaction.user.mention}", 
                file=discord.File(fp=buffer, filename=f"log-{interaction.channel.name}.txt")
            )

        await asyncio.sleep(5)
        await interaction.channel.delete()

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
    bot.add_view(FecharTicketView())
    await bot.add_cog(ticket(bot))

