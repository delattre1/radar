# agente-tarefas — agente derivado da imagem base da Plow.
#
# Pino: tag imutável `base-<sha completo do commit>`, e o sha é o do commit
# que esta casa LEU no clone de leitura (4747960, de 10/09/2026). Código
# conferido e imagem rodada são o mesmo commit — é isso que a tag compra.
# Digest equivalente, para quem quiser prender mais forte:
#   sha256:fe9b0f428f9ed2da1698ecf0b504c79eceb9e016e770291ff6b3418b9f65449d
FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-4747960eaa8a44ac24424bf0cc6c22559af61f43

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
                /etc/cont-init.d/03-maps-path

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

# O REPORTER DO AGENT INDEX. É ele que faz instalação e token CONTAREM no placar:
# o Índice só sabe o que lhe é reportado, então um agente sem este serviço roda
# igual e pontua zero. Copiado do `life-assistant-hermes-agent`, que é o exemplo
# que a própria Plow manda copiar.
#
# O SERVIÇO NÃO TEM CHAVE DE DESLIGAR, e isso é decisão do upstream, dita na
# letra dentro do `run`: quem não quer reportar constrói a imagem SEM ele. Uma
# chave aqui só criaria um segundo lugar para discordar do Dockerfile.
#
# SEM `AGENT_ID` no ambiente ele NÃO CHUTA NOME: avisa que não há agente para
# reportar e dorme. Por isso esta peça entra ANTES de existir id registrado —
# é fiação inerte até o `AGENT_ID` chegar no `compose.yml`.
#
# O CLIENT É BUSCADO NO BUILD, PINADO POR SHA E CONFERIDO POR SHA256 — as duas
# metades importam e o upstream escreveu por quê: o sha impede que código não
# revisado entre por baixo de um agente que segura credencial viva; a soma
# impede que o host que serve aquele sha troque o conteúdo. O pino mora em
# `vendor/client.pin`, e subir de versão é uma edição que alguém lê.
COPY vendor/client.pin /opt/plow/agent-index-client.pin
RUN set -eu; \
    sha="$(sed -n 's/^sha=//p' /opt/plow/agent-index-client.pin)"; \
    want="$(sed -n 's/^sha256=//p' /opt/plow/agent-index-client.pin)"; \
    path="$(sed -n 's/^path=//p' /opt/plow/agent-index-client.pin)"; \
    curl -fsS --max-time 60 -o /opt/plow/agent-index-client.py \
      "https://raw.githubusercontent.com/plow-pbc/agent-index-client/${sha}/${path}"; \
    got="$(sha256sum /opt/plow/agent-index-client.py | cut -d' ' -f1)"; \
    [ "$got" = "$want" ] || { echo "agent-index client is $got, pin says $want" >&2; exit 1; }; \
    chmod 0644 /opt/plow/agent-index-client.py

# O modo do `run`, em passo separado e pelo MESMO motivo da persona e dos três
# `cont-init` acima: o Windows não guarda bit de execução, e um `run` de longrun
# sem ele não roda. O upstream não precisa deste chmod porque nasce em
# filesystem que guarda o bit — esta casa precisa, e a falta apareceria só no
# boot, como serviço que não sobe.
RUN chmod 0755 /etc/s6-overlay/s6-rc.d/agent-index/run
