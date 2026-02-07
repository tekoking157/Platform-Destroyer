import discord
from discord import ui
from discord.ext import commands
import datetime
import time

ID_DONO = 1304003843172077659

class EmbedModal(ui.Modal, title="Criar Embed Personalizado"):
    titulo = ui.TextInput(label="Título", placeholder="Título do aviso...", required=True)
    descricao = ui.TextInput(label="Descrição", style=discord.TextStyle.paragraph, placeholder="Conteúdo principal...", required=True)
    cor = ui.TextInput(label="Cor Hex (Ex: #5603AD)", placeholder="#5603AD", default="#5603AD", required=False, min_length=7, max_length=7)
    imagem = ui.TextInput(label="URL da Imagem (Opcional)", placeholder="https://...", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != ID_DONO:
            return await interaction.response.send_message("❌ Acesso negado.", ephemeral=True)

        cor_final = discord.Color.from_rgb(86, 3, 173)
        if self.cor.value:
            try:
                cor_final = discord.Color(int(self.cor.value.lstrip('#'), 16))
            except: pass

        embed = discord.Embed(
            title=self.titulo.value, 
            description=self.descricao.value, 
            color=cor_final, 
            timestamp=datetime.datetime.now()
        )
        if self.imagem.value and self.imagem.value.startswith("http"):
            embed.set_image(url=self.imagem.value)
            
        embed.set_footer(text=f"Enviado por: {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
        
        await interaction.response.send_message("✅ Embed enviado com sucesso!", ephemeral=True)
        await interaction.channel.send(embed=embed)

class HelpSelect(ui.Select):
    def __init__(self, bot, esconder):
        options = [
            discord.SelectOption(
                label=name.capitalize(), 
                description=f"Comandos do módulo {name}", 
                emoji="📁",
                value=name  
            )
            for name, cog in bot.cogs.items() if name not in esconder
        ]
        super().__init__(placeholder="? Escolha uma categoria para ver os comandos...", options=options)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        cog = self.bot.get_cog(self.values[0])
        if not cog:
            return await interaction.response.send_message(f"❌ Erro: A categoria '{self.values[0]}' não foi encontrada.", ephemeral=True)
            
        cmds = [f"`{c.name}`" for c in cog.get_commands() if not c.hidden]
        
        embed = discord.Embed(
            title=f"📁 Categoria: {self.values[0].capitalize()}",
            description=f"Aqui estão os comandos disponíveis:\n\n{' | '.join(cmds) if cmds else 'Nenhum comando disponível.'}",
            color=discord.Color.from_rgb(86, 3, 173)
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"? Total de {len(cmds)} comandos | Platform Destroyer")
        await interaction.response.edit_message(embed=embed)

class HelpView(ui.View):
    def __init__(self, bot, esconder):
        super().__init__(timeout=60)
        self.add_item(HelpSelect(bot, esconder))

class utilitarios(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.COR_PLATFORM = discord.Color.from_rgb(86, 3, 173)
        self.start_time = time.time()
        self.afk_users = {} 

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.author.id in self.afk_users:
            dados = self.afk_users[message.author.id]
            decorrido_total = time.time() - dados['tempo']
            if decorrido_total > 7:
                self.afk_users.pop(message.author.id)
                tempo_str = str(datetime.timedelta(seconds=int(decorrido_total)))
                try: await message.author.edit(nick=dados['nick_original'])
                except: pass
                await message.channel.send(f"👋 Bem-vindo de volta {message.author.mention}! Removi seu AFK. (Duração: `{tempo_str}`)", delete_after=10)
        for membro in message.mentions:
            if membro.id in self.afk_users:
                dados = self.afk_users[membro.id]
                timestamp = int(dados['tempo'])
                motivo = dados['motivo']
                embed = discord.Embed(
                    description=f"💤 {membro.mention} está **AFK** no momento.\n\n**Motivo:** {motivo}\n**Desde:** <t:{timestamp}:R>",
                    color=self.COR_PLATFORM
                )
                await message.reply(embed=embed, delete_after=15)

    @commands.hybrid_command(name="afk", description="avisa que você ficará offline")
    async def afk(self, ctx, *, motivo: str = "não informado"):
        nick_original = ctx.author.display_name
        novo_nick = f"[AFK] {nick_original}"[:32]
        self.afk_users[ctx.author.id] = {"motivo": motivo, "tempo": time.time(), "nick_original": nick_original}
        try: await ctx.author.edit(nick=novo_nick)
        except: pass
        embed = discord.Embed(description=f"✅ {ctx.author.mention}, seu AFK foi definido!\nMotivo: **{motivo}**", color=self.COR_PLATFORM)
        await ctx.send(embed=embed, delete_after=10)

    @commands.hybrid_command(name="serverinfo", description="mostra informações detalhadas do servidor")
    async def serverinfo(self, ctx):
        g = ctx.guild
        embed = discord.Embed(title=f"🏰 {g.name}", color=self.COR_PLATFORM)
        embed.set_author(name="Informações do Servidor", icon_url=self.bot.user.display_avatar.url)
        if g.icon: embed.set_thumbnail(url=g.icon.url)
        if g.banner: embed.set_image(url=g.banner.url)
        embed.add_field(name="👑 Dono", value=f"{g.owner.mention}", inline=True)
        embed.add_field(name="🆔 ID", value=f"`{g.id}`", inline=True)
        embed.add_field(name="📅 Criado", value=f"<t:{int(g.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="👥 Membros", value=f"Total: `{g.member_count}`\nBots: `{len([m for m in g.members if m.bot])}`", inline=True)
        embed.add_field(name="✨ Boosts", value=f"Nível: `{g.premium_tier}`\nQtd: `{g.premium_subscription_count}`", inline=True)
        embed.add_field(name="💬 Canais", value=f"Texto: `{len(g.text_channels)}`\nVoz: `{len(g.voice_channels)}`", inline=True)
        embed.set_footer(text=f"? Solicitado por {ctx.author.name}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="botinfo", description="mostra informações técnicas sobre o bot")
    async def botinfo(self, ctx):
        uptime = str(datetime.timedelta(seconds=int(round(time.time() - self.start_time))))
        embed = discord.Embed(title="🚀 Platform Destroyer Status", color=self.COR_PLATFORM)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="👨‍💻 Desenvolvedor", value="<@1304003843172077659>", inline=True)
        embed.add_field(name="⏳ Uptime", value=f"`{uptime}`", inline=True)
        embed.add_field(name="📡 Servidores", value=f"`{len(self.bot.guilds)}`", inline=True)
        embed.add_field(name="⚡ Prefixo", value="`?`", inline=True)
        embed.add_field(name="📚 Linguagem", value="`Python (discord.py)`", inline=True)
        embed.add_field(name="⚙️ Versão", value="`2.0.1`", inline=True)
        embed.set_footer(text="? Software de Automação s3ventzz")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="nicktroll", description="trolla o apelido de um membro")
    @commands.has_permissions(manage_nicknames=True)
    async def nicktroll(self, ctx, membro: discord.Member, *, nome: str = "cupiditys slave"):
        try:
            await membro.edit(nick=nome)
            if not ctx.interaction: await ctx.message.delete()
            await ctx.send(f"✅ Apelido de {membro.mention} alterado!", delete_after=3)
        except: await ctx.send("❌ Erro de hierarquia!", delete_after=5)

    @commands.hybrid_command(name="say", description="faz o bot dizer algo no chat")
    async def say(self, ctx, *, mensagem: str):
        if ctx.author.id != ID_DONO: return await ctx.send("❌ Negado.", ephemeral=True)
        if not ctx.interaction: await ctx.message.delete()
        await ctx.send(mensagem)

    @commands.hybrid_command(name="embed", description="envia uma mensagem personalizada em embed")
    async def embed(self, ctx):
        if ctx.author.id != ID_DONO: return await ctx.send("❌ Negado.", ephemeral=True)
        if ctx.interaction: await ctx.interaction.response.send_modal(EmbedModal())
        else:
            view = ui.View()
            btn = ui.Button(label="Abrir Editor", style=discord.ButtonStyle.blurple, emoji="📝")
            async def callback(interaction):
                if interaction.user.id == ID_DONO: await interaction.response.send_modal(EmbedModal())
            btn.callback = callback
            view.add_item(btn)
            await ctx.send("Clique abaixo para criar seu embed:", view=view, delete_after=60)

    @commands.hybrid_command(name="userinfo", description="mostra informações detalhadas de um usuário")
    async def userinfo(self, ctx, membro: discord.Member = None):
        membro = membro or ctx.author
        status_traduzido = {"online": "🟢 Online", "idle": "🌙 Ausente", "dnd": "🔴 Não Perturbe", "offline": "⚪ Offline"}
        status = status_traduzido.get(str(membro.status), "⚪ Offline")
        cargos = [role.mention for role in membro.roles if role.name != "@everyone"]
        embed = discord.Embed(title=f"👤 {membro.name}", color=self.COR_PLATFORM)
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.add_field(name="🆔 ID", value=f"`{membro.id}`", inline=True)
        embed.add_field(name="🌐 Status", value=status, inline=True)
        embed.add_field(name="📅 Criada em", value=f"<t:{int(membro.created_at.timestamp())}:D>", inline=True)
        embed.add_field(name="📥 Entrada", value=f"<t:{int(membro.joined_at.timestamp())}:R>", inline=True)
        embed.add_field(name=f"🛡️ Cargos ({len(cargos)})", value=" ".join(cargos[:5]) if cargos else "Nenhum", inline=False)
        embed.set_footer(text=f"? ID do Autor: {ctx.author.id}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="avatar", description="mostra o avatar de um usuário")
    async def avatar(self, ctx, membro: discord.Member = None):
        membro = membro or ctx.author
        embed = discord.Embed(title=f"🖼️ Avatar de {membro.name}", color=self.COR_PLATFORM)
        embed.set_image(url=membro.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="banner", description="mostra o banner de um usuário")
    async def banner(self, ctx, membro: discord.Member = None):
        membro = membro or ctx.author
        user = await self.bot.fetch_user(membro.id)
        if not user.banner: return await ctx.send("❌ Sem banner.", ephemeral=True)
        embed = discord.Embed(title=f"🚩 Banner de {membro.name}", color=self.COR_PLATFORM)
        embed.set_image(url=user.banner.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="lock", description="tranca o canal atual")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send("🔒 | Canal bloqueado!")

    @commands.hybrid_command(name="unlock", description="destranca o canal atual")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
        await ctx.send("🔓 | Canal desbloqueado!")

    @commands.hybrid_command(name="ping", description="mostra a latência do bot")
    async def ping(self, ctx):
        await ctx.send(f"🛰️ | Pong! **{round(self.bot.latency * 1000)}ms**")

    @commands.hybrid_command(name="slowmode", description="define o slowmode do canal")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, segundos: int):
        await ctx.channel.edit(slowmode_delay=segundos)
        await ctx.send(f"🕒 Modo lento: **{segundos}s**.")

    @commands.hybrid_command(name="help", description="central de ajuda interativa")
    async def help(self, ctx):
        embed = discord.Embed(
            title="📚 Central de Ajuda", 
            description="Selecione uma categoria no menu abaixo para ver os comandos disponíveis.\n\n*Caso o menu expire, use o comando novamente.*", 
            color=self.COR_PLATFORM
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_image(url="https://res.cloudinary.com/dv0xl7skh/image/upload/v1770493528/banner_exemplo.png")
        view = HelpView(self.bot, ["Ticket", "Jishaku", "Seguranca"])
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(utilitarios(bot))






