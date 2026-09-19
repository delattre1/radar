# agente-tarefas — agente derivado da imagem base da Plow.
#
# Pino: tag imutável `base-<sha completo do commit>` MAIS o digest, que é como
# o próprio organizador publicou. A tag diz qual commit é; o digest garante que
# o byte não mudou embaixo dela.
#
# POR QUE ESTÁ NO 51f83158 (17/09 20:19 UTC), desde 17/09/2026: ordem direta do
# Dane no `#ai-worth-using-hackathon`, com `@everyone`, nove minutos depois da
# imagem nascer — "atualize a primeira linha do seu Dockerfile", reconstrua,
# confirme que responde, e poste. Esta casa NÃO leu o código deste commit: o
# pino veio da ordem, e a conferência que coube foi a do registro público da
# ECR — a tag existe, é `linux/amd64`, e o digest bate com o que ele deu.
#
# O pino anterior era o 910b8e3 (16/09 20:56 UTC), e ele NÃO estava quebrado —
# o defeito que a ordem descreve, base que só lê o login de um arquivo, era do
# 4747960. Estávamos um pino atrás, não parados.
#
# POR QUE SAIU DO 4747960 (10/09), em 17/09/2026: naquele commit o `plow-init`
# lia a credencial SÓ de `/var/lib/plow/credentials` e rebaixava o ambiente na
# letra — "The file is the ONLY source". A nuvem da Plow entrega pelo AMBIENTE,
# então uma imagem presa ali estaciona esperando um arquivo que nunca chega.
# O commit b78250e inverteu: ambiente primeiro, arquivo como queda até o
# plow#2007. Lido no código dos dois commits e conferido DENTRO da imagem
# construída, não suposto.
#
# ELE ANDA JUNTO COM O `compose.yml`, E AS DUAS MEXIDAS NÃO SE SEPARAM: o mesmo
# b78250e APAGOU do `00-plow-sanitize` a promoção de `credentials.host`. Quem
# subir este pino continuando a montar o `.host` fica sem credencial nenhuma e
# estaciona igual — só que na própria máquina, em vez de na nuvem.
FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-ef0019372ff8bca593611b31ebd2e08f9f1458ff@sha256:a8a2f97ad78b8192d80a984dce81d3bf5a9a883d18cb7b677704913a09b56aee

# A identidade específica deste agente.
#
# O `plow-init` COMPÕE /var/lib/hermes/SOUL.md a cada boot: persona da base
# primeiro, este arquivo depois. As duas convivem — a proteção de segurança da
# base NÃO some, e por isso não é repetida aqui.
#
# NÃO copiar nada por cima de /var/lib/hermes/SOUL.md: é reescrito no boot.
#
# A fonte é o SOUL.md desta pasta, que é o arquivo ratificado. Ele entra na
# imagem com o nome que o plow-init espera. Um arquivo, uma verdade.
COPY --chown=0:0 SOUL.md /opt/hermes/plow-seed/persona.md
# O modo em passo separado: `COPY --chmod=` é só do BuildKit, e um Docker
# padrão ainda escolhe o construtor antigo, onde isso quebra o build.
RUN chmod 0644 /opt/hermes/plow-seed/persona.md

# A PODA. Decidida pelo Matheus em 14/09/2026, e o motivo NÃO é o token: é que
# este agente resolve uma pergunta só. Nas palavras dele — "se ele for resolver
# vários problemas, ele não é o nosso agente, ele é o Hermes de novo". A imagem
# base chega com 62 habilidades e 16 descrições de categoria, e o que delas
# viaja em TODA mensagem é o índice: 6.067 bytes, ~1.520 tokens. Depois desta
# poda são 281 bytes, ~70 tokens. A economia é consequência, não a razão.
#
# Escrita como LISTA DO QUE FICA, e isso é de propósito: habilidade que a imagem
# base ganhar numa atualização já nasce podada, em vez de voltar pela porta dos
# fundos sem ninguém decidir.
#
# `productivity/maps` fica por ordem dele, e cabe no critério: um lembrete de
# "passar nos Correios" que já chega dizendo qual agência e a que distância é o
# mesmo problema chegando resolvido, não um segundo problema. Provada nesta casa
# com o endereço real dele. Sem chave, biblioteca padrão, e faz fuso horário —
# que é matéria-prima do "quando". `DESCRIPTION.md` da categoria vem junto
# porque é ela que descreve a pasta que sobrou.
#
# `index-cache` NÃO é habilidade e não tem `SKILL.md`: não custa nada no índice
# e é cache das habilidades opcionais. Fica.
#
# Antes do COPY das nossas, para a poda não ter de conhecer o nome delas.
RUN for raiz in /var/lib/hermes/skills /opt/hermes/skills; do \
        [ -d "$raiz" ] || continue; \
        find "$raiz" -mindepth 1 -maxdepth 1 \
             ! -name productivity ! -name index-cache -exec rm -rf {} + ; \
        [ -d "$raiz/productivity" ] && \
        find "$raiz/productivity" -mindepth 1 -maxdepth 1 \
             ! -name maps ! -name DESCRIPTION.md -exec rm -rf {} + ; \
    done; true

