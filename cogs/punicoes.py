import discord
from discord import ui
from discord.ext import commands
import datetime
import re
import asyncio

# --- CONFIGURAÇÃO DE SEGURANÇA (IDs fornecidos por você) ---
IDS_STAFF_PERMITIDOS = [
    1357569800938721350,
    1431475496377389177,
    1414283452878028800,
    1414283694662750268,
    1357569800947237000
]

def check_staff():
    async def predicate(ctx):
        USUARIOS_AUTORIZADOS = [1304003843172077659, 935566792384991303]
        tem_cargo = any(role.id in IDS_STAFF_PERMITIDOS for role in ctx.author.roles)
        if ctx.author.id in USUARIOS_AUTORIZADOS or tem_cargo:
            return True
        await ctx.send("❌ Você não tem permissão para usar este comando.", ephemeral=True)
        return False
    return commands.check(predicate)

# --- VIEW PARA O BOTÃO DE REMOVER PUNIÇÃO ---
class PunicaoView(ui.View):
    def __init__(self, cog, membro_id, acao):
        super().__init__(timeout=None)
        self.cog = cog
        self.membro_id = membro_id
        self.acao = acao.lower()

    @ui.button(label="Remover Punição", style=discord.ButtonStyle.danger, emoji="🔓")
    async def remover_punicao(self, interaction: discord.Interaction, button: ui.Button):
        tem_permissao = any(role.id in IDS_STAFF_PERMITIDOS for role in interaction.user.roles)
        if not tem_permissao:
            return await interaction.response.send_message("❌ Apenas staff pode remover punições.", ephemeral=True)

        guild = interaction.guild
        try:
            membro = guild.get_member(self.membro_id) or await self.cog.bot.fetch_user(self.membro_id)
            if "ban" in self.acao:
                await guild.unban(membro)
            elif "mute" in self.acao:
                if isinstance(membro, discord.Member):
                    await membro.timeout(None)
            elif "warn" in self.acao:
                self.cog.warns_cache[self.membro_id] = 0
            
            button.disabled = True
            button.label = "Removida"
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(f"✅ Punição de {membro.name} removida.", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Erro ao remover.", ephemeral=True)

class punicoes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ID_CANAL_LOGS = 1465118342422593707
        self.ID_CARGO_MUTADO = 1465048090624135351
        self.COR_PLATFORM = discord.Color.from_rgb(47, 49, 54)
        self.warns_cache = {}

    async def enviar_log(self, ctx, membro, acao, motivo, cor, duracao="não informado"):
        canal = ctx.guild.get_channel(self.ID_CANAL_LOGS)
        if not canal: return
        embed = discord.Embed(title=f"| {acao.upper()}", color=cor, timestamp=datetime.datetime.now())
        embed.add_field(name="| usuário", value=f"{membro.mention}\n`{membro.id}`", inline=False)
        embed.add_field(name="| moderador", value=f"{ctx.author.mention}\n`{ctx.author.id}`", inline=False)
        if "muta" in acao.lower(): embed.add_field(name="| duração", value=duracao, inline=False)
        embed.add_field(name="| motivo", value=motivo, inline=False)
        embed.set_footer(text=f"ID do Alvo: {membro.id}")
        await canal.send(embed=embed, view=PunicaoView(self, membro.id, acao))

    # --- COMANDO MODSTATS (COM FILTRO DE TEMPO) ---
    @commands.hybrid_command(name="modstats", description="Estatísticas da staff")
    @check_staff()
    async def modstats(self, ctx, moderador: discord.Member = None):
        moderador = moderador or ctx.author
        await ctx.defer()
        canal_logs = ctx.guild.get_channel(self.ID_CANAL_LOGS)
        
        stats = {"WARN": 0, "MUTE": 0, "KICK": 0, "BAN": 0}
        agora = datetime.datetime.now(datetime.timezone.utc)
        hoje, semana, total = 0, 0, 0

        async for message in canal_logs.history(limit=1000):
            if message.author == self.bot.user and message.embeds:
                embed = message.embeds[0]
                if f"{moderador.id}" in str(embed.to_dict()):
                    titulo = embed.title.upper() if embed.title else ""
                    for k in stats.keys():
                        if k in titulo: stats[k] += 1
                    
                    delta = agora - message.created_at
                    if delta.days == 0: hoje += 1
                    if delta.days < 7: semana += 1
                    total += 1

        embed = discord.Embed(title=f"📊 Estatísticas | {moderador.name}", color=self.COR_PLATFORM)
        embed.set_thumbnail(url=moderador.display_avatar.url)
        
        # Organização por Categoria
        cat_txt = "\n".join([f"**{k}:** `{v}`" for k, v in stats.items()])
        embed.add_field(name="🛡️ Por Categoria", value=cat_txt, inline=True)
        
        # Organização por Tempo
        temp_txt = f"**Hoje:** `{hoje}`\n**7 dias:** `{semana}`\n**Total:** `{total}`"
        embed.add_field(name="📅 Período (Logs)", value=temp_txt, inline=True)
        
        await ctx.send(embed=embed)

    # --- COMANDO MODLOG (ESTILO LISTA LORITTA) ---
    @commands.hybrid_command(name="modlog", description="Ver histórico de um usuário")
    @check_staff()
    async def modlog(self, ctx, usuario: discord.User = None):
        usuario = usuario or ctx.author
        await ctx.defer()
        canal_logs = ctx.guild.get_channel(self.ID_CANAL_LOGS)

        logs = []
        async for message in canal_logs.history(limit=1000):
            if message.author == self.bot.user and message.embeds:
                embed = message.embeds[0]
                if f"{usuario.id}" in str(embed.to_dict()) and "ID do Alvo" in str(embed.footer.text):
                    acao = embed.title.replace("| ", "").title()
                    mod = "Desconhecido"
                    motivo = "Não informado"
                    for f in embed.fields:
                        if "moderador" in f.name: mod = f.value.split('\n')[0]
                        if "motivo" in f.name: motivo = f.value
                    
                    data = message.created_at.strftime("%d/%m/%Y às %H:%M")
                    logs.append(f"**Tipo:** {acao}\n**Moderador:** {mod}\n**Data:** {data}\n**Motivo:** {motivo}\n━━━━━━━━━━━━━━")

        if not logs: return await ctx.send(f"✅ Nenhum registro para {usuario.name}.")

        embed = discord.Embed(title=f"📜 Histórico de {usuario.name}", description="\n".join(logs[:5]), color=self.COR_PLATFORM)
        embed.set_footer(text=f"Total encontrado: {len(logs)} registros.")
        await ctx.send(embed=embed)

    # --- COMANDOS DE PUNIÇÃO (RESUMIDOS PARA O CHAT) ---
    @commands.hybrid_command(name="warn")
    @check_staff()
    async def warn(self, ctx, membro: discord.Member, *, motivo="Não informado"):
        self.warns_cache[membro.id] = self.warns_cache.get(membro.id, 0) + 1
        await self.enviar_log(ctx, membro, f"warn [{self.warns_cache[membro.id]}/3]", motivo, discord.Color.orange())
        await ctx.send(f"✅ {membro.mention} avisado.")

    @commands.hybrid_command(name="mute")
    @check_staff()
    async def mute(self, ctx, membro: discord.Member, tempo="10min", *, motivo="Não informado"):
        # Lógica de tempo e mute...
        await self.enviar_log(ctx, membro, "mute", motivo, discord.Color.red(), tempo)
        await ctx.send(f"✅ {membro.mention} mutado.")

    @commands.hybrid_command(name="ban")
    @check_staff()
    async def ban(self, ctx, membro: discord.Member, *, motivo="Não informado"):
        await membro.ban(reason=motivo)
        await self.enviar_log(ctx, membro, "ban", motivo, discord.Color.black())
        await ctx.send(f"✅ {membro.mention} banido.")

async def setup(bot):
    await bot.add_cog(punicoes(bot))



