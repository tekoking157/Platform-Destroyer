import discord
from discord import ui
from discord.ext import commands
import datetime
import re
import asyncio

IDS_STAFF_PERMITIDOS = [
    1357569800938721350,
    1431475496377389177,
    1414283452878028800,
    1414283694662750268,
    1357569800947237000
]
IDS_STAFF_LIMITADO = [1463174855904989428] 
USUARIOS_SUPREMOS = [1304003843172077659, 935566792384991303]

def check_staff():
    async def predicate(ctx):
        if not ctx.guild: return False
        todos_permitidos = IDS_STAFF_PERMITIDOS + IDS_STAFF_LIMITADO
        tem_cargo = any(role.id in todos_permitidos for role in ctx.author.roles)
        if ctx.author.id in USUARIOS_SUPREMOS or tem_cargo:
            return True
        await ctx.send("❌ Você não tem permissão para usar este comando.", ephemeral=True)
        return False
    return commands.check(predicate)

def check_pode_banir():
    async def predicate(ctx):
        if ctx.author.id in USUARIOS_SUPREMOS: return True
        tem_staff_full = any(role.id in IDS_STAFF_PERMITIDOS for role in ctx.author.roles)
        if tem_staff_full: return True
        await ctx.send("❌ Seu cargo não tem permissão para banir ou desbanir usuários.", ephemeral=True)
        return False
    return commands.check(predicate)

class PunicaoView(ui.View):
    def __init__(self, cog, membro_id, acao):
        super().__init__(timeout=None)
        self.cog = cog
        self.membro_id = membro_id
        self.acao = acao.lower()

    @ui.button(label="Remover Punição", style=discord.ButtonStyle.danger, emoji="🔓")
    async def remover_punicao(self, interaction: discord.Interaction, button: ui.Button):
        tem_cargo = any(role.id in IDS_STAFF_PERMITIDOS for role in interaction.user.roles)
        if not (tem_cargo or interaction.user.id in USUARIOS_SUPREMOS):
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

