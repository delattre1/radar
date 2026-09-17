#!/usr/bin/env python3
"""Resolve a spoken moment into an absolute one-shot schedule for `cronjob`.

Ground version: standard library only. No key, no network, nothing to install.

Whose clock?
    A relative delay ("in 20 minutes") has no zone and needs none.
    A wall-clock time ("tomorrow at 9") belongs to the person who said it, and
    this script never assumes that is the server. The zone is resolved in this
    order, and the answer is always reported back in "zone" / "zone_source":

        1. --tz          the person's zone, as the agent discovered it
        2. HERMES_TIMEZONE   whatever the installer configured
        3. the server's own zone   -- a fallback, flagged as one

    Anything but (1) is announced in "assumed" whenever a wall clock is
    involved, so the agent can confirm it instead of quietly being hours off.

Usage:
    python3 quando.py "amanha as 9" --tz America/Sao_Paulo
    python3 quando.py "in 20 minutes"
    python3 quando.py "friday afternoon" --tz Europe/Lisbon --now 2026-09-13T19:00:00+01:00

Prints one JSON object on stdout.

Exit 0  -- resolved. Pass ["schedule"] straight to cronjob(action="create").
Exit 2  -- not understood, or already past. ASK the person; never guess.
"""

import argparse
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9
    ZoneInfo = None


MINUTES = {
    "m": 1, "min": 1, "mins": 1, "minuto": 1, "minutos": 1,
    "minute": 1, "minutes": 1,
    "h": 60, "hr": 60, "hrs": 60, "hora": 60, "horas": 60,
    "hour": 60, "hours": 60,
    "d": 1440, "dia": 1440, "dias": 1440, "day": 1440, "days": 1440,
    "semana": 10080, "semanas": 10080, "week": 10080, "weeks": 10080,
    # The diminutive is not decoration in spoken Brazilian Portuguese -- it is
    # how a short delay is normally said out loud. "daqui a 5 minutinhos" is
    # more likely in a voice message than "daqui a 5 minutos".
    "minutinho": 1, "minutinhos": 1, "mininho": 1, "mininhos": 1,
    "horinha": 60, "horinhas": 60,
    "diazinho": 1440, "diazinhos": 1440,
    "semaninha": 10080, "semaninhas": 10080,
}

# The words that announce a delay. Named once: the delay branch matches on it,
# and so does the guard that keeps an unrecognised delay away from the clock.
DELAY_LEAD = r"(?:em|daqui a|daqui|dentro de|in|after)"

# Nobody speaks an exact delay. "daqui a UNS 10 minutos" is the ordinary form,
# and the hedge sits between the lead and the number.
VAGUE = r"(?:uns|umas|mais ou menos|cerca de|aproximadamente|about|around|like)"

# Speech gives numbers as words at least as often as digits -- a transcript
# reads "daqui a cinco minutos" exactly as readily as "daqui a 5 minutos".
NUMBER_WORDS = {
    "um": 1, "uma": 1, "one": 1,
    "dois": 2, "duas": 2, "two": 2,
    "tres": 3, "three": 3,
    "quatro": 4, "four": 4,
    "cinco": 5, "five": 5,
    "seis": 6, "six": 6,
    "sete": 7, "seven": 7,
    "oito": 8, "eight": 8,
    "nove": 9, "nine": 9,
    "dez": 10, "ten": 10,
    "onze": 11, "eleven": 11,
    "doze": 12, "twelve": 12,
    "treze": 13, "thirteen": 13,
    "quatorze": 14, "catorze": 14, "fourteen": 14,
    "quinze": 15, "fifteen": 15,
    "vinte": 20, "twenty": 20,
    "trinta": 30, "thirty": 30,
    "quarenta": 40, "forty": 40,
    "cinquenta": 50, "fifty": 50,
    "sessenta": 60, "sixty": 60,
}

# Longest first, so "cinquenta" is never shortened to "cinco" by the alternation.
NUMBER_ALTERNATION = "|".join(
    sorted((re.escape(w) for w in NUMBER_WORDS), key=len, reverse=True)
)


