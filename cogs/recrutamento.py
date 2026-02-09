import discord
from discord.ext import commands
from discord import ui
import datetime

COR_AZUL = discord.Color.from_rgb(86, 3, 173) 
BANNER_GIF = "https://media.discordapp.net/attachments/1383636357745737801/1465105440789757972/bannerdestroyer.gif"

ID_CANAL_LOGS = 1392511238759780475
IDS_PODEM_POSTAR = [1304003843172077659, 1291064098741555273]
IDS_AVALIADORES = [1357569800947236998, 1357569800947237000, 1414283694662750268]

vagas_abertas = True

def pode_postar():
    async def predicate(ctx):
        tem_permissao = any(role.id in IDS_PODEM_POSTAR for role in ctx.author.roles)
        if ctx.author.id in IDS_PODEM_POSTAR or tem_permissao:
            return True
        await ctx.send("❌ Apenas usuários autorizados podem postar o recrutamento.", ephemeral=True)
        return False
    return commands.check(predicate)

class BotaoAbrirRecrutamento(ui.View):
    def __init__(self):
        super().__init__(timeout=None) 

    @ui.button(label="Candidatar-se à Equipe", style=discord.ButtonStyle.primary, custom_id="btn_abrir_form_perma")
    async def callback(self, interaction: discord.Interaction, button: ui.Button):
        if not vagas_abertas:
            return await interaction.response.send_message("❌ As vagas estão fechadas no momento.", ephemeral=True)
        await interaction.response.send_modal(FormularioRecrutamento())

class BotoesAvaliacao(ui.View):
    def __init__(self, membro_candidato_id: int):
        super().__init__(timeout=None)
        self.membro_candidato_id = membro_candidato_id

    async def verificar_permissao_voto(self, interaction: discord.Interaction):
        tem_cargo = any(role.id in IDS_AVALIADORES for role in interaction.user.roles)
        return interaction.user.id in IDS_PODEM_POSTAR or tem_cargo or interaction.user.id in IDS_AVALIADORES

    @ui.button(label="Aprovar", style=discord.ButtonStyle.success, emoji="✅", custom_id="btn_aprovar")
    async def aprovar(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.verificar_permissao_voto(interaction):
            return await interaction.response.send_message("❌ Você não tem permissão para avaliar.", ephemeral=True)

        await interaction.response.defer()
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "✅ FORMULÁRIO APROVADO"
        embed.set_footer(text=f"Aprovado por: {interaction.user.name}")
        
        for item in self.children: item.disabled = True
        await interaction.edit_original_response(embed=embed, view=self)
        
        try:
            membro = await interaction.guild.fetch_member(self.membro_candidato_id)
            embed_dm = discord.Embed(
                title="🎉 Parabéns!",
                description=f"Olá {membro.mention}, seu formulário para a equipe **Platform Destroyer** foi **APROVADO**.",
                color=discord.Color.green()
            )
            embed_dm.set_image(url=BANNER_GIF)
            await membro.send(embed=embed_dm)
            await interaction.followup.send(f"Candidato {membro.name} aprovado e avisado!", ephemeral=True)
        except:
            await interaction.followup.send("Candidato aprovado, mas a DM está fechada.", ephemeral=True)

    @ui.button(label="Recusar", style=discord.ButtonStyle.danger, emoji="❌", custom_id="btn_recusar")
    async def recusar(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.verificar_permissao_voto(interaction):
             return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "❌ FORMULÁRIO RECUSADO"
        embed.set_footer(text=f"Recusado por: {interaction.user.name}")

        for item in self.children: item.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

class FormularioRecrutamento(ui.Modal, title='Recrutamento Platform Destroyer'):
    nome = ui.TextInput(label='Nome e Idade', placeholder='Ex: Pedro, 18 anos', required=True)
    experiencia = ui.TextInput(label='Experiência e Disponibilidade', style=discord.TextStyle.paragraph, max_length=500, required=True)
    conhecimentos = ui.TextInput(label='Conhecimentos Técnicos', style=discord.TextStyle.paragraph, max_length=400, required=True)
    motivacao = ui.TextInput(label='Motivação', style=discord.TextStyle.paragraph, max_length=500, required=True)
    extras = ui.TextInput(label='Informações Extras', style=discord.TextStyle.paragraph, max_length=400, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        canal_logs = interaction.guild.get_channel(ID_CANAL_LOGS)
        embed_staff = discord.Embed(title="📝 Novo Formulário Recebido", color=COR_AZUL, timestamp=datetime.datetime.now())
        embed_staff.set_thumbnail(url=interaction.user.display_avatar.url)
        embed_staff.add_field(name="Candidato", value=interaction.user.mention, inline=True)
        embed_staff.add_field(name="Nome e Idade", value=self.nome.value, inline=True)
        embed_staff.add_field(name="Experiência", value=self.experiencia.value, inline=False)
        embed_staff.add_field(name="Conhecimentos", value=self.conhecimentos.value, inline=False)
        embed_staff.add_field(name="Motivação", value=self.motivacao.value, inline=False)
        embed_staff.add_field(name="Extras", value=self.extras.value or "Nenhuma", inline=False)
        
        if canal_logs:
            await canal_logs.send(embed=embed_staff, view=BotoesAvaliacao(interaction.user.id))
            await interaction.response.send_message(f"✅ {interaction.user.mention}, formulário enviado!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Erro: Canal de logs não encontrado.", ephemeral=True)

class recrutamento(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="postar_recrutamento")
    @pode_postar()
    async def postar_recrutamento(self, ctx):
        embed = discord.Embed(title="<:PD:1384574150080729228> RECRUTAMENTO | PLATFORM DESTROYER", color=COR_AZUL)
        embed.description = (
            "**Deseja fazer parte da nossa staff de moderação?**\n\n"
            "### <:PD:1384574150080729228> Requisitos Básicos:\n"
            "• Ter maturidade e ser ativo no servidor.\n"
            "• Conhecer profundamente as regras.\n\n"
            "**Clique no botão abaixo para preencher seu formulário!**"
        )
        embed.set_image(url=BANNER_GIF)
        embed.set_footer(text="Platform Destroyer • Sistema de Recrutamento")
        await ctx.send(embed=embed, view=BotaoAbrirRecrutamento())
        try: await ctx.message.delete()
        except: pass 

    @commands.command(name="vagas_on")
    @pode_postar()
    async def vagas_on(self, ctx):
        global vagas_abertas
        vagas_abertas = True
        await ctx.send("✅ As vagas de recrutamento foram **ABERTAS**.")

    @commands.command(name="vagas_off")
    @pode_postar()
    async def vagas_off(self, ctx):
        global vagas_abertas
        vagas_abertas = False
        await ctx.send("❌ As vagas de recrutamento foram **FECHADAS**.")

async def setup(bot):
    bot.add_view(BotaoAbrirRecrutamento()) 
    await bot.add_cog(recrutamento(bot))




