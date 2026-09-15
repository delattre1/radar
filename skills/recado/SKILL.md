---
name: recado
description: "Draft a ready-to-send message for someone else."
version: 0.1.0
author: Matheus Sousa
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [message, draft, apology, customer, followup, copy]
    category: productivity
    related_skills: [lembrete]
---

# Recado Skill

Writes the message the person will send to somebody else — a customer, a
friend, a boss — ready to copy and paste with nothing to delete first. It
writes one message, not a menu of options, and it never sends anything: the
person is the one who sends it, in whatever app they already use.

## When to Use

- Someone asks for "a text to send to X", "um textinho pra mandar pra ela",
  "help me tell them that…".
- A commitment is running late, changed, or is finally done, and somebody
  outside this conversation needs to hear about it.
- Paired with `lembrete`: the reminder fires and the message is already
  written, so the moment it arrives there is nothing left to compose.

Do **not** use it to send anything. This agent has no reach into WhatsApp,
SMS, or e-mail on the person's behalf. Say so plainly if asked, and hand over
the text instead.

## Prerequisites

None. No script, no key, nothing to install, no network. Drafting is judgment,
not parsing — the work happens in the writing, not in a helper.

What the draft needs before it can be written:

- **who** receives it, and what they are to the person (customer, friend, boss)
- **what happened**, in the person's own words
- **what changes for the recipient** — the part they actually care about

If any of those three is missing, ask for that one thing. Do not invent it,
and do not write around it.

## How to Run

Nothing to run. Produce the message and hand it over like this:

    Texto pra <quem>:

    <the message, and only the message>

    <one line of what to attach or do, when there is one>

The fenced middle is what gets copied. Nothing above or below it may need to
be deleted before sending.

## Quick Reference

| Situation | What the message must carry |
|---|---|
| Running late | that it is late, that it is moving, and when |
| Finally done | that it is done, and what happens next |
| Something changed | the change, and what the recipient must do about it |
| Bad news | the news first, the reason second, never the reverse |

| Rule | Why |
|---|---|
| One message, not three options | options are work handed back to the person |
| The recipient's language | the person may write to you in one and to them in another |
| No subject line unless it is e-mail | a chat message with a subject line reads as a form letter |
| Short enough to read on a phone | that is where it will be read |

## Procedure

1. **Work out who is reading it.** Not the person talking to you — the person
   on the other end. Everything below follows from that.

2. **Pick the language they will read it in.** Ask if it is genuinely unclear;
   otherwise match the language the person used to talk *about* them.

3. **Lead with the thing that matters to the recipient.** They want to know
   what happens to them, not why it happened. The reason comes after, in one
   clause, and never as a defence.

4. **Name what is real and skip what is not.** Use the concrete details you
   were given — the object, the occasion, the date. Never invent a tracking
   code, a delivery window, or a promise that was not made to you.

5. **Say sorry once, plainly, and move on.** An apology repeated three times
   reads as anxiety and asks the recipient to do the comforting.

6. **Write it, then read it as the recipient.** If any line would make them
   ask a follow-up question you already know the answer to, answer it in the
   message instead.

7. **Hand it over in the shape above**, and add the one practical line if
   something has to go with it — a photo they already have, a link, a file.

8. **Offer one change, not a rewrite.** "Quer mais curto, ou mais formal?" is
   enough. Do not produce variants nobody asked for.

## Pitfalls

- **A preamble is a defect.** "Aqui está o texto que preparei:" is one more
  thing to delete. The shape above exists to prevent it.
- **The person's language is not necessarily the recipient's.** A Brazilian
  seller writing to a customer abroad needs the customer's language, not
  theirs.
- **Do not promise on the person's behalf.** "Chega amanhã" is a commitment
  they will have to keep. Unless they said it, do not write it.
- **Do not claim you sent it.** There is no path from here into their
  messaging app. The person sends it.
- **Over-explaining reads as an excuse.** One clause of reason. The recipient
  did not ask for the story.
- **An emoji is not warmth.** Match how the person themself writes; when in
  doubt, leave it out.

## Verification

Read the draft back against these, before handing it over:

- Could it be pasted as-is, with nothing deleted? If not, fix the shape.
- Does it say what changes for the recipient, in the first line or two?
- Is every concrete detail in it something you were actually told?
- Is it one message, in one language, of a length that fits a phone screen?
- Does it avoid claiming any action this agent cannot perform?

If the answer to any of those is no, the draft is not ready to hand over.
