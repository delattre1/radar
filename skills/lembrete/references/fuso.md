# Whose clock — getting a zone from a person who has never been asked

Read this when step 4 comes back **exit 2 asking where they are**. That happens
once per person, ever. After it, the resolver knows and never asks again.

## Ask for a place, not a zone

    WRONG   "What time zone are you in?"
    RIGHT   "In what part of the world are you?"   (in their language)

Nobody knows their IANA zone. Everybody knows their city. "Brasília?", "summer
time?" and silence are the three answers the wrong question gets, and none of
them is a zone.

## Turn the place into a zone

Two commands, no key, no account, works everywhere:

    cd /opt/hermes/skills/productivity/maps
    python3 scripts/maps_client.py search "Volta Redonda, RJ"
    python3 scripts/maps_client.py timezone -22.521856 -44.1040128

The second one answers `America/Sao_Paulo`. Pass that as `--tz` and run step 4
again. **It is stored from then on** — by the resolver, not by you.

Why a place and not the phone number, which you could look up without asking:
the number says where the LINE was issued. In the United States people keep
their number when they move state, Australian and Russian mobiles carry no
region at all, and anyone travelling is somewhere their number is not. A place
they just told you is where their body is, which is what a morning alarm is
about.

## When maps cannot answer

No network, or a place it does not know. **Ask for their current clock time**
and choose the zone that matches it. An hour is something anyone can read off
the phone in their hand.

## Never fill `--tz` with a guess

Not from their language, not from their number, not from the server. A guess
passed here is recorded as `zone_source: "person"` and is then indistinguishable
from their own answer — including to the check that exists to catch it.

**Measured 2026-09-17.** Someone asked, by voice, for a reminder at nine the
next morning. The instance ran in Pacific, the person was in Brazil, and the
zone was never asked about. The resolver reported the zone as the server's; the
agent answered *"te aviso amanhã às 9h"* and scheduled it four hours after the
appointment. Nothing broke, nothing was logged, and the person had no way to
know until the hour passed. That is the failure this file exists to prevent,
and it is why the resolver now refuses instead of warning.