# As habilidades, nas DUAS cópias, como a imagem base faz. A segunda é de onde
# uma casa que começa vazia é semeada, e é por onde atualização de imagem chega.
# É fonte, não backup: habilidade que o agente apagar fica apagada.
COPY --chown=10000:10000 skills/ /var/lib/hermes/skills/
COPY --chown=10000:10000 skills/ /opt/hermes/skills/

# A configuração que tem de valer na casa que JÁ existe E na de um estranho que
# instale do zero. Essa é a única porta: `cont-init` semeia apenas um
# `config.yaml` AUSENTE, e o `configure()` do plow-init reescreve só as chaves
# de que ele é dono — `stt` não está entre elas. Uma chave posta na semente
# nunca alcançaria a casa do Matheus, que nasceu antes dela.
#
# Roda como root, antes de qualquer serviço, e DEPOIS de `00-plow-sanitize`,
# que é quem semeia o config — a ordem é alfabética, por isso o `01`.
#
# O COPY de diretório MESCLA: o `00-plow-sanitize` da imagem base continua lá.
COPY --chown=0:0 image/cont-init.d/ /etc/cont-init.d/
# O modo em passo separado, pelo mesmo motivo da persona acima: `COPY --chmod=`
# é só do BuildKit. Só os nossos arquivos, nunca a pasta — o script da base tem
# o modo que a base escolheu.
#
# São TRÊS desde 14/09/2026, e os três usam a mesma porta pelo mesmo motivo:
# coisa que precisa valer na casa nascida E na casa nova, por uma porta só. O
# `02` desliga o embrulho de máquina das entregas agendadas
# (`cron.wrap_response`). O `03` conserta o caminho que a habilidade `maps`
# crava e que não existe aqui — não é chave de config, é o texto da habilidade,
# e por isso ele mexe nas DUAS raízes: a casa (volume, que imagem não alcança) e
# o pacote (`/opt/hermes/skills`, de onde uma casa vazia é semeada).
RUN chmod 0755 /etc/cont-init.d/01-stt-language \
                /etc/cont-init.d/02-cron-wrap \
                /etc/cont-init.d/03-maps-path \
                /etc/cont-init.d/04-toolsets

# A trava dos comandos com barra. Sem lista de admin, o portão não fica fechado:
# ele fica DESLIGADO (`enabled = bool(admin_ids)` em `gateway/slash_access.py`), e
# qualquer remetente roda `/yolo`, que desliga a confirmação antes do
# irreversível. É o achado mais barato contra nós numa verificação cujo critério
# declarado é segurança.
#
# Não pode ser constante: a lista é de IDs DE USUÁRIO, diferentes em cada
# instalação. Por isso é um serviço que descobre o dono em execução — depois do
# `plow-init`, que é quem pergunta à Plow quem é o dono, e ANTES do gateway, que
# é quem lê a trava. As duas dependências estão declaradas em `s6-rc.d/`.
COPY --chown=0:0 image/s6-overlay/ /etc/s6-overlay/
RUN chmod 0755 /etc/s6-overlay/scripts/slash-lock.py

# O REPORTER DO AGENT INDEX vem na própria imagem base: o serviço `agent-index`
# e o client em `/opt/plow`. É ele que faz instalação e token CONTAREM no
# placar. SEM `AGENT_ID` no ambiente ele NÃO CHUTA NOME: avisa e dorme.
#
# PARA QUEM ESTE INSTALL REPORTA. Não é segredo e não é por instalação: é a
# PÁGINA do agente no Agent Index, a mesma para todo mundo que instalar o
# RadaR. O Índice aceita uso da chave de qualquer instalador sobre um agente já
# registrado, e cada cópia sorteia o próprio id de instalação — é assim que
# instalação e uso somam na mesma página.
#
#     https://aiworthusing.com/agent-index/radar
#
# ELE MORA AQUI, E NÃO NO `compose.yml`, POR UM MOTIVO MEDIDO EM 17/09: um
# deploy de nuvem (`plow-agents deploy <imagem>@sha --line ln_xxx`) NÃO roda o
# `compose.yml` — sobe a imagem numa VM da Plow, com o ambiente do
# provisionador. Medido dentro da imagem construída: sem esta linha o
# `AGENT_ID` chega VAZIO, o reporter dorme, e o agente funciona perfeitamente
# enquanto o placar não vê nada. É o critério 3 do portão, e é o que não dá
# erro nem aparece em log. O provisionador ainda pode sobrescrever.
ENV AGENT_ID=radar
