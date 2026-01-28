import discord
from discord import ui
from discord.ext import commands
import datetime
import time

# --- MODAL PARA O COMANDO EMBED ---
class EmbedModal(ui.Modal, title="Criar Embed Personalizado"):
    titulo = ui.TextInput(label="Título", placeholder="Título do aviso...", required=True)
    descricao = ui.TextInput(label="Descrição", style=discord.TextStyle.paragraph, placeholder="Conteúdo principal...", required=True)
    cor = ui.TextInput(label="Cor Hex (Ex: #5603AD)", placeholder="#5603AD", default="#5603AD", required=False, min_length=7, max_length=7)
    imagem = ui.TextInput(label="URL da Imagem (Opcional)", placeholder="https://...", required=False)

    async def on_submit(self, interaction: discord.Interaction):
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

# --- VIEW PARA O COMANDO HELP ---
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
        super().__init__(placeholder="Escolha uma categoria para ver os comandos...", options=options)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        
        cog = self.bot.get_cog(self.values[0])
        
        if not cog:
            return await interaction.response.send_message(f"❌ Erro: A categoria '{self.values[0]}' não foi encontrada.", ephemeral=True)
            
        cmds = [f"`{c.name}`" for c in cog.get_commands() if not c.hidden]
        
        embed = discord.Embed(
            title=f"📁 Categoria: {self.values[0].capitalize()}",
            description=" | ".join(cmds) if cmds else "Nenhum comando disponível nesta categoria.",
            color=discord.Color.from_rgb(86, 3, 173)
        )
        embed.set_footer(text=f"Total de {len(cmds)} comandos encontrados.")
        
        await interaction.response.edit_message(embed=embed)
class HelpView(ui.View):
    def __init__(self, bot, esconder):
        super().__init__(timeout=60)
        self.add_item(HelpSelect(bot, esconder))

