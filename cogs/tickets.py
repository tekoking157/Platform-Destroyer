import discord
from discord import app_commands
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

STATS_FILE = "stats.json"

def carregar_stats():
    if not os.path.exists(STATS_FILE):
        return {}
    with open(STATS_FILE, "r") as f:
        return json.load(f)

def salvar_stats(data):
    with open(STATS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def registrar_stats_local(staff_id, nota=None):
    data = carregar_stats()
    sid = str(staff_id)
    hoje = datetime.datetime.now().strftime("%Y-%m-%d")
    if sid not in data:
        data[sid] = {"total": 0, "hoje": 0, "av_count": 0, "soma": 0, "data": hoje}
    if data[sid]["data"] != hoje:
        data[sid]["hoje"] = 0
        data[sid]["data"] = hoje
    data[sid]["total"] += 1
    data[sid]["hoje"] += 1
    if nota:
        data[sid]["av_count"] += 1
        data[sid]["soma"] += int(nota)
    salvar_stats(data)

class AvaliacaoModal(discord.ui.Modal, title="Avaliação do Atendimento"):
    nota = discord.ui.TextInput(label="Nota (1 a 5)", placeholder="5", min_length=1, max_length=1)
    comentario = discord.ui.TextInput(label="Comentário", style=discord.TextStyle.paragraph)

    def __init__(self, view_orig):
        super().__init__()
        self.view_orig = view_orig

    async def on_submit(self, interaction: discord.Interaction):
        if not self.nota.value.isdigit() or not (1 <= int(self.nota.value) <= 5):
            return await interaction.response.send_message("❌ Nota de 1 a 5.", ephemeral=True)
        registrar_stats_local(self.view_orig.staff_id, self.nota.value)
        await interaction.response.send_message("✅ Avaliado com sucesso.")
        await self.view_orig.fechar_final(interaction)

class ReivindicarView(discord.ui.View):
    def __init__(self, usuario_id=None, tipo=None, staff_id=None):
        super().__init__(timeout=None)
        self.usuario_id = usuario_id
        self.tipo = tipo
        self.staff_id = staff_id

    @discord.ui.button(label="Reivindicar", style=discord.ButtonStyle.success, emoji="🛡️", custom_id="btn_claim_perma")
    async def reivindicar(self, interaction: discord.Interaction, button: discord.ui.Button):
        perms = IDS_PERMITIDOS_SUPORTE if self.tipo == "suporte" else IDS_ALTA_STAFF
        if not (interaction.user.id == ID_DONO_BOT or any(r.id in perms for r in interaction.user.roles)):
            return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
        await interaction.response.defer()
        self.staff_id = interaction.user.id
        if self.tipo == "suporte":
            c = interaction.guild.get_role(ID_CARGO_SUPORTE)
            if c: await interaction.channel.set_permissions(c, view_channel=True, send_messages=False)
        else:
            s, h = interaction.guild.get_role(ID_CARGO_SUPERVISOR), interaction.guild.get_role(ID_CARGO_HMOD)
            if s: await interaction.channel.set_permissions(s, view_channel=True, send_messages=False)
            if h: await interaction.channel.set_permissions(h, view_channel=True, send_messages=False)
        for i in IDS_IMUNES_BLOQUEIO:
            ci = interaction.guild.get_role(i)
            if ci: await interaction.channel.set_permissions(ci, view_channel=True, send_messages=True)
        await interaction.channel.set_permissions(interaction.user, view_channel=True, send_messages=True)
        button.disabled, button.label = True, "Reivindicado"
        await interaction.edit_original_response(view=self)
        await interaction.channel.send(f"🛡️ Atendimento por {interaction.user.mention}")

    @discord.ui.button(label="Unclaim", style=discord.ButtonStyle.secondary, emoji="🔄", custom_id="btn_unclaim_perma")
    async def unclaim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not (self.staff_id == interaction.user.id or interaction.user.id == ID_DONO_BOT or any(r.id in IDS_IMUNES_BLOQUEIO for r in interaction.user.roles)):
            return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
        await interaction.response.defer()
        self.staff_id = None
        if self.tipo == "suporte":
            c = interaction.guild.get_role(ID_CARGO_SUPORTE)
            if c: await interaction.channel.set_permissions(c, view_channel=True, send_messages=True)
        else:
            s, h = interaction.guild.get_role(ID_CARGO_SUPERVISOR), interaction.guild.get_role(ID_CARGO_HMOD)
            if s: await interaction.channel.set_permissions(s, view_channel=True, send_messages=True)
            if h: await interaction.channel.set_permissions(h, view_channel=True, send_messages=True)
        for i in self.children:
            if i.custom_id == "btn_claim_perma":
                i.disabled, i.label = False, "Reivindicar"
        await interaction.edit_original_response(view=self)

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_close_perma")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not (self.staff_id == interaction.user.id or interaction.user.id == ID_DONO_BOT or any(r.id in IDS_IMUNES_BLOQUEIO for r in interaction.user.roles)):
            return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
        if interaction.user.id == self.staff_id:
            button.disabled, button.label = True, "Aguardando Membro"
            await interaction.response.edit_message(view=self)
            await interaction.channel.send(f"✅ Suporte finalizado. <@{self.usuario_id}>, avalie para fechar.", view=MembroView(self))
        else:
            await self.fechar_final(interaction)

    async def fechar_final(self, interaction):
        msgs = []
        async for m in interaction.channel.history(limit=None, oldest_first=True):
            msgs.append(f"[{m.created_at.strftime('%d/%m %H:%M')}] {m.author}: {m.content}")
        buf = io.BytesIO("\n".join(msgs).encode("utf-8"))
        l = interaction.guild.get_channel(ID_CANAL_LOG_TICKETS)
        if l:
            e = discord.Embed(title="Ticket Fechado", color=COR_PLATFORM)
            e.add_field(name="Autor", value=f"<@{self.usuario_id}>")
            e.add_field(name="Staff", value=f"<@{self.staff_id}>")
            await l.send(embed=e, file=discord.File(fp=buf, filename="log.txt"))
        await asyncio.sleep(2)
        await interaction.channel.delete()

class MembroView(discord.ui.View):
    def __init__(self, v):
        super().__init__(timeout=None)
        self.v = v
    @discord.ui.button(label="Avaliar e Fechar", style=discord.ButtonStyle.danger, emoji="⭐")
    async def av(self, interaction: discord.Interaction, b: discord.ui.Button):
        if interaction.user.id != self.v.usuario_id:
            return await interaction.response.send_message("❌ Apenas o dono.", ephemeral=True)
        await interaction.response.send_modal(AvaliacaoModal(self.v))

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Suporte", style=discord.ButtonStyle.secondary, emoji="🛠️", custom_id="btn_suporte")
    async def sup(self, interaction: discord.Interaction, b: discord.ui.Button):
        await self.ct(interaction, "suporte", ID_CARGO_SUPORTE, IDS_PERMITIDOS_SUPORTE)
    @discord.ui.button(label="Denúncia", style=discord.ButtonStyle.secondary, emoji="🚨", custom_id="btn_denuncia")
    async def den(self, interaction: discord.Interaction, b: discord.ui.Button):
        await self.ct(interaction, "denuncia", ID_CARGO_SUPERVISOR, IDS_ALTA_STAFF)
    async def ct(self, interaction, t, cp, iv):
        await interaction.response.defer(ephemeral=True)
        n = f"{t}-{interaction.user.name}".lower()
        ow = {interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False), interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True), interaction.guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True)}
        for cid in iv:
            c = interaction.guild.get_role(cid)
            if c: ow[c] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        can = await interaction.guild.create_text_channel(name=n, category=interaction.guild.get_channel(ID_CATEGORIA_TICKETS), overwrites=ow)
        await can.send(content=f"<@&{cp}>", embed=discord.Embed(title=f"Atendimento - {t.upper()}", color=COR_PLATFORM), view=ReivindicarView(interaction.user.id, t))
        await interaction.followup.send(f"Canal: {can.mention}", ephemeral=True)

class ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @commands.hybrid_command(name="setup_ticket")
    async def setup_ticket(self, ctx):
        if not (ctx.author.id == ID_DONO_BOT or any(r.id == ID_CARGO_SETUP for r in ctx.author.roles)):
            return await ctx.send("❌ Sem permissão.")
        e = discord.Embed(title="Platform Destroyer | Tickets", color=COR_PLATFORM)
        e.set_image(url=BANNER_URL)
        await ctx.send(embed=e, view=TicketView())
    @app_commands.command(name="ticket", description="Estatísticas")
    async def ts(self, interaction: discord.Interaction, membro: discord.Member):
        d = carregar_stats().get(str(membro.id), {"total":0,"hoje":0,"av_count":0,"soma":0})
        m = d["soma"]/d["av_count"] if d["av_count"] > 0 else 0
        e = discord.Embed(title=f"Estatísticas de @{membro.name}", color=COR_PLATFORM)
        e.set_thumbnail(url=membro.display_avatar.url)
        e.add_field(name="🎫 Tickets Totais", value=str(d["total"]), inline=False)
        e.add_field(name="🕒 Tickets Hoje", value=str(d["hoje"]), inline=False)
        e.add_field(name="⭐ Avaliações", value=str(d["av_count"]), inline=False)
        e.add_field(name="🎓 Média", value=f"{m:.2f}/5", inline=False)
        await interaction.response.send_message(embed=e)

async def setup(bot):
    bot.add_view(TicketView())
    bot.add_view(ReivindicarView())
    await bot.add_cog(ticket(bot))







