import discord
from discord import ui
from discord.ext import commands
import datetime
import re
import asyncio

# --- CONFIGURAÇÃO DE SEGURANÇA ---
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
        if not ctx.guild: return False
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
        tem_cargo = any(role.id in IDS_STAFF_PERMITIDOS for role in interaction.user.roles)
        if not (tem_cargo or interaction.user.id in [1304003843172077659, 935566792384991303]):
            return await interaction.response.send_message("❌ Você não tem permissão para remover punições.", ephemeral=True)

        await interaction.response.defer()
        guild = interaction.guild
        try:
            membro = guild.get_member(self.membro_id) or await self.cog.bot.fetch_user(self.membro_id)
            if "ban" in self.acao:
                await guild.unban(membro)
                msg = f"✅ Banimento de {membro.name} removido."
            elif "mute" in self.acao:
                if isinstance(membro, discord.Member):
                    await membro.timeout(None)
                    cargo = guild.get_role(self.cog.ID_CARGO_MUTADO)
                    if cargo and cargo in membro.roles: await membro.remove_roles(cargo)
                msg = f"✅ Mute de {membro.mention} removido."
            elif "warn" in self.acao:
                self.cog.warns_cache[self.membro_id] = 0
                msg = f"✅ Avisos de {membro.mention} resetados."

            button.disabled = True
            button.label = "Punição Removida"
            await interaction.edit_original_response(view=self)
            await interaction.followup.send(msg)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao remover: {e}", ephemeral=True)

