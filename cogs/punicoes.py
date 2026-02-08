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
    1357569800947236998
]
IDS_STAFF_LIMITADO = [1463174855904989428] 
USUARIOS_SUPREMOS = [1304003843172077659, 935566792384991303]
DONOS_NUCLEAR = [1304003843172077659, 1291064098741555273]

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
            if any(x in self.acao for x in ["ban", "ipban"]):
                await guild.unban(membro)
                msg = f"✅ Banimento de {membro.name} removido."
            elif any(x in self.acao for x in ["mute", "nuclear"]):
                if isinstance(membro, discord.Member):
                    await membro.timeout(None)
                    cargo = guild.get_role(self.cog.ID_CARGO_MUTADO)
                    if cargo and cargo in membro.roles: await membro.remove_roles(cargo)
                msg = f"✅ Punição de {membro.mention} removida."
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
        else:
            await interaction.response.defer()

    @ui.button(emoji="<:next:1336829709232771143>", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
        else:
            await interaction.response.defer()

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

    async def avisar_usuario(self, membro, acao, motivo, guild_name):
        try:
            embed = discord.Embed(title=f"⚠️ Você foi punido!", color=discord.Color.red())
            embed.add_field(name="Servidor", value=guild_name, inline=False)
            embed.add_field(name="Ação", value=acao.upper(), inline=False)
            embed.add_field(name="Motivo", value=motivo, inline=False)
            await membro.send(embed=embed)
        except:
            pass

    async def enviar_log(self, ctx, membro, acao, motivo, cor, duracao="não informado"):
        canal = ctx.guild.get_channel(self.ID_CANAL_LOGS)
        if not canal: return
        
        embed = discord.Embed(title=f"| {acao.upper()}", color=cor, timestamp=datetime.datetime.now())
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.add_field(name="| usuário", value=f"{membro.mention}\n`{membro.id}`", inline=False)
        embed.add_field(name="| moderador", value=f"{ctx.author.mention}\n`{ctx.author.id}`", inline=False)
        if any(x in acao.lower() for x in ["muta", "nuclear"]): embed.add_field(name="| duração", value=duracao, inline=False)
        embed.add_field(name="| motivo", value=motivo, inline=False)
        embed.set_footer(text=f"ID do Alvo: {membro.id}")
        
        view_enviar = None
        if not acao.lower().startswith("un"):
            view_enviar = PunicaoView(self, membro.id, acao)
            
        await canal.send(embed=embed, view=view_enviar)

    @commands.hybrid_command(name="nuclearbomb", description="Expurga um membro do servidor")
    async def nuclearbomb(self, ctx, membro: discord.Member = None):
        if ctx.author.id not in DONOS_NUCLEAR:
            return await ctx.send("❌ Você não tem autoridade para usar a Bomba Nuclear.", ephemeral=True)
            
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return await ctx.send("❓ Quem você deseja expurgar!")
        if not await self.checar_hierarquia(ctx, membro): return
        
        motivo = "Expurgado via Nuclear Bomb"
        
        try:
            await membro.edit(roles=[])
            await membro.timeout(datetime.timedelta(minutes=15), reason=motivo)
            await self.avisar_usuario(membro, "NUCLEAR BOMB", motivo, ctx.guild.name)
            await self.enviar_log(ctx, membro, "NUCLEAR BOMB", motivo, discord.Color.dark_red(), "15 minutos")
            await ctx.send(f"{membro.mention} foi expurgado.")
        except Exception as e:
            await ctx.send(f"❌ Falha na sequência: {e}")

    @commands.hybrid_command(name="modstats", description="Estatísticas detalhadas de um moderador")
    @check_staff()
    async def modstats(self, ctx, moderador: discord.Member = None):
        moderador = moderador or ctx.author
        await ctx.defer()
        canal_logs = ctx.guild.get_channel(self.ID_CANAL_LOGS)
        
        stats = {"WARN": {"hoje": 0, "semana": 0, "total": 0}, 
                 "MUTE": {"hoje": 0, "semana": 0, "total": 0}, 
                 "KICK": {"hoje": 0, "semana": 0, "total": 0}, 
                 "BAN":  {"hoje": 0, "semana": 0, "total": 0},
                 "IPBAN": {"hoje": 0, "semana": 0, "total": 0}}
        
        total_acumulado = 0
        agora = datetime.datetime.now(datetime.timezone.utc)

        async for message in canal_logs.history(limit=500):
            if message.author == self.bot.user and message.embeds:
                embed = message.embeds[0]
                if f"{moderador.id}" in str(embed.to_dict()):
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
        embed.set_footer(text="Pesquisa realizada nos logs recentes.")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="modlogs", description="Verifica o histórico de punições de um usuário")
    @check_staff()
    async def modlogs(self, ctx, usuario: discord.User):
        await ctx.defer()
        canal_logs = ctx.guild.get_channel(self.ID_CANAL_LOGS)
        if not canal_logs: return await ctx.send("❓ Canal de logs não encontrado.")
        
        punicoes_encontradas = []
        user_id_str = str(usuario.id)

        async for message in canal_logs.history(limit=400):
            if message.author == self.bot.user and message.embeds:
                embed = message.embeds[0]
                encontrou = False
                if embed.description and user_id_str in embed.description: encontrou = True
                else:
                    for field in embed.fields:
                        if user_id_str in field.value:
                            encontrou = True
                            break
                
                if encontrou:
                    info = {
                        "tipo": embed.title.replace("| ", "").capitalize() if embed.title else "Punição",
                        "moderador": "Desconhecido",
                        "motivo": "Não informado",
                        "data": message.created_at
                    }
                    for field in embed.fields:
                        fn = field.name.lower()
                        if "moderador" in fn: info["moderador"] = field.value.split("\n")[0]
                        if "motivo" in fn: info["motivo"] = field.value
                    punicoes_encontradas.append(info)

        if not punicoes_encontradas:
            return await ctx.send(f"✅ Nenhuma punição recente para {usuario.mention}.")

        paginas = []
        for i in range(0, len(punicoes_encontradas), 2):
            chunk = punicoes_encontradas[i:i + 2]
            emb = discord.Embed(title=f"Histórico de {usuario.name}", color=self.COR_PLATFORM)
            emb.set_thumbnail(url=usuario.display_avatar.url)
            for p in chunk:
                ts = int(p["data"].timestamp())
                txt = f"**Tipo:** {p['tipo']}\n**Moderador:** {p['moderador']}\n**Data:** <t:{ts}:d>\n**Motivo:** {p['motivo']}"
                emb.add_field(name="──────────────", value=txt, inline=False)
            emb.set_footer(text=f"❓ Página {len(paginas)+1} | Total: {len(punicoes_encontradas)}")
            paginas.append(emb)

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
            await self.avisar_usuario(membro, "mute", motivo, ctx.guild.name)
            if tempo == "0":
                cargo = ctx.guild.get_role(self.ID_CARGO_MUTADO)
                if not cargo: return await ctx.send("❌ Cargo mutado não configurado.")
                await membro.add_roles(cargo)
                await self.enviar_log(ctx, membro, "mute permanente", motivo, discord.Color.red(), "infinito")
                await ctx.send(f"✅ {membro.mention} mutado **permanente**.\n**Motivo:** {motivo}")
            else:
                match = re.fullmatch(r"(\d+)(min|h|d)", tempo.lower())
                if match:
                    qtd, uni = int(match.group(1)), match.group(2)
                    seg = qtd * {'d': 86400, 'h': 3600, 'min': 60}[uni]
                    await membro.timeout(datetime.timedelta(seconds=seg), reason=motivo)
                    await self.enviar_log(ctx, membro, "mute", motivo, discord.Color.red(), tempo)
                    await ctx.send(f"✅ {membro.mention} silenciado por **{tempo}**.\n**Motivo:** {motivo}")
        except:
            await ctx.send("❌ Erro de permissão.")

    @commands.hybrid_command(name="unmute", description="Remove silenciamento")
    @check_staff()
    async def unmute(self, ctx, membro: discord.Member = None, *, motivo: str = "não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return await ctx.send("❓ Mencione alguém ou responda a uma mensagem.")
        try:
            await membro.timeout(None)
            cargo = ctx.guild.get_role(self.ID_CARGO_MUTADO)
            if cargo and cargo in membro.roles: await membro.remove_roles(cargo)
            await self.enviar_log(ctx, membro, "unmute", motivo, discord.Color.green())
            await ctx.send(f"✅ {membro.mention} desmutado.")
        except:
            await ctx.send("❌ Erro ao desmutar.")

    @commands.hybrid_command(name="warn", description="Aplica um aviso")
    @check_staff()
    async def warn(self, ctx, membro: discord.Member = None, *, motivo: str = "não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return await ctx.send("❓ Mencione alguém ou responda a uma mensagem.")
        if not await self.checar_hierarquia(ctx, membro): return
        self.warns_cache[membro.id] = self.warns_cache.get(membro.id, 0) + 1
        atual = self.warns_cache[membro.id]
        await self.avisar_usuario(membro, f"warn [{atual}/3]", motivo, ctx.guild.name)
        await self.enviar_log(ctx, membro, f"warn [{atual}/3]", motivo, discord.Color.orange())
        if atual >= 3:
            self.warns_cache[membro.id] = 0
            await membro.timeout(datetime.timedelta(hours=1))
            await ctx.send(f"🚨 {membro.mention} mutado por 1h (3 avisos).")
        else:
            await ctx.send(f"✅ {membro.mention} avisado ({atual}/3).")

    @commands.hybrid_command(name="unwarn", description="Remove os avisos de um membro")
    @check_staff()
    async def unwarn(self, ctx, membro: discord.Member = None, *, motivo: str = "não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return await ctx.send("❓ Mencione alguém ou responda a uma mensagem.")
        self.warns_cache[membro.id] = 0
        await self.enviar_log(ctx, membro, "unwarn", motivo, discord.Color.green())
        await ctx.send(f"✅ Avisos de {membro.mention} resetados.")

    @commands.hybrid_command(name="kick", description="Expulsa um membro")
    @check_staff()
    async def kick(self, ctx, membro: discord.Member = None, *, motivo="não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return await ctx.send("❓ Mencione alguém ou responda a uma mensagem.")
        if not await self.checar_hierarquia(ctx, membro): return
        await self.avisar_usuario(membro, "kick", motivo, ctx.guild.name)
        await self.enviar_log(ctx, membro, "kick", motivo, discord.Color.yellow())
        await membro.kick(reason=motivo)
        await ctx.send(f"✅ {membro.mention} expulso.")

    @commands.hybrid_command(name="ban", description="Bane um membro")
    @check_staff()
    @check_pode_banir()
    async def ban(self, ctx, membro: discord.Member = None, *, motivo="não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return await ctx.send("❓ Mencione alguém ou responda a uma mensagem.")
        if not await self.checar_hierarquia(ctx, membro): return
        await self.avisar_usuario(membro, "ban", motivo, ctx.guild.name)
        await self.enviar_log(ctx, membro, "ban", motivo, discord.Color.from_rgb(0, 0, 0))
        await membro.ban(reason=motivo, delete_message_days=1)
        await ctx.send(f"✅ {membro.mention} banido.")

    @commands.hybrid_command(name="ipban", description="Bane um membro e seu endereço IP")
    @check_staff()
    @check_pode_banir()
    async def ipban(self, ctx, membro: discord.Member = None, *, motivo="não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return await ctx.send("❓ Mencione alguém ou responda a uma mensagem.")
        if not await self.checar_hierarquia(ctx, membro): return
        await self.avisar_usuario(membro, "ipban", motivo, ctx.guild.name)
        await self.enviar_log(ctx, membro, "ipban", motivo, discord.Color.from_rgb(20, 20, 20))
        await membro.ban(reason=f"IPBAN: {motivo}", delete_message_days=7)
        await ctx.send(f"🚫 {membro.mention} foi banido por IP.")

    @commands.hybrid_command(name="unban", description="Desbane pelo ID")
    @check_staff()
    @check_pode_banir()
    async def unban(self, ctx, user_id: str, *, motivo="não informado"):
        user = await self.bot.fetch_user(int(user_id))
        await ctx.guild.unban(user)
        await self.enviar_log(ctx, user, "unban", motivo, discord.Color.green())
        await ctx.send(f"✅ `{user.name}` desbanido.")

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