def read_number(token):
    """Return an int from '20' or from 'vinte'. None when it is neither."""
    token = token.strip()
    if token.isdigit():
        return int(token)
    return NUMBER_WORDS.get(token)


WEEKDAYS = {
    "segunda": 0, "seg": 0, "monday": 0, "mon": 0,
    "terca": 1, "ter": 1, "tuesday": 1, "tue": 1,
    "quarta": 2, "qua": 2, "wednesday": 2, "wed": 2,
    "quinta": 3, "qui": 3, "thursday": 3, "thu": 3,
    "sexta": 4, "sex": 4, "friday": 4, "fri": 4,
    "sabado": 5, "sab": 5, "saturday": 5, "sat": 5,
    "domingo": 6, "dom": 6, "sunday": 6, "sun": 6,
}

# Hour assumed when a person names a stretch of day instead of a clock time.
# Every use of this table is reported in "assumed" so it can be corrected.
PERIODS = {
    "madrugada": 3,
    "manha": 9, "manhazinha": 9, "morning": 9,
    "meio-dia": 12, "meio dia": 12, "almoco": 12, "noon": 12,
    "tarde": 14, "afternoon": 14,
    "noite": 20, "evening": 20, "night": 20, "tonight": 20,
    # Bare "noite" resolved and bare "tonight" asked, which is the asymmetry
    # this table exists to avoid. `\b` keeps "night" out of "midnight".
    "midnight": 0, "midday": 12,
}


def strip_accents(text):
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def normalize(text):
    text = strip_accents(text.lower().strip())
    text = text.replace("-feira", "")
    return re.sub(r"\s+", " ", text)


def resolve_zone(requested=None):
    """Return (tzinfo, name, source). Never raises on a bad zone name."""
    if requested:
        if ZoneInfo is not None:
            try:
                return ZoneInfo(requested), requested, "person"
            except Exception:
                pass  # Fall through; the bad name is reported by the caller.
        else:
            return None, requested, "unavailable"

    configured = (os.environ.get("HERMES_TIMEZONE") or "").strip()
    if configured and ZoneInfo is not None:
        try:
            return ZoneInfo(configured), configured, "installer"
        except Exception:
            pass

    local = datetime.now().astimezone()
    return local.tzinfo, str(local.tzname() or local.utcoffset()), "server"


# The read-back stamp. It is deliberately NOT a phrase in any language, and
# deliberately NOT day/month.
#
# It used to be "%d/%m as %H:%M". Two defects, found 17/09/2026:
# `as` is a Portuguese word handed to whoever installs this, and day/month
# flips silently for an American reader -- "05/09" is 5 September here and
# 9 May there, and the reminder fires on the date this skill exists to get
# right. Year-first is ambiguous to nobody and belongs to no language.
#
# The agent restates this in the person's own words and date convention. This
# is machine output, not a sentence to paste.
HUMAN_FORMAT = "%Y-%m-%d %H:%M"

ZONE_NOTE = {
    "person": None,
    "installer": "fuso nao confirmado com a pessoa: usei %s, o que o instalador configurou",
    "server": "fuso nao confirmado com a pessoa: usei %s, o relogio do servidor",
}


