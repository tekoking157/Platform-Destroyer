import discord
from discord.ext import commands

IDS_CARGOS_PERMITIDOS = [
    1357569800947236998, 
    1414283694662750268, 
    1357569800947237000
]
MEU_ID = 1304003843172077659

class moderacao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="up", description="Promove um membro a um cargo")
    async def up(self, ctx, membro: str, cargo: discord.Role):
        # Converter string para Member
        try:
            membro = await commands.MemberConverter().convert(ctx, membro)
        except:
            return await ctx.send("<a:c_negativo:1384563046944608369> Membro inválido. Mencione ou forneça o ID do usuário.", ephemeral=True)
        
        tem_permissao = any(role.id in IDS_CARGOS_PERMITIDOS for role in ctx.author.roles)
        if not tem_permissao and ctx.author.id not in [ctx.guild.owner_id, MEU_ID]:
            return await ctx.send("<a:c_negativo:1384563046944608369> Você não possui um cargo autorizado para usar este comando.", ephemeral=True)

        if ctx.interaction:
            await ctx.defer()

        if ctx.author.top_role.position <= cargo.position and ctx.author.id not in [ctx.guild.owner_id, MEU_ID]:
            return await ctx.send(f"<a:c_negativo:1384563046944608369> Você não pode dar um cargo superior ou igual ao seu ({cargo.mention}).")

        if cargo.position >= ctx.guild.me.top_role.position:
            return await ctx.send(f"<a:c_negativo:1384563046944608369> Erro de Hierarquia: O cargo {cargo.name} está acima do meu cargo mais alto.")

        if cargo in membro.roles:
            return await ctx.send(f"<a:c_negativo:1384563046944608369> {membro.mention} já possui o cargo {cargo.mention}")

        try:
            await membro.add_roles(cargo, reason=f"Promovido por {ctx.author}")
            await ctx.send(
                f"<a:1316869378276458648:1384573961324593152> {membro.mention} foi promovido para o cargo {cargo.mention}",
                allowed_mentions=discord.AllowedMentions(roles=False)
            )
        except discord.Forbidden:
            await ctx.send("<a:c_negativo:1384563046944608369> Erro 403: Verifique se meu cargo está acima desse na lista de cargos.")
        except Exception as e:
            await ctx.send(f"<a:c_negativo:1384563046944608369> Erro inesperado: {e}")

    @commands.hybrid_command(name="demote", description="Remove um cargo de um membro")
    async def demote(self, ctx, membro: str, cargo: discord.Role):
        # Converter string para Member
        try:
            membro = await commands.MemberConverter().convert(ctx, membro)
        except:
            return await ctx.send("<a:c_negativo:1384563046944608369> Membro inválido. Mencione ou forneça o ID do usuário.", ephemeral=True)
        
        tem_permissao = any(role.id in IDS_CARGOS_PERMITIDOS for role in ctx.author.roles)
        if not tem_permissao and ctx.author.id not in [ctx.guild.owner_id, MEU_ID]:
            return await ctx.send("<a:c_negativo:1384563046944608369> Você não possui um cargo autorizado para usar este comando.", ephemeral=True)

        if ctx.interaction:
            await ctx.defer()

        if ctx.author.top_role.position <= cargo.position and ctx.author.id not in [ctx.guild.owner_id, MEU_ID]:
            return await ctx.send(f"<a:c_negativo:1384563046944608369> Você não pode remover um cargo superior ou igual ao seu ({cargo.mention}).")

        if cargo.position >= ctx.guild.me.top_role.position:
            return await ctx.send(f"<a:c_negativo:1384563046944608369> Erro de Hierarquia: Não posso remover o cargo {cargo.name} porque ele é superior ao meu.")

        try:
            if cargo in membro.roles:
                await membro.remove_roles(cargo, reason=f"Rebaixado por {ctx.author}")
                await ctx.send(
                    f"<a:c_positivo:1384563046944608369> {membro.mention} foi rebaixado e perdeu o cargo {cargo.mention}",
                    allowed_mentions=discord.AllowedMentions(roles=False)
                )
            else:
                await ctx.send(f"<a:c_negativo:1384563046944608369> {membro.mention} não possui o cargo {cargo.mention}")
        except discord.Forbidden:
            await ctx.send("<a:c_negativo:1384563046944608369> Falha na permissão: Arraste meu cargo para o topo da hierarquia.")
        except Exception as e:
            await ctx.send(f"<a:c_negativo:1384563046944608369> Erro ao remover cargo: {e}")

async def setup(bot):
    await bot.add_cog(moderacao(bot))