# --- CLASSE PRINCIPAL ---
class punicoes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ID_CANAL_LOGS = 1357569804273324285
        self.ID_CARGO_MUTADO = 1468077325215338719
        self.COR_PLATFORM = discord.Color.from_rgb(47, 49, 54)
        self.warns_cache = {}

    async def identificar_alvo(self, ctx, membro):
        if membro: return membro
        if ctx.message and ctx.message.reference:
            msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            return msg.author
        return None

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

    @commands.hybrid_command(name="modstats", description="Estatísticas detalhadas de um moderador")
    @check_staff()
    async def modstats(self, ctx, moderador: discord.Member = None):
        moderador = moderador or ctx.author
        await ctx.defer()

        canal_logs = ctx.guild.get_channel(self.ID_CANAL_LOGS)
        if not canal_logs: return await ctx.send("❌ Canal de logs não encontrado.")

        stats = {"WARN": 0, "MUTE": 0, "KICK": 0, "BAN": 0}
        agora = datetime.datetime.now(datetime.timezone.utc)
        hoje, semana, total_geral = 0, 0, 0

        async for message in canal_logs.history(limit=1000):
            if message.author == self.bot.user and message.embeds:
                embed_msg = message.embeds[0]
                if f"{moderador.id}" in str(embed_msg.to_dict()):
                    titulo = embed_msg.title.upper() if embed_msg.title else ""
                    for k in stats.keys():
                        if k in titulo: stats[k] += 1
                    delta = agora - message.created_at
                    if delta.days == 0: hoje += 1
                    if delta.days < 7: semana += 1
                    total_geral += 1

        embed = discord.Embed(title=f"📊 Estatísticas | {moderador.name}", color=self.COR_PLATFORM)
        embed.set_thumbnail(url=moderador.display_avatar.url)
        cat_txt = "\n".join([f"**{k}:** `{v}`" for k, v in stats.items()])
        embed.add_field(name="| categorias", value=cat_txt, inline=True)
        temp_txt = f"**Hoje:** `{hoje}`\n**7 dias:** `{semana}`\n**Total:** `{total_geral}`"
        embed.add_field(name="| período", value=temp_txt, inline=True)
        embed.set_footer(text=f"Total de {total_geral} ações registradas.")
        await ctx.send(embed=embed)

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
                    logs.append(f"**Tipo:** {acao}\n**Mod:** {mod}\n**Data:** {data}\n**Motivo:** {motivo}\n━━━━━━━━━━━━━━")
        if not logs: return await ctx.send(f"✅ Nenhum registro para {usuario.name}.")
        embed = discord.Embed(title=f"📜 Histórico de {usuario.name}", description="\n".join(logs[:5]), color=self.COR_PLATFORM)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="mute", description="Silencia um membro")
    @check_staff()
    async def mute(self, ctx, membro: discord.Member = None, tempo: str = "10min", *, motivo: str = "não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return await ctx.send("Mencione alguém.")
        
        try:
            if tempo == "0":
                cargo = ctx.guild.get_role(self.ID_CARGO_MUTADO)
                if not cargo: return await ctx.send("❌ Cargo mutado não configurado.")
                await membro.add_roles(cargo)
                await self.enviar_log(ctx, membro, "mute permanente", motivo, discord.Color.red(), "infinito")
            else:
                match = re.fullmatch(r"(\d+)(min|h|d)", tempo.lower())
                if not match: return await ctx.send("❌ Tempo inválido (Ex: 10min, 1h, 0).")
                qtd, uni = int(match.group(1)), match.group(2)
                seg = qtd * {'d': 86400, 'h': 3600, 'min': 60}[uni]
                await membro.timeout(datetime.timedelta(seconds=seg), reason=motivo)
                await self.enviar_log(ctx, membro, "mute", motivo, discord.Color.red(), tempo)
            await ctx.send(f"✅ {membro.mention} silenciado.")
        except discord.Forbidden:
            await ctx.send("❌ Erro de permissão: Verifique se meu cargo está acima do alvo.")

    @commands.hybrid_command(name="unmute", description="Desmuta um membro")
    @check_staff()
    async def unmute(self, ctx, membro: discord.Member = None, *, motivo: str = "não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return
        try:
            await membro.timeout(None)
            cargo = ctx.guild.get_role(self.ID_CARGO_MUTADO)
            if cargo and cargo in membro.roles: await membro.remove_roles(cargo)
            await self.enviar_log(ctx, membro, "unmute", motivo, discord.Color.green())
            await ctx.send(f"✅ {membro.mention} desmutado.")
        except:
            await ctx.send("❌ Não consegui remover o mute.")

    @commands.hybrid_command(name="warn", description="Aplica um aviso")
    @check_staff()
    async def warn(self, ctx, membro: discord.Member = None, *, motivo: str = "não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return
        self.warns_cache[membro.id] = self.warns_cache.get(membro.id, 0) + 1
        atual = self.warns_cache[membro.id]
        await self.enviar_log(ctx, membro, f"warn [{atual}/3]", motivo, discord.Color.orange())
        if atual >= 3:
            self.warns_cache[membro.id] = 0
            await membro.timeout(datetime.timedelta(hours=1))
            await ctx.send(f"🚨 {membro.mention} mutado (atingiu 3 avisos).")
        else: await ctx.send(f"✅ {membro.mention} avisado ({atual}/3).")

    @commands.hybrid_command(name="unwarn", description="Reseta avisos")
    @check_staff()
    async def unwarn(self, ctx, membro: discord.Member = None):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return
        self.warns_cache[membro.id] = 0
        await self.enviar_log(ctx, membro, "unwarn", "Reset de avisos", discord.Color.green())
        await ctx.send(f"✅ Avisos de {membro.mention} resetados.")

    @commands.hybrid_command(name="kick", description="Expulsa um membro")
    @check_staff()
    async def kick(self, ctx, membro: discord.Member = None, *, motivo="não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return
        try:
            await self.enviar_log(ctx, membro, "kick", motivo, discord.Color.yellow())
            await membro.kick(reason=motivo)
            await ctx.send(f"✅ {membro.mention} expulso.")
        except:
            await ctx.send("❌ Erro ao expulsar.")

    @commands.hybrid_command(name="ban", description="Bane um membro")
    @check_staff()
    async def ban(self, ctx, membro: discord.Member = None, *, motivo="não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return
        try:
            await self.enviar_log(ctx, membro, "ban", motivo, discord.Color.from_rgb(0, 0, 0))
            await membro.ban(reason=motivo)
            await ctx.send(f"✅ {membro.mention} banido.")
        except:
            await ctx.send("❌ Erro ao banir.")

    @commands.hybrid_command(name="unban", description="Desbane pelo ID")
    @check_staff()
    async def unban(self, ctx, user_id: str, *, motivo="não informado"):
        try:
            user = await self.bot.fetch_user(int(user_id))
            await ctx.guild.unban(user)
            await self.enviar_log(ctx, user, "unban", motivo, discord.Color.green())
            await ctx.send(f"✅ `{user.name}` desbanido.")
        except:
            await ctx.send("❌ ID inválido ou usuário não banido.")

    @commands.hybrid_command(name="clear", description="Limpa o chat")
    @check_staff()
    async def clear(self, ctx, quantidade: int):
        if quantidade <= 0: return await ctx.send("❌ Use números positivos.")
        if ctx.interaction: await ctx.defer(ephemeral=True)
        
        try:
            limite = quantidade if ctx.interaction else quantidade + 1
            deleted = await ctx.channel.purge(limit=limite)
            res = f"✅ **{len(deleted) if ctx.interaction else len(deleted)-1}** mensagens apagadas."
            
            if ctx.interaction: await ctx.interaction.followup.send(res)
            else: await ctx.send(res, delete_after=5)
        except:
            await ctx.send("❌ Erro ao limpar mensagens.")

async def setup(bot):
    await bot.add_cog(punicoes(bot))



