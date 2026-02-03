import discord
from discord import ui
from discord.ext import commands
import datetime
import time

# ID do Dono (Você)
ID_DONO = 1304003843172077659

# --- MODAL PARA O COMANDO EMBED ---
class EmbedModal(ui.Modal, title="Criar Embed Personalizado"):
    titulo = ui.TextInput(label="Título", placeholder="Título do aviso...", required=True)
    descricao = ui.TextInput(label="Descrição", style=discord.TextStyle.paragraph, placeholder="Conteúdo principal...", required=True)
    cor = ui.TextInput(label="Cor Hex (Ex: #5603AD)", placeholder="#5603AD", default="#5603AD", required=False, min_length=7, max_length=7)
    imagem = ui.TextInput(label="URL da Imagem (Opcional)", placeholder="https://...", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        # Double check de segurança no submit do modal
        if interaction.user.id != ID_DONO:
            return await interaction.response.send_message("❌ Apenas o dono pode enviar este formulário.", ephemeral=True)

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
        self.afk_users = {} 

    # Check personalizado para o Dono
    def e_dono():
        async def predicate(ctx):
            if ctx.author.id == ID_DONO:
                return True
            await ctx.send("❌ Este comando é exclusivo do desenvolvedor.", ephemeral=True)
            return False
        return commands.check(predicate)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        
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
        embed = discord.Embed(description=f"✅ {ctx.author.mention}, seu AFK foi definido!", color=self.COR_PLATFORM)
        await ctx.send(embed=embed, delete_after=10)

    @commands.hybrid_command(name="say", description="faz o bot dizer algo no chat")
    @e_dono() # Restrito ao dono
    async def say(self, ctx, *, mensagem: str):
        if not ctx.interaction: await ctx.message.delete()
        await ctx.send(mensagem)

    @commands.hybrid_command(name="embed", description="envia uma mensagem personalizada em embed")
    @e_dono() # Restrito ao dono
    async def embed(self, ctx):
        if ctx.interaction:
            await ctx.interaction.response.send_modal(EmbedModal())
        else:
            view = ui.View()
            btn = ui.Button(label="Abrir Editor", style=discord.ButtonStyle.blurple, emoji="📝")
            async def callback(interaction):
                if interaction.user.id == ID_DONO:
                    await interaction.response.send_modal(EmbedModal())
                else:
                    await interaction.response.send_message("Apenas o dono pode abrir este editor!", ephemeral=True)
            btn.callback = callback
            view.add_item(btn)
            await ctx.send("Clique abaixo para criar seu embed:", view=view, delete_after=60)

    @commands.hybrid_command(name="serverinfo")
    async def serverinfo(self, ctx):
        g = ctx.guild
        embed = discord.Embed(title=f"🏰 Informações de {g.name}", color=self.COR_PLATFORM)
        if g.icon: embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="👑 Dono", value=g.owner.mention, inline=True)
        embed.add_field(name="👥 Membros", value=f"`{g.member_count}`", inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="botinfo")
    async def botinfo(self, ctx):
        uptime = str(datetime.timedelta(seconds=int(round(time.time() - self.start_time))))
        embed = discord.Embed(title="Status da Platform Destroyer", color=self.COR_PLATFORM)
        embed.add_field(name="⏳ Uptime", value=f"`{uptime}`", inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="ping")
    async def ping(self, ctx):
        await ctx.send(f"🛰️ | Pong! **{round(self.bot.latency * 1000)}ms**")

    @commands.hybrid_command(name="help")
    async def help(self, ctx):
        embed = discord.Embed(title="📚 Central de Ajuda", description="Escolha uma categoria abaixo:", color=self.COR_PLATFORM)
        view = HelpView(self.bot, ["Ticket", "Jishaku", "Seguranca"])
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(utilitarios(bot))