def find_time(text):
    """Return (hour, minute, source) or None. Never invents a time."""
    # A leading `\b` demands a word boundary between "3" and "pm", and a digit
    # beside a letter is not one. Measured 17/09/2026: "3pm" resolved to 03:00
    # while "3 pm" resolved to 15:00 -- twelve hours apart, exit 0, nothing in
    # `assumed`, and the attached form is how English is normally written. The
    # lookbehind takes the digit and still refuses "amanha" and "vieram".
    #
    # The English markers sat empty next to four Portuguese ones, so "friday at
    # 3pm" and "tonight at 8" both landed in the morning.
    ampm = None
    if re.search(
        r"(?<![a-z])(pm|tonight|afternoon|evening|da tarde|a tarde|da noite|a noite)\b",
        text,
    ):
        ampm = "pm"
    elif re.search(r"(?<![a-z])(am|morning|da manha|de manha)\b", text):
        ampm = "am"

    # Trailing `(?!\d)` rather than `\b`, for the same reason: "3:30pm" ended
    # the match at "30" against a following "p", fell through to the branch
    # below, and kept the hour while throwing the minutes away.
    match = re.search(r"\b(\d{1,2})\s*[:h]\s*(\d{2})(?!\d)", text)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
    else:
        match = re.search(r"\b(\d{1,2})\s*h\b", text)
        if not match:
            match = re.search(
                r"\b(?:as|a|at|pras|pra as)\s+(\d{1,2}|%s)\b" % NUMBER_ALTERNATION,
                text,
            )
        if not match:
            match = re.search(r"\b(\d{1,2})\s*(?:am|pm)\b", text)
        if not match:
            return None
        hour, minute = read_number(match.group(1)), 0
        if hour is None:
            return None

    if ampm == "pm" and hour < 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour, minute, match.group(0).strip()


def find_period(text):
    for word, hour in PERIODS.items():
        if re.search(r"\b%s\b" % re.escape(word), text):
            return word, hour
    return None


def resolve(phrase, now, zone_name=None, zone_source="server"):
    """Return (result_dict, ok)."""
    text = normalize(phrase)
    assumed = []
    context = {"zone": zone_name, "zone_source": zone_source, "assumed": assumed}

    def wall_clock_note():
        template = ZONE_NOTE.get(zone_source)
        if template:
            assumed.append(template % zone_name)

    # 1. An ISO stamp the caller already worked out.
    iso = re.search(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{1,2}:\d{2}(?::\d{2})?)?", phrase)
    if iso:
        try:
            moment = datetime.fromisoformat(iso.group(0).replace(" ", "T"))
        except ValueError:
            moment = None
        if moment is not None:
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=now.tzinfo)
                wall_clock_note()
            if moment.hour == 0 and moment.minute == 0 and "T" not in iso.group(0):
                moment = moment.replace(hour=9)
                assumed.append("hora nao dita: assumido 09:00")
            return finish(moment, now, context, text)

    # 2. "em 20 minutos" / "daqui a 2 horas" / "in 30 min" -- relative.
    #    A delay has no zone: it means the same thing anywhere on earth.
    #    "meia hora" is an idiom, not a number and a unit. Rewrite, then match.
    spoken = re.sub(r"\bmeia hor(?:a|inha)\b", "30 minutos", text)
    spoken = re.sub(r"\bhalf an? hour\b", "30 minutes", spoken)

    rel = re.search(
        r"\b%s\s+(?:%s\s+)?(\d+|%s)\s*([a-z]+)"
        % (DELAY_LEAD, VAGUE, NUMBER_ALTERNATION),
        spoken,
    )
    if rel:
        amount, unit = read_number(rel.group(1)), rel.group(2)
        if amount is not None and unit in MINUTES:
            minutes = amount * MINUTES[unit]
            if minutes <= 0:
                return fail("O prazo pedido e zero ou negativo.",
                            "Daqui a quanto tempo, exatamente?")
            # Handed to cron as "in Nm": it fires ONCE. A bare "30m" would
            # mean EVERY 30 minutes -- not the same thing.
            moment = now + timedelta(minutes=minutes)
            return {
                "ok": True,
                "schedule": "in %dm" % minutes,
                "kind": "once",
                "run_at": moment.isoformat(),
                "human": moment.strftime(HUMAN_FORMAT),
                "now": now.isoformat(),
                "zone": zone_name,
                "zone_source": zone_source,
                "zone_matters": False,
                "assumed": assumed,
            }, True

    # 2b. A delay was plainly meant -- "daqui a 5 <something>" -- but the unit
    #     did not land. STOP HERE. Falling through to the wall clock below is
    #     not a harmless retry: there, the "a" of "daqui a 5" is read as the
    #     "as" of a clock time, so "daqui a 5 minutinhos" resolves to 05:00
    #     tomorrow and exits 0. A wrong hour that looks like success is the one
    #     failure this whole script exists to prevent -- and no list of known
    #     units ever closes it, because the next person says it another way.
    #     The lookahead spares "em 20 de setembro": a spoken date is not a
    #     delay, and it belongs to the branch below, which asks its own way.
    if re.search(
        r"\b%s\s+(?:%s\s+)?(?:\d+|%s)\b(?!\s+de\b)"
        % (DELAY_LEAD, VAGUE, NUMBER_ALTERNATION),
        spoken,
    ):
        return fail(
            "Reconheci um prazo relativo em %r, mas nao a unidade de tempo." % phrase,
            "E daqui a quanto tempo? Minutos, horas ou dias?",
        )

    # 3. A day anchor, with or without a clock time. All of this is wall clock.
    day = None
    if re.search(r"\bdepois de amanha\b", text):
        day = now.date() + timedelta(days=2)
    elif re.search(r"\bamanha|tomorrow\b", text):
        day = now.date() + timedelta(days=1)
    elif re.search(r"\bhoje|today\b", text):
        day = now.date()
    else:
        for word, index in WEEKDAYS.items():
            if re.search(r"\b%s\b" % word, text):
                ahead = (index - now.weekday()) % 7
                if ahead == 0:
                    ahead = 7  # "sexta" said on a Friday means the next one.
                    assumed.append("hoje ja e esse dia: marcado para a semana que vem")
                day = now.date() + timedelta(days=ahead)
                break

    clock = find_time(text)
    period = find_period(text)

    if day is None and clock is None and period is None:
        return fail("Nao reconheci nenhuma expressao de tempo em %r." % phrase,
                    "Para quando e isso?")

    wall_clock_note()

    if clock is not None:
        hour, minute, _ = clock
    elif period is not None:
        word, hour = period
        minute = 0
        assumed.append("hora nao dita: assumido %02d:00 (%s)" % (hour, word))
    else:
        hour, minute = 9, 0
        assumed.append("hora nao dita: assumido 09:00")

    if day is None:
        # A clock time with no day: today if it is still ahead, else tomorrow.
        day = now.date()
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            day = day + timedelta(days=1)
            assumed.append("esse horario ja passou hoje: marcado para amanha")

    moment = datetime.combine(day, now.timetz()).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    return finish(moment, now, context, text)


