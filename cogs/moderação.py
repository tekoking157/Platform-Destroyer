import discord
from discord.ext import commands

class moderacao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="up")
    @commands.has_permissions(manage_roles=True)
    async def up(self, ctx, membro: discord.Member, *, cargo: discord.Role):
        """Uso: ?up @membro Nome do Cargo OU ID"""
        
        # --- TRAVA DE HIERARQUIA DO AUTOR ---
        # Verifica se o cargo que o autor quer dar é maior ou igual ao cargo mais alto do autor
        if ctx.author.top_role.position <= cargo.position and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(f"❌ Você não pode dar um cargo que é superior ou igual ao seu ({cargo.mention}).")

        if cargo in membro.roles:
            return await ctx.send(f"❌ {membro.mention} já possui o cargo {cargo.mention}")

        try:
            await membro.add_roles(cargo)
            await ctx.send(
                f"✅ {membro.mention} foi promovido para o cargo {cargo.mention}",
                allowed_mentions=discord.AllowedMentions(roles=False)
            )
        
        except discord.Forbidden:
            await ctx.send("❌ Erro de Hierarquia: Meu cargo (Bot) precisa estar **ACIMA** do cargo que você quer dar no menu de cargos.")
        
        except Exception as e:
            await ctx.send(f"❌ Erro inesperado: {e}")

    @commands.hybrid_command(name="demote")
    @commands.has_permissions(manage_roles=True)
    async def demote(self, ctx, membro: discord.Member, *, cargo: discord.Role):
        """Uso: ?demote @membro Nome do Cargo OU ID"""

        # --- TRAVA DE HIERARQUIA DO AUTOR ---
        # Verifica se o cargo que o autor quer tirar é maior ou igual ao cargo mais alto do autor
        if ctx.author.top_role.position <= cargo.position and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(f"❌ Você não pode remover um cargo que é superior ou igual ao seu ({cargo.mention}).")

        try:
            if cargo in membro.roles:
                await membro.remove_roles(cargo)
                await ctx.send(
                    f"⚠️ {membro.mention} foi rebaixado e perdeu o cargo {cargo.mention}",
                    allowed_mentions=discord.AllowedMentions(roles=False)
                )
            else:
                await ctx.send(f"❌ {membro.mention} não possui o cargo {cargo.mention}?")
        
        except discord.Forbidden:
            await ctx.send("❌ Erro de Hierarquia: Meu cargo (Bot) precisa estar **ACIMA** do cargo que você quer remover.")
        
        except Exception as e:
            await ctx.send(f"❌ Erro ao remover cargo: {e}")

async def setup(bot):
    await bot.add_cog(moderacao(bot))
