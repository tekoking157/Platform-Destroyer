import discord
from discord import ui
from discord.ext import commands
import datetime
import time

# ID do Dono
ID_DONO = 1304003843172077659

# --- MODAL PARA O COMANDO EMBED ---
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

        embed = discord.Embed(title=self.titulo.value, description=self.descricao.value, color=cor_final, timestamp=datetime.datetime.now())
        if self.imagem.value and self.imagem.value.startswith("http"):
            embed.set_image(url=self.imagem.value)
            
        embed.set_footer(text=f"Enviado por: {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message("✅ Embed enviado com sucesso!", ephemeral=True)
        await interaction.channel.send(embed=embed)

# --- VIEW PARA O COMANDO HELP ---
class HelpSelect(ui.Select):
    def __init__(self, bot, esconder):
        options = [
            discord.SelectOption(label=name.capitalize(), description=f"Comandos do módulo {name}", emoji="📁", value=name)
            for name, cog in bot.cogs.items() if name not in esconder
        ]
        super().__init__(placeholder="Escolha uma categoria para ver os comandos...", options=options)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        cog = self.bot.get_cog(self.values[0])
        cmds = [f"`{c.name}`" for c in cog.get_commands() if not c.hidden]
        embed = discord.Embed(title=f"📁 Categoria: {self.values[0].capitalize()}", description=" | ".join(cmds) if cmds else "Vazio.", color=discord.Color.from_rgb(86, 3, 173))
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
        self.afk_users = {} 

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return

        # Volta do AFK (Tempo de espera de 7 segundos)
        if message.author.id in self.afk_users:
            dados = self.afk_users[message.author.id]
            if (time.time() - dados['tempo']) > 7:
                self.afk_users.pop(message.author.id)
                try: await message.author.edit(nick=dados['nick_original'])
                except: pass
                await message.channel.send(f"👋 Bem-vindo de volta {message.author.mention}! Removi seu AFK.", delete_after=10)

        # Menção a quem está AFK
        for membro in message.mentions:
            if membro.id in self.afk_users:
                dados = self.afk_users[membro.id]
                embed = discord.Embed(
                    description=f"💤 {membro.mention} está **AFK** no momento.\n\n**Motivo:** {dados['motivo']}\n**Desde:** <t:{int(dados['tempo'])}:R>",
                    color=self.COR_PLATFORM
                )
                await message.reply(embed=embed, delete_after=15)

    @commands.hybrid_command(name="afk", description="avisa que você ficará offline")
    async def afk(self, ctx, *, motivo: str = "não informado"):
        nick_original = ctx.author.display_name
        self.afk_users[ctx.author.id] = {"motivo": motivo, "tempo": time.time(), "nick_original": nick_original}
        
        try: await ctx.author.edit(nick=f"[AFK] {nick_original}"[:32])
        except: pass

        embed = discord.Embed(
            description=f"✅ {ctx.author.mention}, seu AFK foi definido!\nMotivo: **{motivo}**",
            color=self.COR_PLATFORM
        )
        await ctx.send(embed=embed, delete_after=10)

    @commands.hybrid_command(name="say")
    async def say(self, ctx, *, mensagem: str):
        if ctx.author.id != ID_DONO: return
        if not ctx.interaction: await ctx.message.delete()
        await ctx.send(mensagem)

    @commands.hybrid_command(name="embed")
    async def embed(self, ctx):
        if ctx.author.id != ID_DONO: return
        if ctx.interaction: await ctx.interaction.response.send_modal(EmbedModal())
        else:
            view = ui.View()
            btn = ui.Button(label="Abrir Editor", style=discord.ButtonStyle.blurple, emoji="📝")
            btn.callback = lambda i: i.response.send_modal(EmbedModal()) if i.user.id == ID_DONO else None
            view.add_item(btn)
            await ctx.send("Clique abaixo para criar seu embed:", view=view)

    @commands.hybrid_command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send("🔒 | Canal bloqueado! Use `?unlock` para destravar.")

    @commands.hybrid_command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
        await ctx.send("🔓 | Canal desbloqueado!")

    @commands.hybrid_command(name="slowmode")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, segundos: int):
        await ctx.channel.edit(slowmode_delay=segundos)
        await ctx.send(f"🕒 Modo lento: **{segundos}s**.")

    @commands.hybrid_command(name="nicktroll")
    @commands.has_permissions(manage_nicknames=True)
    async def nicktroll(self, ctx, membro: discord.Member, *, nome: str = "cupiditys slave"):
        await membro.edit(nick=nome)
        await ctx.send(f"✅ Nick de {membro.mention} alterado!", delete_after=3)

    @commands.hybrid_command(name="avatar")
    async def avatar(self, ctx, membro: discord.Member = None):
        membro = membro or ctx.author
        embed = discord.Embed(title=f"🖼️ Avatar de {membro.name}", color=self.COR_PLATFORM)
        embed.set_image(url=membro.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="userinfo")
    async def userinfo(self, ctx, membro: discord.Member = None):
        membro = membro or ctx.author
        embed = discord.Embed(title=f"👤 Informações de {membro.name}", color=self.COR_PLATFORM)
        embed.add_field(name="🆔 ID", value=f"`{membro.id}`", inline=True)
        embed.add_field(name="📅 Conta criada", value=f"<t:{int(membro.created_at.timestamp())}:R>", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="serverinfo")
    async def serverinfo(self, ctx):
        g = ctx.guild
        embed = discord.Embed(title=f"🏰 Informações de {g.name}", color=self.COR_PLATFORM)
        embed.add_field(name="👑 Dono", value=g.owner.mention)
        embed.add_field(name="👥 Membros", value=f"`{g.member_count}`")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="botinfo")
    async def botinfo(self, ctx):
        uptime = str(datetime.timedelta(seconds=int(round(time.time() - self.start_time))))
        embed = discord.Embed(title="Status da Platform Destroyer", color=self.COR_PLATFORM)
        embed.add_field(name="⏳ Uptime", value=f"`{uptime}`")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="ping")
    async def ping(self, ctx):
        await ctx.send(f"🛰️ | Pong! **{round(self.bot.latency * 1000)}ms**")

    @commands.hybrid_command(name="manutencao")
    async def manutencao(self, ctx, status: str):
        if ctx.author.id != ID_DONO: return
        self.bot.manutencao = (status.lower() == "on")
        await ctx.send(f"Modo manutenção {'ligado' if self.bot.manutencao else 'desligado'}.")

    @commands.hybrid_command(name="help")
    async def help(self, ctx):
        view = HelpView(self.bot, ["Ticket", "Jishaku", "Seguranca"])
        await ctx.send("📚 Central de Ajuda", view=view)

async def setup(bot):
    await bot.add_cog(utilitarios(bot))



