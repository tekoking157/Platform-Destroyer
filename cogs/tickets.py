import discord
from discord.ext import commands
import asyncio
import datetime
import io
import aiohttp

# CONFIGURAÇÕES (IDs Atualizados)
COR_PLATFORM = discord.Color.from_rgb(86, 3, 173)
BANNER_URL = "https://media.discordapp.net/attachments/1383636357745737801/1465105440789757972/bannerdestroyer.gif"
ID_CATEGORIA_TICKETS = 1357569803778392269
ID_CANAL_LOG_TICKETS = 1392528999623692460 # ID atualizado para seu canal de logs

# PERMISSÕES ESPECÍFICAS (IDs Atualizados)
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

        # Dar permissão de ver o canal para quem pode reivindicar e para a alta staff
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
            topic=f"Dono do Ticket: {interaction.user.id}"
        )
        
        await registrar_ticket_site({
            "action": "open", "discord_channel_id": str(canal.id),
            "discord_user_id": str(interaction.user.id), "discord_username": interaction.user.name,
            "subject": f"Ticket de {tipo}", "priority": "medium"
        })

        embed = discord.Embed(title=f"Atendimento - {tipo.upper()}", color=COR_PLATFORM)
        embed.description = f"Olá {interaction.user.mention}, descreva seu problema abaixo e aguarde um moderador."
        embed.set_image(url=BANNER_URL)
        
        view = ReivindicarView(usuario_id=interaction.user.id, tipo=tipo)
        await canal.send(embed=embed, view=view)
        await interaction.followup.send(f"Ticket criado: {canal.mention}", ephemeral=True)

class ReivindicarView(discord.ui.View):
    def __init__(self, usuario_id, tipo):
        super().__init__(timeout=None)
        self.usuario_id = usuario_id
        self.tipo = tipo

    @discord.ui.button(label="Reivindicar", style=discord.ButtonStyle.success, emoji="🛡️", custom_id="btn_claim")
    async def reivindicar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Apenas o cargo 1357569800938721349 ou Alta Staff pode reivindicar
        pode_reivindicar = interaction.user.id == ID_DONO_BOT or \
                           any(role.id == ID_CARGO_REIVINDICAR for role in interaction.user.roles) or \
                           any(role.id in IDS_ALTA_STAFF for role in interaction.user.roles)

        if not pode_reivindicar:
            return await interaction.response.send_message("❌ Você não tem permissão para reivindicar este ticket.", ephemeral=True)

        await interaction.response.defer()
        
        dono_id = self.usuario_id
        if not dono_id and interaction.channel.topic:
            try: dono_id = int(interaction.channel.topic.split(": ")[1])
            except: dono_id = 0

        await registrar_ticket_site({
            "action": "claim", "discord_channel_id": str(interaction.channel.id),
            "assigned_to": str(interaction.user.id), "assigned_username": interaction.user.name
        })

        view = FecharTicketView(staff_id=interaction.user.id, dono_ticket_id=dono_id)
        await interaction.message.delete()
        await interaction.channel.send(f"🛡️ Atendimento iniciado por {interaction.user.mention}", view=view)

class FecharTicketView(discord.ui.View):
    def __init__(self, staff_id, dono_ticket_id):
        super().__init__(timeout=None)
        self.staff_id = staff_id
        self.dono_ticket_id = dono_ticket_id

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_close")
    async def fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Pode fechar se: For quem reivindicou OU for da Alta Staff OU for o dono do bot
        es_alta_staff = any(role.id in IDS_ALTA_STAFF for role in interaction.user.roles)
        pode_fechar = interaction.user.id == self.staff_id or \
                      interaction.user.id == ID_DONO_BOT or \
                      es_alta_staff

        if not pode_fechar:
            return await interaction.response.send_message("❌ Você não tem permissão para fechar este ticket (apenas o responsável ou Alta Staff).", ephemeral=True)

        await interaction.response.send_message("Salvando logs e fechando em 5 segundos...")
        
        await registrar_ticket_site({"action": "resolve", "discord_channel_id": str(interaction.channel.id)})
        await registrar_ticket_site({"action": "close", "discord_channel_id": str(interaction.channel.id)})

        log_canal = interaction.guild.get_channel(ID_CANAL_LOG_TICKETS)
        mensagens = []
        async for msg in interaction.channel.history(limit=None, oldest_first=True):
            mensagens.append(f"[{msg.created_at.strftime('%H:%M')}] {msg.author}: {msg.content}")
        
        buffer = io.BytesIO("\n".join(mensagens).encode("utf-8"))
        if log_canal:
            await log_canal.send(f"📝 Log de ticket: `{interaction.channel.name}`", file=discord.File(fp=buffer, filename=f"log-{interaction.channel.name}.txt"))

        await asyncio.sleep(5)
        await interaction.channel.delete()

class ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="setup_ticket", description="Envia o painel de tickets")
    async def setup_ticket(self, ctx):
        # Apenas Dono ou Cargo de Setup
        tem_permissao = ctx.author.id == ID_DONO_BOT or any(role.id == ID_CARGO_SETUP for role in ctx.author.roles)
        if not tem_permissao:
            return await ctx.send("❌ Você não tem permissão para usar este comando.", ephemeral=True)

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
    await bot.add_cog(ticket(bot))