def finish(moment, now, context, text):
    if moment <= now:
        return fail(
            "O momento resolvido (%s) ja passou." % moment.isoformat(),
            "Isso ja passou. Voce quer marcar para quando?",
        )
    return {
        "ok": True,
        "schedule": moment.isoformat(),
        "kind": "once",
        "run_at": moment.isoformat(),
        "human": moment.strftime(HUMAN_FORMAT),
        "now": now.isoformat(),
        "zone": context["zone"],
        "zone_source": context["zone_source"],
        "zone_matters": True,
        "assumed": context["assumed"],
    }, True


def fail(reason, ask):
    return {"ok": False, "reason": reason, "ask": ask}, False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phrase", help="What the person said about when.")
    parser.add_argument("--tz", help="The person's IANA zone, e.g. Europe/Lisbon.")
    parser.add_argument("--now", help="Override the clock (aware ISO). Testing only.")
    args = parser.parse_args(argv)

    tzinfo, zone_name, zone_source = resolve_zone(args.tz)
    if args.tz and zone_source != "person":
        json.dump({
            "ok": False,
            "reason": "Fuso %r nao reconhecido nesta maquina." % args.tz,
            "ask": "Em que cidade ou fuso voce esta?",
        }, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 2

    if args.now:
        now = datetime.fromisoformat(args.now)
        # An ISO offset parses to a FIXED offset, which knows nothing about
        # daylight saving. Re-anchor to the real zone so a moment resolved
        # across a DST boundary lands on the right wall clock.
        now = now.replace(tzinfo=tzinfo) if now.tzinfo is None else now.astimezone(tzinfo)
    else:
        now = datetime.now(tzinfo)
    now = now.replace(second=0, microsecond=0)

    result, ok = resolve(args.phrase, now, zone_name, zone_source)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