# --- CLASSE PRINCIPAL ---
class utilitarios(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.COR_PLATFORM = discord.Color.from_rgb(86, 3, 173)
        self.start_time = time.time()

    @commands.hybrid_command(name="serverinfo", description="mostra informações detalhadas do servidor")
    async def serverinfo(self, ctx):
        g = ctx.guild
        total = g.member_count
        bot_count = len([m for m in g.members if m.bot])
        human_count = total - bot_count
        
        embed = discord.Embed(title=f"🏰 Informações de {g.name}", color=self.COR_PLATFORM)
        if g.icon: embed.set_thumbnail(url=g.icon.url)
        
        embed.add_field(name="👑 Dono", value=g.owner.mention, inline=True)
        embed.add_field(name="🆔 ID", value=f"`{g.id}`", inline=True)
        embed.add_field(name="📅 Criado em", value=f"<t:{int(g.created_at.timestamp())}:D>", inline=True)
        
        embed.add_field(name="👥 Membros", value=f"Total: `{total}`\nHumanos: `{human_count}`\nBots: `{bot_count}`", inline=True)
        embed.add_field(name="✨ Boosts", value=f"Nível: `{g.premium_tier}`\nQuantidade: `{g.premium_subscription_count}`", inline=True)
        
        embed.set_footer(text=f"Solicitado por {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="botinfo", description="mostra informações técnicas sobre o bot")
    async def botinfo(self, ctx):
        uptime_sec = int(round(time.time() - self.start_time))
        uptime = str(datetime.timedelta(seconds=uptime_sec))
        
        embed = discord.Embed(
            title="Status da Platform Destroyer",
            description=(
                "A **Platform Destroyer** é um bot multifuncional focado em segurança avançada, "
                "gerenciamento de tickets e automação avançada."
            ),
            color=self.COR_PLATFORM
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        embed.add_field(name="👨‍💻 Criador", value="<@1304003843172077659>", inline=True)
        embed.add_field(name="⏳ Uptime", value=f"`{uptime}`", inline=True)
        embed.add_field(name="📡 Servidores", value=f"`{len(self.bot.guilds)}`", inline=True)
        
        embed.add_field(name="⚡ Prefixo", value=f"`{self.bot.command_prefix}`", inline=True)
        embed.add_field(name="📚 Versão", value="`2.0.1 - stable`", inline=True)
        embed.add_field(name="⚙️ Sistema", value="`Python & Discord.py`", inline=True)
        
        embed.set_footer(text="Platform Destroyer 2026")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="nicktroll", description="trolla o apelido de um membro")
    @commands.has_permissions(manage_nicknames=True)
    async def nicktroll(self, ctx, membro: discord.Member, *, nome: str = None):
        nome_troll = nome or "cupiditys slave"
        try:
            await membro.edit(nick=nome_troll)
            if not ctx.interaction: await ctx.message.delete()
            await ctx.send(f"✅ o apelido de {membro.mention} foi alterado para: **{nome_troll}**", delete_after=3)
        except discord.Forbidden:
            await ctx.send("❌ erro de hierarquia: não posso mudar o nome deste usuário.", delete_after=5)

    @commands.hybrid_command(name="say", description="faz o bot dizer algo no chat")
    @commands.has_permissions(manage_messages=True)
    async def say(self, ctx, *, mensagem: str):
        if not ctx.interaction: await ctx.message.delete()
        await ctx.send(mensagem)

    @commands.hybrid_command(name="embed", description="envia uma mensagem personalizada em embed")
    @commands.has_permissions(manage_messages=True)
    async def embed(self, ctx):
        if ctx.interaction:
            await ctx.interaction.response.send_modal(EmbedModal())
        else:
            view = ui.View()
            btn = ui.Button(label="Abrir Editor de Embed", style=discord.ButtonStyle.blurple, emoji="📝")
            async def callback(interaction):
                if interaction.user == ctx.author:
                    await interaction.response.send_modal(EmbedModal())
                else:
                    await interaction.response.send_message("Você não iniciou este comando!", ephemeral=True)
            btn.callback = callback
            view.add_item(btn)
            await ctx.send("Clique no botão abaixo para criar seu embed:", view=view, delete_after=60)

    @commands.hybrid_command(name="userinfo", description="mostra informações detalhadas de um usuário")
    async def userinfo(self, ctx, membro: discord.Member = None):
        membro = membro or ctx.author
        status_traduzido = {"online": "🟢 online", "idle": "🌙 ausente", "dnd": "🔴 não perturbe", "offline": "⚪ offline"}
        status = status_traduzido.get(str(membro.status), "⚪ offline")
        
        cargos = [role.mention for role in membro.roles if role.name != "@everyone"]
        cargos_str = " ".join(cargos) if cargos else "nenhum cargo"

        embed = discord.Embed(title=f"👤 Informações de {membro.name}", color=self.COR_PLATFORM)
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.add_field(name="🆔 ID", value=f"`{membro.id}`", inline=True)
        embed.add_field(name="🏷️ Apelido", value=f"{membro.nick or 'nenhum'}", inline=True)
        embed.add_field(name="🌐 Status", value=status, inline=True)
        embed.add_field(name="📅 Conta criada", value=f"<t:{int(membro.created_at.timestamp())}:R>", inline=False)
        embed.add_field(name="📥 Entrou aqui", value=f"<t:{int(membro.joined_at.timestamp())}:R>", inline=False)
        embed.add_field(name=f"🛡️ Cargos ({len(cargos)})", value=cargos_str, inline=False)
        embed.set_footer(text=f"Solicitado por {ctx.author.name}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="avatar", description="mostra o avatar de um usuário")
    async def avatar(self, ctx, membro: discord.Member = None):
        membro = membro or ctx.author
        embed = discord.Embed(
            title=f"🖼️ Avatar de {membro.name}",
            description=f"🔗 [Clique aqui para baixar]({membro.display_avatar.url})",
            color=self.COR_PLATFORM
        )
        embed.set_image(url=membro.display_avatar.url)
        embed.set_footer(text=f"Solicitado por {ctx.author.name}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="lock", description="tranca o canal atual")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        emoji_lock = "<:lock:1465515254556393526>" # Certifique-se que o bot está no server desse emoji
        await ctx.send(f"{emoji_lock} | Canal bloqueado com sucesso! Use `?unlock` para destravar.")

    @commands.hybrid_command(name="unlock", description="destranca o canal atual")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
        emoji_unlock = "<:unlock:1465525796499099728>"
        await ctx.send(f"{emoji_unlock} | Canal desbloqueado com sucesso!")

    @commands.hybrid_command(name="ping", description="mostra a latência do bot")
    async def ping(self, ctx):
        lat = round(self.bot.latency * 1000)
        await ctx.send(f"🛰️ | Pong! Meu ping é de **{lat}ms**")

    @commands.hybrid_command(name="slowmode", description="define o slowmode do canal")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, segundos: int):
        if segundos > 21600: return await ctx.send("❌ Limite: 6h.", delete_after=5)
        await ctx.channel.edit(slowmode_delay=segundos)
        await ctx.send(f"🕒 Modo lento: **{segundos}s**.")

    @commands.hybrid_command(name="help", description="central de ajuda interativa")
    async def help(self, ctx):
        embed = discord.Embed(
            title="📚 Central de Ajuda | Platform Destroyer",
            description="Escolha uma categoria no menu abaixo para ver os comandos disponíveis.",
            color=self.COR_PLATFORM
        )
        esconder = ["Ticket", "Jishaku", "Seguranca", "Recrutamento"]
        view = HelpView(self.bot, esconder)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="manutencao", description="ativa/desativa o modo de manutenção")
    async def manutencao(self, ctx, status: str):
        if ctx.author.id != 1304003843172077659:
            return await ctx.send("❌ Apenas o dono!", delete_after=5)
        
        status = status.lower()
        if status == "on":
            self.bot.manutencao = True
            await self.bot.change_presence(activity=discord.Game(name="⚠️ EM MANUTENÇÃO"))
            await ctx.send("🚨 Modo manutenção **ATIVADO**.")
        elif status == "off":
            self.bot.manutencao = False
            await self.bot.change_presence(activity=discord.Game(name="Platform Destroyer 2026"))
            await ctx.send("✅ Modo manutenção **DESATIVADO**.")

async def setup(bot):
    await bot.add_cog(utilitarios(bot))