class ModlogsPagination(ui.View):
    def __init__(self, pages, current_page=0):
        super().__init__(timeout=60)
        self.pages = pages
        self.current_page = current_page

    @ui.button(emoji="<:back:1336829707269701763>", style=discord.ButtonStyle.gray)
    async def previous(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @ui.button(emoji="<:next:1336829709232771143>", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

class punicoes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ID_CANAL_LOGS = 1357569804273324285
        self.ID_CARGO_MUTADO = 1468077325215338719
        self.COR_PLATFORM = discord.Color.from_rgb(86, 3, 173)
        self.warns_cache = {}

    async def identificar_alvo(self, ctx, membro):
        if membro: return membro
        if ctx.message and ctx.message.reference:
            msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            return msg.author
        return None

    async def checar_hierarquia(self, ctx, membro: discord.Member):
        if not isinstance(membro, discord.Member): return True
        if ctx.author.id == ctx.guild.owner_id: return True
        if membro.id == self.bot.user.id: return False
        if membro.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            await ctx.send(f"❌ Você não pode punir {membro.mention} (cargo igual ou superior).")
            return False
        if membro.top_role >= ctx.guild.me.top_role:
            await ctx.send(f"❌ Eu não posso punir {membro.mention} (cargo superior ao meu).")
            return False
        return True

    async def enviar_log(self, ctx, membro, acao, motivo, cor, duracao="não informado"):
        canal = ctx.guild.get_channel(self.ID_CANAL_LOGS)
        if not canal: return
        
        embed = discord.Embed(title=f"| {acao.upper()}", color=cor, timestamp=datetime.datetime.now())
        embed.add_field(name="| usuário", value=f"{membro.mention}\n`{membro.id}`", inline=False)
        embed.add_field(name="| moderador", value=f"{ctx.author.mention}\n`{ctx.author.id}`", inline=False)
        if "muta" in acao.lower(): embed.add_field(name="| duração", value=duracao, inline=False)
        embed.add_field(name="| motivo", value=motivo, inline=False)
        embed.set_footer(text=f"ID do Alvo: {membro.id}")
        
        view_enviar = None
        if not acao.lower().startswith("un"):
            view_enviar = PunicaoView(self, membro.id, acao)
            
        await canal.send(embed=embed, view=view_enviar)

    @commands.hybrid_command(name="modstats", description="Estatísticas detalhadas de um moderador")
    @check_staff()
    async def modstats(self, ctx, moderador: discord.Member = None):
        moderador = moderador or ctx.author
        await ctx.defer()
        canal_logs = ctx.guild.get_channel(self.ID_CANAL_LOGS)
        
        stats = {"WARN": {"hoje": 0, "semana": 0, "total": 0}, 
                 "MUTE": {"hoje": 0, "semana": 0, "total": 0}, 
                 "KICK": {"hoje": 0, "semana": 0, "total": 0}, 
                 "BAN":  {"hoje": 0, "semana": 0, "total": 0}}
        
        total_acumulado = 0
        agora = datetime.datetime.now(datetime.timezone.utc)

        async for message in canal_logs.history(limit=1000):
            if message.author == self.bot.user and message.embeds:
                embed = message.embeds[0]
                content = str(embed.to_dict())
                if f"{moderador.id}" in content and "| moderador" in content:
                    titulo = embed.title.upper() if embed.title else ""
                    delta = agora - message.created_at
                    for tipo in stats.keys():
                        if tipo in titulo:
                            stats[tipo]["total"] += 1
                            if delta.days == 0: stats[tipo]["hoje"] += 1
                            if delta.days < 7: stats[tipo]["semana"] += 1
                    total_acumulado += 1

        embed = discord.Embed(title=f"📊 Estatísticas | {moderador.name}", color=self.COR_PLATFORM)
        embed.description = f"punições de {moderador.mention}"
        embed.set_thumbnail(url=moderador.display_avatar.url)

        for tipo, valores in stats.items():
            txt = f"Hoje: **{valores['hoje']}**\nSemana: **{valores['semana']}**\nTotal: **{valores['total']}**"
            embed.add_field(name=tipo, value=txt, inline=True)

        embed.add_field(name="📈 TOTAL ACUMULADO", value=f"O moderador possui **{total_acumulado}** punições.", inline=False)
        embed.set_footer(text="Pesquisa realizada nas últimas 1000 mensagens de logs.")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="modlogs", description="Verifica o histórico de punições de um usuário")
    @check_staff()
    async def modlogs(self, ctx, usuario: discord.User):
        await ctx.defer()
        canal_logs = ctx.guild.get_channel(self.ID_CANAL_LOGS)
        punicoes_encontradas = []

        async for message in canal_logs.history(limit=1000):
            if message.author == self.bot.user and message.embeds:
                embed = message.embeds[0]
                content = str(embed.to_dict())
                if f"{usuario.id}" in content and "| usuário" in content:
                    info = {
                        "tipo": embed.title.replace("| ", "").capitalize() if embed.title else "Ação Desconhecida",
                        "moderador": "Desconhecido",
                        "motivo": "Motivo não informado",
                        "data": message.created_at
                    }
                    for field in embed.fields:
                        if "| moderador" in field.name.lower(): info["moderador"] = field.value.split("\n")[0]
                        if "| motivo" in field.name.lower(): info["motivo"] = field.value
                    punicoes_encontradas.append(info)

        if not punicoes_encontradas:
            return await ctx.send(f"✅ Nenhuma punição encontrada para {usuario.mention}.")

        paginas = []
        punicoes_por_pagina = 2
        for i in range(0, len(punicoes_encontradas), punicoes_por_pagina):
            chunk = punicoes_encontradas[i:i + punicoes_por_pagina]
            embed = discord.Embed(title=f"Histórico de Punições de {usuario.name} — Página {len(paginas)+1}", color=discord.Color.from_rgb(231, 76, 60))
            embed.set_thumbnail(url=usuario.display_avatar.url)
            
            for p in chunk:
                timestamp = int(p["data"].timestamp())
                txt = f"**Tipo:** {p['tipo']}\n**Punido por:** {p['moderador']}\n**Punido em:** <t:{timestamp}:d> às <t:{timestamp}:t> (há <t:{timestamp}:R>)\n**Motivo:** {p['motivo']}"
                embed.add_field(name="\u200b", value=txt, inline=False)
            
            embed.set_footer(text=f"Total de punições: {len(punicoes_encontradas)}")
            paginas.append(embed)

        view = ModlogsPagination(paginas) if len(paginas) > 1 else None
        await ctx.send(embed=paginas[0], view=view)

    @commands.hybrid_command(name="mute", description="Silencia um membro")
    @check_staff()
    async def mute(self, ctx, membro: discord.Member = None, tempo: str = "10min", *, motivo: str = "não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return await ctx.send("❓ Mencione alguém ou responda a uma mensagem.")
        if not await self.checar_hierarquia(ctx, membro): return
        if ctx.interaction: await ctx.defer()
        
        try:
            if tempo == "0":
                cargo = ctx.guild.get_role(self.ID_CARGO_MUTADO)
                if not cargo: return await ctx.send("❌ Cargo mutado não configurado.")
                await membro.add_roles(cargo)
                await self.enviar_log(ctx, membro, "mute permanente", motivo, discord.Color.red(), "infinito")
                await ctx.send(f"✅ {membro.mention} mutado **permanente**.\n**Motivo:** {motivo}")
            else:
                match = re.fullmatch(r"(\d+)(min|h|d)", tempo.lower())
                if not match: return await ctx.send("❌ Tempo inválido (Ex: 10min, 1h, 0).")
                qtd, uni = int(match.group(1)), match.group(2)
                seg = qtd * {'d': 86400, 'h': 3600, 'min': 60}[uni]
                await membro.timeout(datetime.timedelta(seconds=seg), reason=motivo)
                await self.enviar_log(ctx, membro, "mute", motivo, discord.Color.red(), tempo)
                await ctx.send(f"✅ {membro.mention} silenciado por **{tempo}**.\n**Motivo:** {motivo}")
        except:
            await ctx.send("❌ Erro de permissão: Verifique meu cargo.")

    @commands.hybrid_command(name="unmute", description="Remove silenciamento")
    @check_staff()
    async def unmute(self, ctx, membro: discord.Member = None, *, motivo: str = "não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return
        try:
            await membro.timeout(None)
            cargo = ctx.guild.get_role(self.ID_CARGO_MUTADO)
            if cargo and cargo in membro.roles: await membro.remove_roles(cargo)
            await self.enviar_log(ctx, membro, "unmute", motivo, discord.Color.green())
            await ctx.send(f"✅ {membro.mention} desmutado.\n**Motivo:** {motivo}")
        except:
            await ctx.send("❌ Erro ao desmutar.")

    @commands.hybrid_command(name="warn", description="Aplica um aviso")
    @check_staff()
    async def warn(self, ctx, membro: discord.Member = None, *, motivo: str = "não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return
        if not await self.checar_hierarquia(ctx, membro): return
        self.warns_cache[membro.id] = self.warns_cache.get(membro.id, 0) + 1
        atual = self.warns_cache[membro.id]
        await self.enviar_log(ctx, membro, f"warn [{atual}/3]", motivo, discord.Color.orange())
        if atual >= 3:
            self.warns_cache[membro.id] = 0
            await membro.timeout(datetime.timedelta(hours=1))
            await ctx.send(f"🚨 {membro.mention} mutado por 1h (3 avisos).\n**Motivo:** {motivo}")
        else:
            await ctx.send(f"✅ {membro.mention} avisado ({atual}/3).\n**Motivo:** {motivo}")

    @commands.hybrid_command(name="unwarn", description="Remove os avisos de um membro")
    @check_staff()
    async def unwarn(self, ctx, membro: discord.Member = None, *, motivo: str = "não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return await ctx.send("❓ Mencione alguém ou responda a uma mensagem.")
        self.warns_cache[membro.id] = 0
        await self.enviar_log(ctx, membro, "unwarn", motivo, discord.Color.green())
        await ctx.send(f"✅ Avisos de {membro.mention} foram resetados.\n**Motivo:** {motivo}")

    @commands.hybrid_command(name="kick", description="Expulsa um membro")
    @check_staff()
    async def kick(self, ctx, membro: discord.Member = None, *, motivo="não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return
        if not await self.checar_hierarquia(ctx, membro): return
        await self.enviar_log(ctx, membro, "kick", motivo, discord.Color.yellow())
        await membro.kick(reason=motivo)
        await ctx.send(f"✅ {membro.mention} expulso.\n**Motivo:** {motivo}")

    @commands.hybrid_command(name="ban", description="Bane um membro")
    @check_staff()
    @check_pode_banir()
    async def ban(self, ctx, membro: discord.Member = None, *, motivo="não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return
        if not await self.checar_hierarquia(ctx, membro): return
        await self.enviar_log(ctx, membro, "ban", motivo, discord.Color.from_rgb(0, 0, 0))
        await membro.ban(reason=motivo, delete_message_days=1)
        await ctx.send(f"✅ {membro.mention} banido.\n**Motivo:** {motivo}")

    @commands.hybrid_command(name="ipban", description="Bane IP e limpa mensagens")
    @check_staff()
    @check_pode_banir()
    async def ipban(self, ctx, membro: discord.Member = None, *, motivo="não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return
        if not await self.checar_hierarquia(ctx, membro): return
        await self.enviar_log(ctx, membro, "IP BAN (7D)", motivo, discord.Color.dark_red())
        await membro.ban(reason=f"IP BAN: {motivo}", delete_message_days=7)
        await ctx.send(f"🚫 {membro.mention} banido por IP (7 dias de limpeza).\n**Motivo:** {motivo}")

    @commands.hybrid_command(name="unban", description="Desbane pelo ID")
    @check_staff()
    @check_pode_banir()
    async def unban(self, ctx, user_id: str, *, motivo="não informado"):
        user = await self.bot.fetch_user(int(user_id))
        await ctx.guild.unban(user)
        await self.enviar_log(ctx, user, "unban", motivo, discord.Color.green())
        await ctx.send(f"✅ `{user.name}` desbanido.\n**Motivo:** {motivo}")

    @commands.hybrid_command(name="clear", description="Limpa o chat")
    @check_staff()
    async def clear(self, ctx, quantidade: int):
        if quantidade <= 0: return await ctx.send("❌ Use números positivos.")
        if ctx.interaction: await ctx.defer(ephemeral=True)
        deleted = await ctx.channel.purge(limit=quantidade if ctx.interaction else quantidade + 1)
        res = f"✅ **{len(deleted) if ctx.interaction else len(deleted)-1}** mensagens apagadas."
        if ctx.interaction: await ctx.interaction.followup.send(res)
        else: await ctx.send(res, delete_after=5)

async def setup(bot):
    await bot.add_cog(punicoes(bot))






