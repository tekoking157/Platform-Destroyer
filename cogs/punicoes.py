import discord
from discord import ui
from discord.ext import commands
import datetime
import re
import asyncio
import aiohttp
import json

# --- VIEW PARA O BOTÃO DE REMOVER PUNIÇÃO ---
class PunicaoView(ui.View):
    def __init__(self, cog, membro_id, acao):
        super().__init__(timeout=None)
        self.cog = cog
        self.membro_id = membro_id
        self.acao = acao.lower()

    @ui.button(label="Remover Punição", style=discord.ButtonStyle.danger, emoji="🔓")
    async def remover_punicao(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message("❌ Você não tem permissão para remover punições.", ephemeral=True)

        guild = interaction.guild
        try:
            membro = guild.get_member(self.membro_id) or await self.cog.bot.fetch_user(self.membro_id)
        except:
            return await interaction.response.send_message("❌ Usuário não encontrado.", ephemeral=True)
        
        try:
            if "ban" in self.acao:
                await guild.unban(membro, reason=f"Removido via botão por {interaction.user}")
                msg = f"✅ Banimento de {membro.name} removido."
            elif "mute" in self.acao:
                if isinstance(membro, discord.Member):
                    await membro.timeout(None, reason=f"Removido via botão por {interaction.user}")
                    cargo = guild.get_role(self.cog.ID_CARGO_MUTADO)
                    if cargo and cargo in membro.roles: await membro.remove_roles(cargo)
                msg = f"✅ Mute de {membro.mention} removido."
            elif "warn" in self.acao:
                self.cog.warns_cache[self.membro_id] = 0
                msg = f"✅ Avisos de {membro.mention} resetados."
            else:
                msg = "❌ Esta punição não pode ser revertida por este botão."

            button.disabled = True
            button.label = "Punição Removida"
            button.style = discord.ButtonStyle.secondary
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(msg, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao remover: {e}", ephemeral=True)

# --- CLASSE PRINCIPAL ---
class punicoes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ID_CANAL_LOGS = 1465118342422593707
        self.ID_CARGO_MUTADO = 1465048090624135351
        self.URL_SITE = 'https://otzrrxefahqeovfbonag.supabase.co/functions/v1/register-moderation'
        self.URL_STATS = 'https://otzrrxefahqeovfbonag.supabase.co/functions/v1/get-moderator-stats'
        self.URL_LOGS = 'https://otzrrxefahqeovfbonag.supabase.co/functions/v1/get-user-logs'
        self.COR_PLATFORM = discord.Color.from_rgb(47, 49, 54)
        self.warns_cache = {}
        self.USUARIOS_AUTORIZADOS = [1304003843172077659, 935566792384991303] 

    async def identificar_alvo(self, ctx, membro):
        if membro: return membro
        if ctx.message.reference:
            msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            return msg.author
        return None

    async def registrar_punicao_site(self, tipo, usuario, moderador, motivo):
        payload = {
            "action": tipo, 
            "discord_user_id": str(usuario.id),
            "discord_username": str(usuario),
            "applied_by_discord_id": str(moderador.id),
            "applied_by_username": str(moderador),
            "reason": motivo
        }
        headers = {"Content-Type": "application/json", "x-bot-token": str(self.bot.http.token)}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.URL_SITE, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        print(f"DEBUG: Falha ao registrar no site. Status: {resp.status}")
        except Exception as e: 
            print(f"DEBUG: Erro de conexão com Supabase: {e}")

    async def enviar_log(self, ctx, membro, acao, motivo, cor, duracao="não informado"):
        await self.registrar_punicao_site(acao.lower(), membro, ctx.author, motivo)
        canal = ctx.guild.get_channel(self.ID_CANAL_LOGS)
        if not canal: return

        embed = discord.Embed(title=f"| {acao.upper()}", color=cor, timestamp=datetime.datetime.now())
        embed.set_thumbnail(url=membro.display_avatar.url if hasattr(membro, 'display_avatar') else self.bot.user.display_avatar.url)
        
        embed.add_field(name="| usuário", value=f"{membro.mention}\n`{membro.id}`", inline=False)
        embed.add_field(name="| moderador", value=f"{ctx.author.mention}\n`{ctx.author.id}`", inline=False)
        
        if "muta" in acao.lower():
            embed.add_field(name="| duração", value=duracao, inline=False)
            
        embed.add_field(name="| motivo", value=motivo, inline=False)
        embed.add_field(name="| informações", value="executado via platform destroyer", inline=False)
        embed.set_footer(text=f"ID do Alvo: {membro.id}")
        
        view = PunicaoView(self, membro.id, acao)
        await canal.send(embed=embed, view=view)

    # --- COMANDOS DE ESTATÍSTICAS E HISTÓRICO ---

    @commands.hybrid_command(name="modstats", description="vê as estatísticas de um moderador")
    async def modstats(self, ctx, moderador: discord.Member = None):
        moderador = moderador or ctx.author
        headers = {"x-bot-token": str(self.bot.http.token)}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.URL_STATS}?moderator_id={moderador.id}", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embed = discord.Embed(title=f"📊 Estatísticas: {moderador.name}", color=self.COR_PLATFORM)
                    embed.add_field(name="Warns", value=f"`{data.get('warn', 0)}`", inline=True)
                    embed.add_field(name="Mutes", value=f"`{data.get('mute', 0)}`", inline=True)
                    embed.add_field(name="Bans", value=f"`{data.get('ban', 0)}`", inline=True)
                    embed.add_field(name="Kicks", value=f"`{data.get('kick', 0)}`", inline=True)
                    await ctx.send(embed=embed)
                else:
                    print(f"DEBUG: Erro na API (Stats). Status: {resp.status}")
                    print(f"Resposta: {await resp.text()}")
                    await ctx.send("❌ Não foi possível carregar as estatísticas.")

    @commands.hybrid_command(name="modlog", description="vê o histórico de punições de um usuário")
    async def modlog(self, ctx, usuario: discord.User = None):
        usuario = usuario or ctx.author
        headers = {"x-bot-token": str(self.bot.http.token)}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.URL_LOGS}?user_id={usuario.id}", headers=headers) as resp:
                if resp.status == 200:
                    logs = await resp.json()
                    if not logs: return await ctx.send(f"✅ Nenhum registro encontrado para {usuario.name}.")
                    
                    descricao = ""
                    for log in logs[:10]:
                        data = log.get('created_at', 'Desconhecido')[:10]
                        descricao += f"**{log['action'].upper()}** - {data}\nMotivo: *{log['reason']}*\n\n"
                    
                    embed = discord.Embed(title=f"📜 Histórico: {usuario.name}", description=descricao, color=self.COR_PLATFORM)
                    await ctx.send(embed=embed)
                else:
                    print(f"DEBUG: Erro na API (Logs). Status: {resp.status}")
                    await ctx.send("❌ Erro ao buscar histórico no banco de dados.")

    # --- COMANDOS DE PUNIÇÃO ---

    @commands.command(name="nuclearbomb")
    async def nuclearbomb(self, ctx, membro: discord.Member = None):
        if ctx.author.id not in self.USUARIOS_AUTORIZADOS: return
        alvo = await self.identificar_alvo(ctx, membro)
        if not alvo: return await ctx.send("❓ Alvo não encontrado.")
        try:
            await alvo.edit(roles=[], reason="Bomba Nuclear")
            await alvo.timeout(datetime.timedelta(hours=1), reason="Bomba Nuclear")
            await ctx.send(f"☢️ {alvo.mention} foi obliterado.") 
            await self.enviar_log(ctx, alvo, "NUCLEAR BOMB", "Lançamento autorizado", discord.Color.from_rgb(0,0,0), "1h")
        except: await ctx.send("❌ Erro de hierarquia.")

    @commands.hybrid_command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, membro: discord.Member = None, tempo: str = "10min", *, motivo: str = "não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return await ctx.send("Mencione alguém.")
        match = re.fullmatch(r"(\d+)(min|h|d)", tempo.lower())
        if match or tempo == "0":
            try:
                if tempo == "0":
                    cargo = ctx.guild.get_role(self.ID_CARGO_MUTADO)
                    await membro.add_roles(cargo)
                    await self.enviar_log(ctx, membro, "mute permanente", motivo, discord.Color.red(), "infinito")
                else:
                    qtd, uni = int(match.group(1)), match.group(2)
                    seg = qtd * {'d': 86400, 'h': 3600, 'min': 60}[uni]
                    await membro.timeout(datetime.timedelta(seconds=seg), reason=motivo)
                    await self.enviar_log(ctx, membro, "mute", motivo, discord.Color.red(), tempo)
                await ctx.send(f"✅ {membro.mention} foi silenciado.")
            except: await ctx.send("❌ Erro ao aplicar mute.")

    @commands.hybrid_command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, membro: discord.Member = None, *, motivo: str = "não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        try:
            await membro.timeout(None)
            cargo = ctx.guild.get_role(self.ID_CARGO_MUTADO)
            if cargo and cargo in membro.roles: await membro.remove_roles(cargo)
            await self.enviar_log(ctx, membro, "unmute", motivo, discord.Color.green())
            await ctx.send(f"✅ {membro.mention} desmutado.")
        except: pass

    @commands.hybrid_command(name="warn")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, membro: discord.Member = None, *, motivo: str = "não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return
        uid = membro.id
        self.warns_cache[uid] = self.warns_cache.get(uid, 0) + 1
        atual = self.warns_cache[uid]
        await self.enviar_log(ctx, membro, f"warn [{atual}/3]", motivo, discord.Color.orange())
        if atual >= 3:
            self.warns_cache[uid] = 0
            await membro.timeout(datetime.timedelta(hours=1))
            await ctx.send(f"🚨 {membro.mention} mutado (3 avisos).")
        else: await ctx.send(f"✅ {membro.mention} avisado ({atual}/3).")

    @commands.hybrid_command(name="unwarn")
    @commands.has_permissions(manage_messages=True)
    async def unwarn(self, ctx, membro: discord.Member = None):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return
        self.warns_cache[membro.id] = 0
        await self.enviar_log(ctx, membro, "unwarn", "Reset de avisos", discord.Color.green())
        await ctx.send(f"✅ Avisos de {membro.mention} resetados.")

    @commands.hybrid_command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, membro: discord.Member = None, *, motivo="não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        await self.enviar_log(ctx, membro, "kick", motivo, discord.Color.yellow())
        await membro.kick(reason=motivo)
        await ctx.send(f"✅ {membro.mention} expulso.")

    @commands.hybrid_command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, membro: discord.Member = None, *, motivo="não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        await self.enviar_log(ctx, membro, "ban", motivo, discord.Color.from_rgb(0, 0, 0))
        await membro.ban(reason=motivo)
        await ctx.send(f"✅ {membro.mention} banido.")

    @commands.hybrid_command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: str, *, motivo="não informado"):
        user = await self.bot.fetch_user(int(user_id))
        await ctx.guild.unban(user)
        await self.enviar_log(ctx, user, "unban", motivo, discord.Color.green())
        await ctx.send(f"✅ Usuário `{user.name}` desbanido.")

    @commands.hybrid_command(name="clear")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, quantidade: int):
        deleted = await ctx.channel.purge(limit=quantidade + 1)
        await ctx.send(f"✅ **{len(deleted)-1}** mensagens apagadas", delete_after=5)

async def setup(bot):
    await bot.add_cog(punicoes(bot))





