---
name: lembrete
description: "Save what must not be forgotten; deliver, move or cancel."
version: 0.1.0
author: Matheus Sousa
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [reminder, deadline, schedule, followup, task]
    category: productivity
    requires_toolsets: [terminal, cronjob]
---

# Lembrete Skill

Turns a commitment mentioned in a message into one scheduled delivery back into
the same conversation, and changes or calls it off afterwards. It handles a
single moment per commitment: it does not keep a task list, does not repeat, and
does not chase an answer. A deadline that was never said is asked for — never
assumed.

## When to Use

- Someone says there is something they must not forget, with or without a time.
- A message carries any expression of time attached to something to do
  ("amanhã às 9", "em 20 minutos", "sexta à tarde", "in two hours").
- A photo or a voice message arrives with a commitment inside it.
- **Someone calls off, moves, or asks about something already set** — "deixa pra
  lá o do dentista", "adia os Correios pra amanhã", "never mind the dentist
  one", "what do I have set?". See *Changing what is already set*.

Do **not** use it for recurring routines ("every morning", "toda segunda").
This skill only ever creates one-shot jobs; a routine is a different shape.

## Prerequisites

- The `cronjob` toolset, which exposes a single tool also named `cronjob`.
- A turn that came in from a gateway platform, so `deliver="origin"` resolves to
  this conversation. Created any other way the job has no origin, and delivery
  falls back to the configured home channel instead.
- **The person's own handle**, from `plow_contacts`. It is what makes their
  zone knowable without asking; the server's own zone is nobody's in particular.
- Nothing else. `scripts/quando.py` is standard library only: no key, no
  network, nothing to install — the area-code table ships beside it.

## How to Run

Run the resolver through `terminal`, from the skill directory:

    python3 scripts/quando.py "<what they said about when>" --handle <their number>

Add `--tz <zone>` only once they have told you. It prints one JSON object.

- **Exit 0** — resolved. Pass `["schedule"]` to `cronjob` verbatim.
- **Exit 2** — not understood, already past, or nothing at all said where they
  are. Ask the question in `["ask"]` and stop. Do not guess.

Read `["zone_source"]` on every success:

| value | what it means |
|---|---|
| `person` | they said it; it outranks their number from now on |
| `inferido` | worked out from their area code — right until they say otherwise |
| `installer` | `HERMES_TIMEZONE`, set by whoever installed this agent |
| `server` | nobody chose it — it is just the machine's clock |

The last two never reach you on a wall clock — the resolver exits 2 instead.
`inferido` lands a line in `["assumed"]`: not a warning to obey, but why
`["agora"]` has to be said out loud.

`--now "<aware ISO>"` overrides the clock, for checking behaviour.

## Quick Reference

| Passed to `cronjob` as `schedule` | What actually happens |
|---|---|
| `"in 20m"` | fires **once**, 20 minutes from now |
| `"2026-09-14T09:00:00-03:00"` | fires **once**, at that exact instant |
| `"20m"` | **every** 20 minutes, forever — almost never a reminder |
| `"every monday 9am"` | recurring — out of scope here |

| `deliver` value | Where the reminder lands |
|---|---|
| `"origin"` | back into this conversation — **always pass this** |
| omitted / `None` | stored as `"local"`: the job runs and reaches **nobody** |
| `"platform:chat_id"` | that exact chat |

The resolver only ever emits the first two `schedule` forms, and it stamps
absolute times with an explicit UTC offset so the instant cannot be
reinterpreted by whatever zone the scheduler runs in.

A delay — `"in 20m"` — means the same thing everywhere on earth and needs no
zone at all; `["zone_matters"]` says so. A wall clock does not: "tomorrow at 9"
is a different instant in São Paulo and in California, and it shifts again
across a daylight-saving change. That is why the zone is an input, not a
setting.

## Procedure

**Steps 1 to 7 are work, and work is silent.** The person hears exactly **one**
message out of this procedure: the confirmation in step 8. The zone, the
resolver, the exit code and the job are machinery, and naming machinery is the
agent describing itself instead of answering. Only a real question — step 3 or
step 5, in their words — may break that silence.

1. **Capture the thing first, in the person's own words.** Write down what must
   not be forgotten before touching the clock. If the commitment is unclear,
   ask about the commitment — not about the time.

2. **If a photo came with the message, reopen it.** Use `vision_analyze` on its
   path under `cache/images/` and describe it in the person's language. Do not
   trust an analysis that arrived pre-attached to the message: it is not
   guaranteed to be in their language, and it is not guaranteed to be about
   what they meant.

