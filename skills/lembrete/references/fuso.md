# Whose clock — working it out instead of asking

The zone is **deduced, not requested**. A person who has just installed this
should get a reminder, not a form. Read this when `--handle` came back silent
(exit 2), or when you need to know why the order is the order.

## The chain, in the order things EXIST

The first message is the hard case: the store is empty and they have said
nothing about where they are. So the only rung that exists at first contact is
the one that has to carry the whole thing.

    1. their number     plow_contacts -> area code -> zone       "inferido"
    2. the store        what an earlier run worked out or was told
    3. the question     ONLY when 1 and 2 came back empty
    4. their answer     --tz; becomes the store, outranks the number for good

**Existing early is not outranking.** Their number says where the LINE was
issued; their sentence says where THEY are. Once they have said it, the number
never speaks again — `store_write` refuses to let an inference overwrite their
own word, so a correction cannot be quietly undone by an area code on the next
message.

**The chain runs once, not once per message.** Whatever resolves is written to
the store with its source, so the second reminder is already answered.

## Getting the number

`plow_contacts` returns your owner's contact book, **their own row first**.
That row's handle is what `--handle` wants. In a one-to-one chat the sender is
the owner, so this is them. It costs a tool call, no line credit, and they see
nothing.

The area-code table lives in `scripts/fusos_por_numero.json` — data the script
reads, never text you read. Brazil: every DDD, all four Brazilian zones. The
US: the codes whose zone is unambiguous. Codes that straddle two zones and
Canadian codes are **deliberately absent**, so they fall through to the
question rather than being answered wrongly.

## When the number is silent

Unknown country, a straddling area code, no handle at all. Then, and only
then, ask — and ask for a **place**, not a zone:

    WRONG   "What time zone are you in?"
    RIGHT   "In what part of the world are you?"   (in their language)

Nobody knows their IANA zone. Everybody knows their city. Turn the answer into
a zone with `maps`, which is already in this image:

    cd /opt/hermes/skills/productivity/maps
    python3 scripts/maps_client.py search "Volta Redonda, RJ"
    python3 scripts/maps_client.py timezone -22.521856 -44.1040128

The second answers `America/Sao_Paulo`. Pass it as `--tz`. **`maps` converts a
PLACE into a zone — it never says where a person is.** There is no location
here, no GPS, no device clock.

**No network, or a place it does not know?** Ask their current clock time and
pick the zone that matches. An hour is something anyone can read off the phone
in their hand.

## Never fill `--tz` with a guess

Not from their language, not from the server, not from a hunch. `--tz` is
recorded as `zone_source: "person"` and then outranks their number forever — a
guess passed there is indistinguishable from their own answer, including to the
check that exists to catch it. A zone worked out from their number is passed by
`--handle`, never by `--tz`, precisely so the two stay telling apart.

## When they travel

Nothing here can see it. Their number does not change when they land somewhere
else, and `maps` cannot be asked where they are. **The read-back is the whole
defence:** `["agora"]` puts their own current time in front of them in every
answer, relative delays included. Someone who went to bed in Alaska and woke up
in Norway reads "são 3h da manhã aí agora" at midday and says so.

**Measured 2026-09-17, and it is why the chain exists.** Someone asked, by
voice, for a reminder at nine the next morning. The instance ran in Pacific,
the person was in Brazil, and nothing had been asked. The agent answered *"te
aviso amanhã às 9h"* and scheduled it four hours after the appointment.
Nothing broke, nothing was logged, and the person had no way to know until the
hour passed. Their number began `+55 24`. **The answer was in the message all
along.**
