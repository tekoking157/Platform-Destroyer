import discord
from discord.ext import commands
import datetime
import re
import asyncio
import aiohttp

class punicoes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ID_CANAL_LOGS = 1465118342422593707
        self.ID_CARGO_MUTADO = 1465048090624135351
        self.URL_SITE = 'https://otzrrxefahqeovfbonag.supabase.co/functions/v1/register-moderation'
        self.COR_PLATFORM = discord.Color.from_rgb(47, 49, 54)
        self.warns_cache = {}
        self.USUARIOS_AUTORIZADOS = [1304003843172077659, 935566792384991303] 

    async def identificar_alvo(self, ctx, membro):
        if membro:
            return membro
        if ctx.message.reference:
            msg_referenciada = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            return msg_referenciada.author
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
        # Corrigido: Usando a variável de ambiente para o token se necessário ou o token do bot
        headers = {"Content-Type": "application/json", "x-bot-token": str(self.bot.http.token)}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.URL_SITE, json=payload, headers=headers) as response:
                    if response.status in [200, 201]:
                        print(f"Log enviado ao site: {usuario.name}")
        except Exception as e:
            print(f"Falha ao conectar com o site: {e}")

    async def enviar_log(self, ctx, membro, acao, motivo, cor, duracao="não informado"):
        tipo_site = acao.lower()
        if "aviso" in tipo_site: tipo_site = "warn"
        elif "mute" in tipo_site: tipo_site = "mute"
        elif "expuls" in tipo_site: tipo_site = "kick"
        elif "ban" in tipo_site: tipo_site = "ban"
        elif "unban" in tipo_site: tipo_site = "unban"
        
        await self.registrar_punicao_site(tipo_site, membro, ctx.author, motivo)
        canal = ctx.guild.get_channel(self.ID_CANAL_LOGS)
        if not canal: return

        # ALTERAÇÃO: Título agora contém o nome do usuário e removemos o campo separado
        titulo = f"| {acao.upper()} - {membro}"
        embed = discord.Embed(title=titulo, color=cor, timestamp=datetime.datetime.now())
        
        avatar_url = membro.display_avatar.url if hasattr(membro, 'display_avatar') else self.bot.user.display_avatar.url
        embed.set_thumbnail(url=avatar_url)
        
        # Campo de usuário removido conforme solicitado, ID movido para o rodapé
        embed.add_field(name="| moderador", value=f"{ctx.author.mention}\n`{ctx.author.id}`", inline=False)
        if "muta" in acao.lower():
            embed.add_field(name="| duração", value=duracao, inline=False)
        embed.add_field(name="| motivo", value=motivo, inline=False)
        embed.add_field(name="| informações", value="executado via platform destroyer", inline=False)
        embed.set_footer(text=f"ID do Usuário: {membro.id}")
        await canal.send(embed=embed)

    async def avisar_dm(self, membro, acao, motivo):
        try:
            embed_dm = discord.Embed(
                title="aviso de punição",
                description=f"você recebeu um **{acao.lower()}** no servidor **platform destroyer**.",
                color=discord.Color.red()
            )
            embed_dm.add_field(name="motivo:", value=motivo)
            await membro.send(embed=embed_dm)
        except: pass 

    @commands.command(name="nuclearbomb")
    async def nuclearbomb(self, ctx, membro: discord.Member = None):
        if ctx.author.id not in self.USUARIOS_AUTORIZADOS:
            return await ctx.send("❌ Você não tem acesso aos códigos de lançamento!")

        alvo = await self.identificar_alvo(ctx, membro)
        if not alvo:
            return await ctx.send("❓ Marque alguém ou responda para lançar a bomba!")

        try:
            # Corrigido: Membros precisam de roles=[], mas o timeout deve vir antes se for tirar todas as roles
            await alvo.edit(roles=[], reason="Bomba Nuclear: Falou mal do Santos")
            await alvo.timeout(datetime.timedelta(hours=1), reason="Falou mal do Santos FC")
            await ctx.send(f"☢️ {alvo.mention} foi expurgado por falar mal do Santos.") # Corrigido f-string
            await self.enviar_log(ctx, alvo, "NUCLEAR BOMB", "Falar mal do Santos FC", discord.Color.from_rgb(0,0,0), "1h")
        except discord.Forbidden:
            await ctx.send("❌ Erro de hierarquia: O alvo é mais poderoso que o bot!")

    @commands.hybrid_command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, membro: discord.Member = None, tempo: str = "10min", *, motivo: str = "não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return await ctx.send("Mencione alguém ou responda a uma mensagem.")

        if tempo == "0":
            cargo = ctx.guild.get_role(self.ID_CARGO_MUTADO)
            if cargo:
                try:
                    await self.avisar_dm(membro, "mute", motivo)
                    await membro.add_roles(cargo, reason=motivo)
                    await self.enviar_log(ctx, membro, "mute permanente", motivo, discord.Color.red(), "permanente")
                    return await ctx.send(f"o usuário {membro.mention} foi mutado permanentemente")
                except discord.Forbidden:
                    return await ctx.send("❌ sem permissão para mutar este usuário")
        
        match = re.fullmatch(r"(\d+)(min|h|d)", tempo.lower())
        if match:
            qtd, unidade = int(match.group(1)), match.group(2) 
            segundos = qtd * {'d': 86400, 'h': 3600, 'min': 60}[unidade]
            try:
                await self.avisar_dm(membro, f"mutado por {tempo}", motivo)
                await membro.timeout(datetime.timedelta(seconds=segundos), reason=motivo)
                await self.enviar_log(ctx, membro, "mute", motivo, discord.Color.red(), tempo)
                await ctx.send(f"o usuário {membro.mention} foi silenciado por {tempo}")
            except discord.Forbidden:
                await ctx.send("❌ erro de permissão (hierarquia de cargos)")
        else:
            await ctx.send("use: ?mute @usuario 10min/1h/1d ou 0 para permanente")

    @commands.hybrid_command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, membro: discord.Member = None, *, motivo: str = "não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return await ctx.send("Mencione alguém ou responda a uma mensagem.")

        try:
            await membro.timeout(None, reason=motivo)
            cargo = ctx.guild.get_role(self.ID_CARGO_MUTADO)
            if cargo and cargo in membro.roles:
                await membro.remove_roles(cargo)
            await self.enviar_log(ctx, membro, "unmute", motivo, discord.Color.green())
            await ctx.send(f"o usuário {membro.mention} foi desmutado")
        except discord.Forbidden:
            await ctx.send("❌ falha: não tenho permissão para desmutar este membro")

    @commands.hybrid_command(name="warn")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, membro: discord.Member = None, *, motivo: str = "não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return await ctx.send("Mencione alguém ou responda a uma mensagem.")

        user_id = membro.id
        self.warns_cache[user_id] = self.warns_cache.get(user_id, 0) + 1
        atual = self.warns_cache[user_id]
        
        await self.avisar_dm(membro, f"aviso(warn) [{atual}/3]", motivo)
        await self.enviar_log(ctx, membro, f"aviso(warn) [{atual}/3]", motivo, discord.Color.orange())
        
        if atual >= 3:
            self.warns_cache[user_id] = 0 
            try:
                await membro.timeout(datetime.timedelta(hours=1), reason="limite de 3 warns atingido")
                await ctx.send(f"o usuário {membro.mention} recebeu o 3º aviso e foi mutado por 1 hora")
            except:
                await ctx.send(f"o usuário {membro.mention} recebeu o 3º aviso.")
        else:
            await ctx.send(f"o usuário {membro.mention} foi punido. (aviso {atual}/3)")

    @commands.hybrid_command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, membro: discord.Member = None, *, motivo="não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return await ctx.send("Mencione alguém ou responda a uma mensagem.")

        try:
            await self.avisar_dm(membro, "kick", motivo)
            await self.enviar_log(ctx, membro, "expulsão(kick)", motivo, discord.Color.yellow())
            await membro.kick(reason=motivo)
            await ctx.send(f"o usuário {membro.mention} foi expulso")
        except discord.Forbidden:
            await ctx.send("❌ falha: o cargo do usuário é superior ao meu")

    @commands.hybrid_command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, membro: discord.Member = None, *, motivo="não informado"):
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return await ctx.send("Mencione alguém ou responda a uma mensagem.")

        try:
            await self.avisar_dm(membro, "ban", motivo)
            await self.enviar_log(ctx, membro, "banimento", motivo, discord.Color.from_rgb(0, 0, 0))
            await membro.ban(reason=motivo)
            await ctx.send(f"o usuário {membro.mention} foi banido")
        except discord.Forbidden:
            await ctx.send("❌ falha: não posso banir este membro")

    @commands.hybrid_command(name="clear")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, quantidade: int):
        try:
            deleted = await ctx.channel.purge(limit=quantidade + 1)
            await ctx.send(f"✅ **{len(deleted)-1}** mensagens apagadas", delete_after=5)
        except Exception as e:
            await ctx.send(f"erro ao limpar chat: {e}")

async def setup(bot):
    await bot.add_cog(punicoes(bot))
