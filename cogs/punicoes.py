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
        # ADICIONE OS IDs AUTORIZADOS AQUI
        self.USUARIOS_AUTORIZADOS = [1304003843172077659, 935566792384991303] 

    # --- Função Auxiliar para identificar o alvo (Mencionado ou Respondido) ---
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
        headers = {"Content-Type": "application/json", "x-bot-token": self.bot.http.token}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.URL_SITE, json=payload, headers=headers) as response:
                    if response.status in [200, 201]:
                        print(f"log enviado ao site: {usuario.name}")
        except Exception as e:
            print(f"falha ao conectar com o site: {e}")

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

        titulo = f"| usuário {acao.lower()}"
        embed = discord.Embed(title=titulo, color=cor, timestamp=datetime.datetime.now())
        
        avatar_url = membro.display_avatar.url if hasattr(membro, 'display_avatar') else self.bot.user.display_avatar.url
        embed.set_thumbnail(url=avatar_url)
        
        embed.add_field(name="| usuário", value=f"{membro.mention}\n`{membro.id}`", inline=False)
        embed.add_field(name="| moderador", value=f"{ctx.author.mention}\n`{ctx.author.id}`", inline=False)
        if "muta" in acao.lower():
            embed.add_field(name="| duração", value=duracao, inline=False)
        embed.add_field(name="| motivo", value=motivo, inline=False)
        embed.add_field(name="| informações", value="executado via platform destroyer", inline=False)
        embed.set_footer(text=f"id do caso: {membro.id}")
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
            return await ctx.send("❌ Você não tem acesso aos códigos de lançamento da bomba nuclear!")

        alvo = await self.identificar_alvo(ctx, membro)
        if not alvo:
            return await ctx.send("❓ Marque alguém ou responda a uma mensagem para lançar a bomba!")

        try:
            await alvo.edit(roles=[], reason="Bomba Nuclear: Falou mal do Santos")
            await alvo.timeout(datetime.timedelta(hours=1), reason="Falou mal do Santos FC")
            await ctx.send(f"💣 **NUKE DISPARADA**\n{alvo.mention} foi expurgado por falar mal do Santos.")
            await self.enviar_log(ctx, alvo, "NUCLEAR BOMB", "Falar mal do Santos FC", discord.Color.from_rgb(0,0,0), "1h")
        except discord.Forbidden:
            await ctx.send("❌ Erro de hierarquia: O alvo é mais poderoso que o bot!")

    # --- COMANDOS COM SISTEMA DE RESPOSTA ---

    @commands.hybrid_command(name="mute", description="silencia um usuário")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, membro: discord.Member = None, tempo: str = "10min", *, motivo: str = "não informado"):
        await ctx.defer()
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
                await ctx.send("❌ erro de permissão ao tentar aplicar timeout")
        else:
            await ctx.send("use: ?mute @usuario 10min/1h/1d ou 0 para permanente")

    @commands.hybrid_command(name="unmute", description="desmuta um usuário")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, membro: discord.Member = None, *, motivo: str = "não informado"):
        await ctx.defer()
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

    @commands.hybrid_command(name="warn", description="aplica um aviso no usuário")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, membro: discord.Member = None, *, motivo: str = "não informado"):
        await ctx.defer()
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
                await ctx.send(f"o usuário {membro.mention} recebeu o 3º aviso e foi mutado por 1 hora automaticamente")
            except:
                await ctx.send(f"o usuário {membro.mention} recebeu o 3º aviso, mas falhei no castigo automático")
        else:
            await ctx.send(f"o usuário {membro.mention} foi punido. (aviso {atual}/3)")

    @commands.hybrid_command(name="unwarn", description="remove um aviso do usuário")
    @commands.has_permissions(manage_messages=True)
    async def unwarn(self, ctx, membro: discord.Member = None):
        await ctx.defer()
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return await ctx.send("Mencione alguém ou responda a uma mensagem.")

        user_id = membro.id
        if self.warns_cache.get(user_id, 0) > 0:
            self.warns_cache[user_id] -= 1
            atual = self.warns_cache[user_id]
            await self.enviar_log(ctx, membro, "aviso removido", "unwarn manual", discord.Color.blue())
            await ctx.send(f"removi um aviso de {membro.mention}. agora ele tem {atual}/3 avisos")
        else:
            await ctx.send(f"o usuário {membro.mention} não possui avisos para remover")

    @commands.hybrid_command(name="kick", description="expulsa um usuário")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, membro: discord.Member = None, *, motivo="não informado"):
        await ctx.defer()
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return await ctx.send("Mencione alguém ou responda a uma mensagem.")

        try:
            await self.avisar_dm(membro, "kick", motivo)
            await self.enviar_log(ctx, membro, "expulsão(kick)", motivo, discord.Color.yellow())
            await membro.kick(reason=motivo)
            await ctx.send(f"o usuário {membro.mention} foi expulso")
        except discord.Forbidden:
            await ctx.send("❌ falha: o cargo do usuário é superior ao meu")

    @commands.hybrid_command(name="ban", description="bane um usuário")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, membro: discord.Member = None, *, motivo="não informado"):
        await ctx.defer()
        membro = await self.identificar_alvo(ctx, membro)
        if not membro: return await ctx.send("Mencione alguém ou responda a uma mensagem.")

        try:
            await self.avisar_dm(membro, "ban", motivo)
            await self.enviar_log(ctx, membro, "banimento", motivo, discord.Color.from_rgb(0, 0, 0))
            await membro.ban(reason=motivo)
            await ctx.send(f"o usuário {membro.mention} foi banido")
        except discord.Forbidden:
            await ctx.send("❌ falha: não posso banir este membro")

    
    @commands.hybrid_command(name="unban", description="desbane um usuário pelo ID")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: str, *, motivo="não informado"):
        await ctx.defer()
        try:
            user = await self.bot.fetch_user(int(user_id))
            await ctx.guild.unban(user, reason=motivo)
            await self.enviar_log(ctx, user, "desbanimento(unban)", motivo, discord.Color.green())
            await ctx.send(f"o usuário {user.name} foi desbanido")
        except ValueError:
            await ctx.send("❌ o ID fornecido é inválido")
        except discord.NotFound:
            await ctx.send("❌ esse usuário não está banido")
        except Exception as e:
            await ctx.send(f"❌ erro ao desbanir: {e}")

    @commands.hybrid_command(name="clear", description="limpa mensagens do chat")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, quantidade: int):
        await ctx.defer(ephemeral=True) 
        try:
            deleted = await ctx.channel.purge(limit=quantidade)
            await ctx.send(f"✅ **{len(deleted)}** mensagens apagadas", delete_after=5)
        except Exception as e:
            await ctx.send(f"erro ao limpar chat: {e}")

async def setup(bot):
    await bot.add_cog(punicoes(bot))