3. **Work their clock out — do not ask for it.** Call `plow_contacts`, take the
   handle on your owner's own row (it comes first), pass it as `--handle`.
   Their area code answers it offline, and the resolver keeps the answer: one
   call, never repeated. **Do this on every request, relative delays
   included** — where they are is for their job list, for what the delivery
   says, and for the "na verdade, às 17h" one message later, not just for this
   calculation. **Never fill `--tz` with a guess:** `--tz` is what they *said*,
   and it outranks their number for good. `references/fuso.md` has the rest,
   and is where exit 2 sends you.

4. **Run the resolver** on what they said about when, with `--handle` (and
   `--tz`, if told). Silent: no "vou criar o lembrete", no "deixa eu verificar".

5. **On exit 2, ask and stop.** Never record "prazo não informado" when a time
   *was* said — that is the failure this skill exists to prevent.

6. **Settle what you understood, before creating anything:** the thing, the
   moment from `["human"]`, every line of `["assumed"]`. Voice messages reach
   you translated or garbled, so this reading has to reach the person — it
   reaches them **inside** the step 8 confirmation, never as a message of its
   own announcing what you are about to do.

7. **Create the job:**

       cronjob(
         action="create",
         schedule=<the resolver's "schedule">,
         prompt=<what the future agent should say>,
         name=<a short handle>,
         deliver="origin",
       )

   The `prompt` is spoken later, to someone who has lost the context. Write it
   so it stands on its own: the thing, and enough of the why to act on.

   **It opens with the thing. No preamble, in any language.** Not "this is the
   reminder you asked for", not a greeting. They know they asked.

       WRONG   This é o lembrete que você pediu: levar a encomenda aos
               Correios agora! 📦
       RIGHT   Levar a encomenda aos Correios agora! 📦

   That wrong line is real: it went out on 16/09/2026 and reached this
   project's public demo image. **The English word sits in the preamble, never
   in the thing** — the thing is the person's own words, the preamble is the
   part written from nothing, in the language of whatever was last read. This
   file. A reminder with no preamble has nowhere to leak.

   **Write the `prompt` in the person's language, not in yours and not in this
   file's.** The reminder turn runs with no conversation history — it sees this
   text and nothing else, so a prompt written in English produces a reminder in
   English no matter what language the person used. Measured 14/09/2026: a
   Portuguese request produced an English `prompt`, which produced an English
   reminder. **This is not a rule about Portuguese** — whoever writes in
   English gets English, in German gets German. Follow the person, never a
   language this file or this house happens to use.

   **When the `prompt` carries the person's own words, bind them as WORDS.**
   The turn that fires reads the `prompt` and nothing else, so whatever the
   `prompt` calls those words is what it obeys. Asking it for a *tone* invites
   it to write its own sentence in that tone; asking it for a *text* does not.

       WRONG   Manda pro Davi, exatamente com esse clima: "<o texto dele>"
       RIGHT   Manda pro Davi este texto, palavra por palavra, sem corrigir
               nada: "<o texto dele>"

   That wrong line is real, read out of a stored job on 18/09/2026. The person
   had asked for a phrase in quotes, deliberately misspelled — it was the joke.
   The stored `prompt` said *"com esse clima"*, and what went out nine hours
   later was a third version of the sentence, tidied up. **Quotes around a
   phrase are the plainest thing a person has for saying this is mine: do not
   touch it.** Spelling they chose is part of the phrase, not an error to fix.

   **What that turn says is the whole message.** This house sets
   `cron.wrap_response: false`, so there is no header, no job id and no footer
   around it. Write the `prompt` so the delivery reads as something a person
   would send, not as a job reporting that it ran.

8. **Confirm — ONE message, and it is the only one.** The thing, the moment
   from `["human"]` in plain words, every line of `["assumed"]`, and nothing
   about how you got there. Sent on the real line on 14/09/2026, in this order:

       "Isso é um delay relativo, então não precisa de fuso horário.
        Vou criar o lembrete."
       "Certo, te aviso em 2 minutos pra tirar o bolo do forno."

   The second one alone was the whole answer. When a reply has two paragraphs
   and the first explains the mechanism, the first is not part of the answer.

   **Three numbers go back, always and together** — `["agora"]`, `["human"]`,
   `["daqui"]`:

       "São 23:32 aí agora. Te aviso amanhã às 9h, daqui a 9h28."

   **`["agora"]` is the one that matters and the one you will drop.** The
   moment is their own words returning and cannot sound wrong to them; the gap
   needs arithmetic nobody does. Their own clock they check by glancing at
   their phone, and a wrong zone moves all three at once.

   **Say `["agora"]` on relative delays too, whenever it is not `null`.** It is
   the only way anyone finds out they travelled — nothing here can see that,
   and an hour that does not match the phone in their hand is what tells them.

   **When `["human"]` and `["agora"]` are `null`**, say `["daqui"]` and no
   wall-clock time: an hour invented there would be the server's.

   **`["human"]`, `["assumed"]` and `["ask"]` are machine output — a bare
   `2026-09-18 09:00` and a fixed Portuguese note. Restate them; never paste
   them.** Say the date the way the person writes dates, and the note in their
   language.

