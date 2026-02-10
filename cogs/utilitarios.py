const { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, ModalBuilder, TextInputBuilder, TextInputStyle, StringSelectMenuBuilder, SlashCommandBuilder } = require('discord.js');

const ID_DONO = "1304003843172077659";
const CARGOS_WHITELIST = ["1357569800947236998", "1414283694662750268", "1357569800947237000"];
const EMOJI_SETA = "<:seta:1384562807369895946>";
const EMOJI_SERVER = "<:server:1413985224223621212>";
const COR_PLATFORM = 0x5603AD;

let afkUsers = new Map();
let startTime = Date.now();

module.exports = {
    data: new SlashCommandBuilder()
        .setName('util')
        .setDescription('Comandos utilitários')
        .addSubcommand(s => s.setName('ping').setDescription('Veja o ping do bot'))
        .addSubcommand(s => s.setName('afk').setDescription('Fique AFK').addStringOption(o => o.setName('motivo').setDescription('Motivo do AFK'))),

    async execute(interaction) {
        const sub = interaction.options.getSubcommand();
        if (sub === 'ping') {
            return interaction.reply(`${EMOJI_SERVER} Pong! **${interaction.client.ws.ping}ms**`);
        }
        if (sub === 'afk') {
            const motivo = interaction.options.getString('motivo') || "não informado";
            const nickOriginal = interaction.member.displayName;
            afkUsers.set(interaction.user.id, { motivo, tempo: Date.now(), nickOriginal });
            try { await interaction.member.setNickname(`[AFK] ${nickOriginal}`.slice(0, 32)); } catch (e) {}
            const embed = new EmbedBuilder().setDescription(`${EMOJI_SERVER} ${interaction.user}, seu AFK foi definido!\n${EMOJI_SETA} Motivo: **${motivo}**`).setColor(COR_PLATFORM);
            return interaction.reply({ embeds: [embed] });
        }
    },

    async messageRun(message) {
        if (message.author.bot || !message.guild) return;

        if (afkUsers.has(message.author.id)) {
            const dados = afkUsers.get(message.author.id);
            const decorrido = Date.now() - dados.tempo;
            if (decorrido > 7000) {
                afkUsers.delete(message.author.id);
                try { await message.member.setNickname(dados.nickOriginal); } catch (e) {}
                const segundos = Math.floor(decorrido / 1000);
                const h = Math.floor(segundos / 3600);
                const m = Math.floor((segundos % 3600) / 60);
                const s = segundos % 60;
                await message.channel.send(`👋 Bem-vindo de volta ${message.author}! Removi seu AFK. (Duração: \`${h}h ${m}m ${s}s\`)`).then(msg => setTimeout(() => msg.delete(), 10000));
            }
        }

        if (message.mentions.users.size > 0) {
            message.mentions.users.forEach(async (user) => {
                if (afkUsers.has(user.id)) {
                    const dados = afkUsers.get(user.id);
                    const timestamp = Math.floor(dados.tempo / 1000);
                    const embed = new EmbedBuilder().setDescription(`${EMOJI_SERVER} <@${user.id}> está **AFK** no momento.\n\n${EMOJI_SETA} **Motivo:** ${dados.motivo}\n${EMOJI_SETA} **Desde:** <t:${timestamp}:R>`).setColor(COR_PLATFORM);
                    await message.reply({ embeds: [embed] }).then(msg => setTimeout(() => msg.delete(), 15000));
                }
            });
        }

        if (!message.content.startsWith('?')) return;
        const args = message.content.slice(1).trim().split(/ +/);
        const command = args.shift().toLowerCase();

        const listaComandos = ["afk", "serverinfo", "botinfo", "nicktroll", "say", "embed", "userinfo", "avatar", "banner", "lock", "unlock", "ping", "slowmode", "help"];
        if (!listaComandos.includes(command)) return;

        if (command === 'afk') {
            const motivo = args.join(" ") || "não informado";
            const nickOriginal = message.member.displayName;
            afkUsers.set(message.author.id, { motivo, tempo: Date.now(), nickOriginal });
            try { await message.member.setNickname(`[AFK] ${nickOriginal}`.slice(0, 32)); } catch (e) {}
            const embed = new EmbedBuilder().setDescription(`${EMOJI_SERVER} ${message.author}, seu AFK foi definido!\n${EMOJI_SETA} Motivo: **${motivo}**`).setColor(COR_PLATFORM);
            await message.channel.send({ embeds: [embed] }).then(msg => setTimeout(() => msg.delete(), 10000));
        }

        if (command === 'serverinfo') {
            const g = message.guild;
            const embed = new EmbedBuilder().setColor(COR_PLATFORM).setAuthor({ name: g.name, iconURL: g.iconURL() })
                .setDescription(`${EMOJI_SETA} **Dono:** <@${g.ownerId}>\n${EMOJI_SETA} **ID:** \`${g.id}\`\n${EMOJI_SETA} **Criado:** <t:${Math.floor(g.createdTimestamp / 1000)}:R>\n──────────────────────────────\n${EMOJI_SETA} **Membros:** \`${g.memberCount}\`\n${EMOJI_SETA} **Boosts:** Nível \`${g.premiumTier}\` (${g.premiumSubscriptionCount})\n${EMOJI_SETA} **Canais:** \`${g.channels.cache.size}\``)
                .setFooter({ text: `Solicitado por ${message.author.username}` });
            if (g.bannerURL()) embed.setImage(g.bannerURL());
            await message.channel.send({ embeds: [embed] });
        }

        if (command === 'botinfo') {
            const totalSec = Math.floor((Date.now() - startTime) / 1000);
            const h = Math.floor(totalSec / 3600);
            const m = Math.floor((totalSec % 3600) / 60);
            const s = totalSec % 60;
            const embed = new EmbedBuilder().setColor(COR_PLATFORM).setAuthor({ name: "Platform Destroyer", iconURL: message.client.user.displayAvatarURL() })
                .setDescription(`${EMOJI_SETA} **Dev:** <@${ID_DONO}>\n${EMOJI_SETA} **Ping:** \`${message.client.ws.ping}ms\`\n${EMOJI_SETA} **Uptime:** \`${h}h ${m}m ${s}s\`\n──────────────────────────────\n${EMOJI_SETA} **Servidores:** \`${message.client.guilds.cache.size}\`\n${EMOJI_SETA} **Linguagem:** Node.js\n${EMOJI_SETA} **Versão:** \`14.x\``).setThumbnail(message.client.user.displayAvatarURL());
            await message.channel.send({ embeds: [embed] });
        }

        if (command === 'nicktroll') {
            if (!message.member.permissions.has('ManageNicknames')) return;
            const target = message.mentions.members.first();
            const novoNick = args.slice(1).join(" ") || "cupiditys slave";
            if (!target) return message.reply("Mencione um membro.");
            try {
                await target.setNickname(novoNick);
                await message.channel.send(`${EMOJI_SERVER} Apelido de ${target} alterado!`).then(msg => setTimeout(() => msg.delete(), 3000));
                await message.delete().catch(() => {});
            } catch (e) { await message.channel.send("❌ Erro de hierarquia!"); }
        }

        if (command === 'say') {
            if (message.author.id !== ID_DONO) return;
            const msg = args.join(" ");
            if (!msg) return;
            await message.delete().catch(() => {});
            await message.channel.send(msg);
        }

        if (command === 'embed') {
            if (message.author.id !== ID_DONO) return;
            const btn = new ButtonBuilder().setCustomId('open_embed_modal').setLabel('Abrir Editor').setStyle(ButtonStyle.Primary).setEmoji(EMOJI_SETA);
            const row = new ActionRowBuilder().addComponents(btn);
            await message.channel.send({ content: "Clique abaixo para criar seu embed:", components: [row] });
        }

        if (command === 'userinfo') {
            const m = message.mentions.members.first() || message.member;
            const roles = m.roles.cache.filter(r => r.name !== '@everyone').map(r => r.toString());
            const embed = new EmbedBuilder().setColor(COR_PLATFORM).setAuthor({ name: m.user.username, iconURL: m.user.displayAvatarURL() }).setThumbnail(m.user.displayAvatarURL())
                .setDescription(`${EMOJI_SETA} **Tag:** ${m}\n${EMOJI_SETA} **ID:** \`${m.id}\`\n${EMOJI_SETA} **Criado:** <t:${Math.floor(m.user.createdTimestamp / 1000)}:D>\n${EMOJI_SETA} **Entrou:** <t:${Math.floor(m.joinedTimestamp / 1000)}:R>\n──────────────────────────────\n${EMOJI_SERVER} **Cargos (${roles.length}):**\n${roles.slice(0, 5).join(' ') || 'Nenhum'}`);
            await message.channel.send({ embeds: [embed] });
        }

        if (command === 'avatar') {
            const m = message.mentions.users.first() || message.author;
            const embed = new EmbedBuilder().setTitle(`Avatar de ${m.username}`).setImage(m.displayAvatarURL({ size: 2048 })).setColor(COR_PLATFORM);
            await message.channel.send({ embeds: [embed] });
        }

        if (command === 'banner') {
            const m = message.mentions.users.first() || message.author;
            const user = await message.client.users.fetch(m.id, { force: true });
            if (!user.bannerURL()) return message.reply("❌ Sem banner.");
            const embed = new EmbedBuilder().setTitle(`Banner de ${m.username}`).setImage(user.bannerURL({ size: 2048 })).setColor(COR_PLATFORM);
            await message.channel.send({ embeds: [embed] });
        }

        if (command === 'lock') {
            if (!message.member.permissions.has('ManageChannels')) return;
            await message.channel.permissionOverwrites.edit(message.guild.roles.everyone, { SendMessages: false });
            for (const id of CARGOS_WHITELIST) {
                const role = message.guild.roles.cache.get(id);
                if (role) await message.channel.permissionOverwrites.edit(role, { SendMessages: true });
            }
            await message.channel.send(`${EMOJI_SETA} Canal trancado com sucesso!`);
        }

        if (command === 'unlock') {
            if (!message.member.permissions.has('ManageChannels')) return;
            await message.channel.permissionOverwrites.edit(message.guild.roles.everyone, { SendMessages: true });
            for (const id of CARGOS_WHITELIST) {
                const role = message.guild.roles.cache.get(id);
                if (role) await message.channel.permissionOverwrites.delete(role);
            }
            await message.channel.send(`${EMOJI_SETA} Canal destrancado com sucesso!`);
        }

        if (command === 'ping') {
            await message.channel.send(`${EMOJI_SERVER} Pong! **${message.client.ws.ping}ms**`);
        }

        if (command === 'slowmode') {
            if (!message.member.permissions.has('ManageChannels')) return;
            const seg = parseInt(args[0]) || 0;
            await message.channel.setRateLimitPerUser(seg);
            await message.channel.send(`${EMOJI_SETA} Modo lento: **${seg}s**.`);
        }

        if (command === 'help') {
            const embed = new EmbedBuilder().setDescription(`${EMOJI_SERVER} **Central de Ajuda**`).setColor(COR_PLATFORM);
            const select = new StringSelectMenuBuilder().setCustomId('help_select').setPlaceholder('Selecione uma categoria...')
                .addOptions([{ label: 'Utilitários', description: 'Comandos gerais', value: 'utilitarios', emoji: EMOJI_SETA }, { label: 'Moderação', description: 'Comandos de staff', value: 'moderacao', emoji: EMOJI_SETA }]);
            await message.channel.send({ embeds: [embed], components: [new ActionRowBuilder().addComponents(select)] });
        }
    },

    async onInteraction(i) {
        if (i.isButton() && i.customId === 'open_embed_modal') {
            if (i.user.id !== ID_DONO) return i.reply({ content: "❌ Negado.", ephemeral: true });
            const modal = new ModalBuilder().setCustomId('embed_modal').setTitle('Criar Embed Personalizado');
            modal.addComponents(
                new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('titulo').setLabel('Título').setStyle(TextInputStyle.Short).setRequired(true)),
                new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('descricao').setLabel('Descrição').setStyle(TextInputStyle.Paragraph).setRequired(true)),
                new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('cor').setLabel('Cor Hex').setPlaceholder('#5603AD').setRequired(false)),
                new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('imagem').setLabel('URL Imagem').setRequired(false))
            );
            await i.showModal(modal);
        }
        if (i.isModalSubmit() && i.customId === 'embed_modal') {
            const t = i.fields.getTextInputValue('titulo');
            const d = i.fields.getTextInputValue('descricao');
            const c = i.fields.getTextInputValue('cor') || '#5603AD';
            const im = i.fields.getTextInputValue('imagem');
            const embed = new EmbedBuilder().setTitle(t).setDescription(d).setColor(c.startsWith('#') ? parseInt(c.slice(1), 16) : COR_PLATFORM).setTimestamp();
            if (im && im.startsWith('http')) embed.setImage(im);
            embed.setFooter({ text: `Enviado por: ${i.user.username}`, iconURL: i.user.displayAvatarURL() });
            await i.channel.send({ embeds: [embed] });
            await i.reply({ content: `${EMOJI_SETA} Embed enviado!`, ephemeral: true });
        }
        if (i.isStringSelectMenu() && i.customId === 'help_select') {
            const val = i.values[0];
            let txt = val === 'utilitarios' ? "ping, afk, serverinfo, botinfo, userinfo, avatar, banner" : "nicktroll, say, embed, lock, unlock, slowmode";
            await i.update({ embeds: [new EmbedBuilder().setTitle(val.toUpperCase()).setDescription(`\`${txt}\``).setColor(COR_PLATFORM)], components: i.message.components });
        }
    }
};









