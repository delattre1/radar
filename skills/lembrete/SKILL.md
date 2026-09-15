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
  lá o do dentista", "adia os Correios pra amanhã", "o que você tem marcado?",
  "guarda esse aí por enquanto". See *Changing what is already set*.

Do **not** use it for recurring routines ("every morning", "toda segunda").
This skill only ever creates one-shot jobs; a routine is a different shape.

## Prerequisites

- The `cronjob` toolset, which exposes a single tool also named `cronjob`.
- A turn that came in from a gateway platform, so `deliver="origin"` resolves to
  this conversation. Created any other way the job has no origin, and delivery
  falls back to the configured home channel instead.
- **The person's time zone, for any wall-clock time.** It is discovered at run
  time and never hardcoded: this agent runs wherever it was installed, and the
  server's own zone is nobody's in particular.
- Nothing else. `scripts/quando.py` is standard library only: no key, no
  network, nothing to install.

## How to Run

Run the resolver through `terminal`, from the skill directory:

    python3 scripts/quando.py "<what the person said about when>" --tz <their zone>

It prints one JSON object.

- **Exit 0** — resolved. Pass `["schedule"]` to `cronjob` verbatim.
- **Exit 2** — not understood, already past, or an unknown zone. Ask the
  question in `["ask"]` and stop. Do not guess.

Read `["zone_source"]` on every success:

| value | what it means |
|---|---|
| `person` | you passed `--tz`; the zone is theirs |
| `installer` | `HERMES_TIMEZONE`, set by whoever installed this agent |
| `server` | nobody chose it — it is just the machine's clock |

Anything but `person` also lands a line in `["assumed"]` whenever the zone
actually matters. Say it out loud; do not let it pass.

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

3. **Know whose clock it is, before resolving a wall-clock time.** Use the zone
   you already learned from this person. If you have never learned it, ask once
   — "what time zone are you in?" — and remember the answer for next time. Do
   not ask again, and do not fall back to the server's zone in silence. A
   relative delay skips this step entirely: it needs no zone — which is yours
   to work out, never to explain. "Fuso horário", "delay" and "relativo" are
   not words the person hears unless you are asking them the question above.

4. **Run the resolver** on whatever the person said about when, passing `--tz`.
   Silent too: no "vou criar o lembrete", no "deixa eu verificar".

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

   **Write the `prompt` in the person's language, not in yours and not in this
   file's.** The reminder turn runs with no conversation history — it sees this
   text and nothing else, so a prompt written in English produces a reminder in
   English no matter what language the person used. Measured 14/09/2026: a
   Portuguese request produced an English `prompt`, which produced an English
   reminder.

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

Answer in the language the person wrote in. Do not switch to English because
this file is in English.

### Changing what is already set

Creating is half of it. The other half is what people actually say next: *deixa
pra lá*, *adia pra amanhã*, *o que eu tenho marcado?*. All of it is the same
`cronjob` tool, with the action changed — nothing new to install.

| They say | Action | What it does |
|---|---|---|
| "deixa pra lá", "cancela" | `remove` | gone, permanently |
| "adia pra amanhã", "muda pra 9h" | `update` with a new `schedule` | keeps the job and its text, rearms it |
| "guarda esse por enquanto" | `pause` | stays, stops firing |
| "volta aquele do dentista" | `resume` | fires again |
| "o que você tem marcado?" | `list` | everything, to read back |
| — | `run` | fires now; see the pitfall below |

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

- **An omitted `deliver` is not a default — it is a silent drop.** It stores as
  `"local"`, and a local job runs, saves its output, and delivers nowhere. The
  origin is captured and stored either way, but it is never consulted unless the
  token `origin` is in `deliver`.
- **`"2h"` means *every* two hours, not *in* two hours.** One-shot by duration
  is `"in 2h"`. The resolver never emits the bare form.
- **A naive timestamp is anchored to the configured Hermes zone**, which may not
  be the person's. Always pass the offset-carrying stamp the resolver returns.
- **The server's zone is not the person's zone, and it is nobody's by default.**
  A container with nothing configured runs in UTC. Scheduling "9am" there sends
  a reminder at 9am UTC — 6am in São Paulo, 1am in California. This is the
  failure that looks like success: the job fires, the log says delivered, and
  the person is simply woken at the wrong hour.
- **Daylight saving moves the wall clock under you.** Most of the United States
  still changes twice a year. Pass the IANA zone name — `America/Los_Angeles`,
  not a fixed `-08:00` — so the offset is computed for the target date, not
  today's.
- **A time that already passed is not a reminder.** The resolver refuses it
  rather than scheduling something that can never fire.
- **A weekday name said on that same weekday means next week.** The resolver
  says so in `["assumed"]`; pass that on rather than quietly moving the date.
- **A voice message may arrive already transcribed, translated, and wrong**, and
  the original audio is not kept. There is nothing to recover from later — the
  read-back carried by the step 8 confirmation is the only defence.
- **Rescheduling a PAUSED job does not wake it up.** `update` rearms a job when
  it sets a new `schedule` — `state` back to `scheduled`, `enabled` true — but
  it checks first, and a job whose state is `paused` is left paused. The date
  moves and nothing ever fires. Read this in the source, 15/09/2026:
  `if job.get("state") != "paused"`. If someone postpones something they had
  parked, `resume` it too, and say it landed.
- **`run` fires in the background and returns immediately.** It hands back a
  handle, and the outcome re-enters the conversation on its own when the job is
  done. Do not wait for it, do not poll it, and do not tell the person it has
  already been delivered. It is for testing a reminder, not for delivering one
  early — early delivery is `update` with a sooner time.
- **`remove` has no undo, and it is not the same as `pause`.** "Deixa pra lá"
  usually is a cancel and `remove` is right. "Guarda isso por enquanto" is not —
  that is `pause`, and removing it throws away text the person wrote.
- **Narrating the gear reads as a different product.** Nothing is wrong except
  that the person was shown the inside of the skill — and that is the whole
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

must print `2026-09-14T09:00:00-03:00` and exit 0. The same words in another
zone must give another instant:

    python3 scripts/quando.py "tomorrow at 9" --tz America/Los_Angeles \
        --now "2026-10-31T19:00:00-07:00"

must print `2026-11-01T09:00:00-08:00` — the offset changes across the
daylight-saving boundary while the wall clock stays at 9. And

    python3 scripts/quando.py "preciso ir no correio" --tz America/Sao_Paulo

must exit 2 with a question rather than inventing a deadline.