### Changing what is already set

Creating is half of it. The other half is what people actually say next: *deixa
pra lá*, *adia pra amanhã*, *o que eu tenho marcado?*. All of it is the same
`cronjob` tool, with the action changed — nothing new to install.

| They say | Action | What it does |
|---|---|---|
| "deixa pra lá", "never mind", "cancel that" | `remove` | gone, permanently |
| "adia pra amanhã", "push it to friday", "make it 9" | `update` with a new `schedule` | keeps the job and its text, rearms it |
| "guarda esse por enquanto", "hold that one for now" | `pause` | stays, stops firing |
| "volta aquele do dentista", "bring back the dentist one" | `resume` | fires again |
| "o que você tem marcado?", "what do I have set?" | `list` | everything, to read back |
| — | `run` | fires now; see `references/cronjob.md` |

**Rule one: always `list` first, and never guess a job id.** The tool says so
itself. `job_id` is required by every action except `list`, and it accepts a
**name**, not only an id.

**Rule two: an ambiguous name is a question, not a guess.** Two jobs matching
one name come back as `success: false` with a `matches` array — id, name,
schedule and next run for each. That is enough to ask *"o do dentista de terça
ou o de quinta?"* in the person's own terms. Never pick one. A name that matches
nothing comes back as not found; say that plainly rather than inventing.

**Postponing is ONE call, not a delete and a recreate:**

    cronjob(
      action="update",
      job_id=<name or id from list>,
      schedule=<the resolver's new "schedule">,
    )

The stored `prompt` survives, so the reminder still says what the person
originally meant. Resolve the new moment exactly as step 4 does — *"adia 1 hora"*
is a relative delay and becomes `"in 1h"`; *"amanhã às 9"* needs the zone. A bare
`"1h"` still means **every** hour.

**`update` only touches what you pass.** A field you omit is left alone; a blank
`name` is treated as "no change", not as an erase. Do not re-send the whole job
to change one thing.

**Confirm the same way step 8 does: one message, in their words.** *"Cancelei o
do dentista."* *"Beleza, os Correios ficam pra amanhã às 9."* No job id, no
action name, no report that a tool ran.

## Pitfalls

- **The mechanics of `cronjob` have their own traps** — a dropped `deliver`, a
  job that recurs instead of firing once, a paused job that will not rearm.
  They are in `references/cronjob.md`, to read when a job behaves oddly.
- **A naive timestamp is anchored to the configured Hermes zone**, which may not
  be the person's. Always pass the offset-carrying stamp the resolver returns.
- **The server's zone is nobody's.** A wall clock that reaches it exits 2 — but
  it only gets there when `--handle` was missing or silent, which is rare.
  Passing the number is what keeps the question away from them.
- **Their number does not move when they do.** Travel is invisible here; the
  `["agora"]` read-back is the only thing that surfaces it.
- **Daylight saving moves the wall clock under you.** The IANA name carries the
  rule; a fixed `-08:00` does not. Both the table and `maps` return IANA names.
- **A time that already passed is not a reminder.** The resolver refuses it
  rather than scheduling something that can never fire.
- **A weekday name said on that same weekday means next week.** The resolver
  says so in `["assumed"]`; pass that on rather than quietly moving the date.
- **A voice message may arrive already transcribed, translated, and wrong.** The
  original audio is kept under `cache/audio/` and can be reopened, but the step
  8 read-back is what catches it while it still matters.
- **Narrating the gear reads as a different product**, and it is the whole
  first impression of whoever installs this. A tool, a step, an exit code and a
  job id are yours; the moment and the thing are theirs.

## Verification

    cronjob(action="list")

The job must show `Deliver: origin`, a `Next run` that matches what you told the
person, and `Repeat: 0/1` — a one-shot. Anything showing an interval means the
bare-duration trap was hit; delete it and recreate with `"in …"`.

To check the resolver itself, without touching the scheduler:

    python3 scripts/quando.py "amanha as 9" --tz America/Sao_Paulo \
        --now "2026-09-13T19:00:00-03:00"

must print `2026-09-14T09:00:00-03:00` and exit 0. The zone is not decoration:
the same words in `America/Los_Angeles` give a different instant, and different
again across a daylight-saving boundary, while the wall clock stays at 9. A
phrase carrying no time at all must exit 2 with a question rather than a date.
All three are asserted in `tests/skills/test_lembrete_skill.py`.
