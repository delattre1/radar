"""Authoring and behaviour checks for the `lembrete` skill.

Standard library only — `unittest` ships with Python, so these run on a
stranger's machine with nothing installed. Same rule the skill itself obeys.

    python3 tests/skills/test_lembrete_skill.py
    python3 -m unittest discover -s tests -v

The authoring ruler lives in test_authoring.py, which checks every skill.

No network, no scheduler, no container: the resolver is imported straight from
the skill directory and driven with a frozen clock, so a pass here means the
same thing anywhere.

The zone cases are not decoration. This agent is installed by strangers, and
the people who verify it sit in the United States, where daylight saving still
moves the wall clock twice a year. A reminder an hour off is a broken reminder.
"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "lembrete"
SKILL_MD = SKILL_DIR / "SKILL.md"
RESOLVER = SKILL_DIR / "scripts" / "quando.py"

# A Sunday, 19:00 local, wherever "local" happens to be.
NOW = "2026-09-13T19:00:00"
BR = "America/Sao_Paulo"
LA = "America/Los_Angeles"
NY = "America/New_York"


def load_resolver():
    spec = importlib.util.spec_from_file_location("quando", RESOLVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


quando = load_resolver()


def resolve(phrase, now=NOW, tz=BR):
    """Drive the resolver with an explicit zone and a frozen clock."""
    tzinfo, name, source = quando.resolve_zone(tz)
    moment = datetime.fromisoformat(now)
    moment = moment.replace(tzinfo=tzinfo) if moment.tzinfo is None \
        else moment.astimezone(tzinfo)
    return quando.resolve(phrase, moment, name, source)


class WhatTheSkillExistsFor(unittest.TestCase):

    def test_a_stated_deadline_is_never_dropped(self):
        """The measured defect: a time was given, and stored as 'not informed'."""
        result, ok = resolve("preciso ir no correio amanha as 9")
        self.assertTrue(ok)
        self.assertEqual(result["schedule"], "2026-09-14T09:00:00-03:00")
        self.assertEqual(result["assumed"], [])

    def test_no_time_said_means_ask_not_guess(self):
        result, ok = resolve("preciso ir no correio")
        self.assertFalse(ok)
        self.assertIn("?", result["ask"])
        self.assertNotIn("schedule", result)

    def test_relative_delay_fires_once_not_every(self):
        """A bare '20m' would recur forever; 'in 20m' is the one-shot form."""
        result, ok = resolve("em 20 minutos")
        self.assertTrue(ok)
        self.assertEqual(result["schedule"], "in 20m")
        self.assertEqual(result["kind"], "once")
        self.assertIsNone(re.fullmatch(r"\d+m", result["schedule"]))

    def test_absolute_stamps_carry_an_explicit_offset(self):
        result, ok = resolve("sexta as 14h")
        self.assertTrue(ok)
        self.assertIsNotNone(datetime.fromisoformat(result["schedule"]).utcoffset())

    def test_known_phrases(self):
        for phrase, expected in [
            ("amanha as 9", "2026-09-14T09:00:00-03:00"),
            ("depois de amanha as 14:30", "2026-09-15T14:30:00-03:00"),
            ("sexta a tarde", "2026-09-18T14:00:00-03:00"),
            ("2026-09-20T10:00", "2026-09-20T10:00:00-03:00"),
        ]:
            with self.subTest(phrase=phrase):
                result, ok = resolve(phrase)
                self.assertTrue(ok, result)
                self.assertEqual(result["schedule"], expected)

    def test_an_assumed_hour_is_always_declared(self):
        result, ok = resolve("sexta a tarde")
        self.assertTrue(ok)
        self.assertTrue(any("14:00" in line for line in result["assumed"]))

    def test_a_weekday_said_on_that_weekday_means_next_week(self):
        result, ok = resolve("domingo as 10")  # NOW is a Sunday
        self.assertTrue(ok)
        self.assertTrue(result["schedule"].startswith("2026-09-20"))
        self.assertTrue(result["assumed"], "the week-long jump must be declared")

    def test_a_time_already_past_is_refused(self):
        result, ok = resolve("hoje as 18h")  # NOW is 19:00
        self.assertFalse(ok)
        self.assertIn("passou", result["reason"])

    def test_rolling_to_tomorrow_is_declared(self):
        result, ok = resolve("as 7 da noite")  # 19:00 today has passed
        self.assertTrue(ok)
        self.assertTrue(result["schedule"].startswith("2026-09-14"))
        self.assertTrue(result["assumed"], "the roll must be declared")

    def test_period_of_day_words(self):
        for phrase, hour in [("amanha de manha", 9), ("amanha a tarde", 14),
                             ("amanha a noite", 20)]:
            with self.subTest(phrase=phrase):
                result, ok = resolve(phrase)
                self.assertTrue(ok, phrase)
                self.assertEqual(datetime.fromisoformat(result["schedule"]).hour, hour)


class SpeechNotTyping(unittest.TestCase):
    """Real transcripts of real voice messages, once STT stopped forcing English."""

    def test_spoken_durations(self):
        for phrase, expected in [
            ("Preciso que me lembre de, no correio, daqui a cinco minutos, "
             "fazer o despacho dessa encomenda", "in 5m"),
            ("Preciso que me lembre daqui a 5 minutos de ir no correio", "in 5m"),
            ("em meia hora", "in 30m"),
            ("daqui a uma hora", "in 60m"),
            ("in twenty minutes", "in 20m"),
            ("in 30m", "in 30m"),
        ]:
            with self.subTest(phrase=phrase):
                result, ok = resolve(phrase)
                self.assertTrue(ok, result)
                self.assertEqual(result["schedule"], expected)

    def test_a_spelled_out_hour(self):
        result, ok = resolve("amanha as tres da tarde")
        self.assertTrue(ok)
        self.assertEqual(result["schedule"], "2026-09-14T15:00:00-03:00")

    def test_the_transcript_that_started_all_this(self):
        """Forced-English STT turned 'ir no correio' into 'Irenu Correio' and
        lost the deadline. With the hint cleared, the deadline is right there."""
        result, ok = resolve(
            "Preciso que me lembre daqui a 5 minutos de ir no correio e depois "
            "estar essa encomenda é para uma cliente Carla."
        )
        self.assertTrue(ok)
        self.assertEqual(result["schedule"], "in 5m")
        self.assertFalse(result["zone_matters"])


class TheDelayThatBecameAnHour(unittest.TestCase):
    """Measured 13/09, on disk, before any paid test.

    A delay whose unit was not recognised used to fall through to the
    wall-clock branch, where the *a* of "daqui a 5" reads as the *as* of a
    clock time. "daqui a 5 minutinhos" resolved to 05:00 tomorrow and exited
    0 -- no question, no line in "assumed". A reminder nine hours late, that
    every log calls a success.
    """

    def test_the_diminutive_is_how_people_actually_speak(self):
        for phrase, expected in [
            ("daqui a 5 minutinhos", "in 5m"),
            ("daqui a 2 horinhas", "in 120m"),
            ("daqui a 3 diazinhos", "in 4320m"),
            ("em meia horinha", "in 30m"),
        ]:
            with self.subTest(phrase=phrase):
                result, ok = resolve(phrase)
                self.assertTrue(ok, result)
                self.assertEqual(result["schedule"], expected)

    def test_a_hedge_does_not_break_the_delay(self):
        for phrase, expected in [
            ("daqui a uns 10 minutos", "in 10m"),
            ("daqui a mais ou menos 2 horas", "in 120m"),
            ("em cerca de 20 minutos", "in 20m"),
            ("in about 30 minutes", "in 30m"),
        ]:
            with self.subTest(phrase=phrase):
                result, ok = resolve(phrase)
                self.assertTrue(ok, result)
                self.assertEqual(result["schedule"], expected)

    def test_an_unknown_unit_asks_instead_of_reading_a_clock(self):
        """The guard, not the word list. No list of units ever closes this --
        the next person says it a way nobody wrote down."""
        result, ok = resolve("daqui a 5 xablau")
        self.assertFalse(ok, "a delay with an unreadable unit must never resolve")
        self.assertIn("?", result["ask"])
        self.assertNotIn("schedule", result)

    def test_a_spoken_date_is_not_caught_by_the_delay_guard(self):
        """'em 20 de setembro' is a date, not a delay. It still ends in a
        question -- but the question it gets must be about the date."""
        result, ok = resolve("em 20 de setembro")
        self.assertFalse(ok)
        self.assertNotIn("daqui a quanto tempo", result["ask"].lower())


class WhoseClock(unittest.TestCase):
    """The part that decides whether a stranger can use this at all."""

    def test_english_phrases_work_the_same(self):
        result, ok = resolve("tomorrow at 9am", tz=LA)
        self.assertTrue(ok)
        self.assertEqual(result["schedule"], "2026-09-14T09:00:00-07:00")

    def test_the_same_words_mean_different_instants_in_different_zones(self):
        brazil, _ = resolve("amanha as 9", tz=BR)
        california, _ = resolve("amanha as 9", tz=LA)
        self.assertNotEqual(brazil["schedule"], california["schedule"])

    def test_a_wall_clock_survives_the_us_daylight_saving_change(self):
        """31/10/2026 is PDT (-07:00); 01/11 is PST (-08:00). 9am stays 9am."""
        result, ok = resolve("tomorrow at 9", now="2026-10-31T19:00:00", tz=LA)
        self.assertTrue(ok)
        self.assertEqual(result["schedule"], "2026-11-01T09:00:00-08:00")

    def test_new_york_is_not_california(self):
        east, _ = resolve("tomorrow at 9", tz=NY)
        west, _ = resolve("tomorrow at 9", tz=LA)
        self.assertEqual(east["schedule"], "2026-09-14T09:00:00-04:00")
        self.assertEqual(west["schedule"], "2026-09-14T09:00:00-07:00")

    def test_a_zone_that_did_not_come_from_the_person_is_flagged(self):
        tzinfo, name, _ = quando.resolve_zone(LA)
        moment = datetime.fromisoformat(NOW).replace(tzinfo=tzinfo)
        result, ok = quando.resolve("amanha as 9", moment, name, "server")
        self.assertTrue(ok)
        self.assertTrue(any("fuso nao confirmado" in l for l in result["assumed"]))

    def test_a_relative_delay_needs_no_zone_at_all(self):
        result, ok = resolve("in 20 minutes", tz=LA)
        self.assertTrue(ok)
        self.assertFalse(result["zone_matters"])
        self.assertFalse(any("fuso" in line for line in result["assumed"]))

    def test_a_wall_clock_declares_that_the_zone_matters(self):
        result, ok = resolve("amanha as 9", tz=LA)
        self.assertTrue(ok)
        self.assertTrue(result["zone_matters"])


class CommandLineContract(unittest.TestCase):
    """What SKILL.md tells the agent it can rely on."""

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(RESOLVER), *args],
            capture_output=True, text=True,
        )

    def test_exit_code_zero_carries_a_schedule(self):
        done = self.run_cli("amanha as 9", "--tz", BR,
                            "--now", "2026-09-13T19:00:00-03:00")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)["schedule"],
                         "2026-09-14T09:00:00-03:00")

    def test_exit_code_two_carries_a_question(self):
        done = self.run_cli("preciso ir no correio", "--tz", BR,
                            "--now", "2026-09-13T19:00:00-03:00")
        self.assertEqual(done.returncode, 2)
        payload = json.loads(done.stdout)
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["ask"])

    def test_an_unknown_zone_asks_instead_of_falling_back_silently(self):
        done = self.run_cli("amanha as 9", "--tz", "Mars/Olympus_Mons")
        self.assertEqual(done.returncode, 2)
        payload = json.loads(done.stdout)
        self.assertFalse(payload["ok"])
        self.assertIn("?", payload["ask"])


class TheGuardAndTheMemory(unittest.TestCase):
    """The 2026-09-17 defect, and the two things that stop it repeating.

    What happened: someone asked for "amanha as 9" on an instance running in
    Pacific. The resolver said the zone came from the server and said so in
    `assumed`. The agent scheduled it anyway and answered "te aviso amanha as
    9h" -- four hours off, with nothing broken and nothing logged.

    A note the caller can read past is not a guard. These check the two that
    do not depend on anyone choosing to obey: the schedule is WITHHELD, and
    the answer is REMEMBERED by the script rather than by the agent.
    """

    def setUp(self):
        self.store = Path(tempfile.mkdtemp()) / "fuso.json"

    def tearDown(self):
        shutil.rmtree(self.store.parent, ignore_errors=True)

    def run_cli(self, *args):
        env = dict(os.environ)
        env["LEMBRETE_STORE"] = str(self.store)
        env.pop("HERMES_TIMEZONE", None)   # the installer must not stand in
        return subprocess.run(
            [sys.executable, str(RESOLVER), *args],
            capture_output=True, text=True, env=env,
        )

    def test_a_wall_clock_nobody_named_a_zone_for_is_refused(self):
        """The whole point: no schedule comes back, so none can be created."""
        done = self.run_cli("amanha as 9")
        self.assertEqual(done.returncode, 2)
        payload = json.loads(done.stdout)
        self.assertFalse(payload["ok"])
        self.assertNotIn("schedule", payload)
        self.assertIn("?", payload["ask"])

    def test_the_zone_is_remembered_without_the_agent_deciding_to_save_it(self):
        first = self.run_cli("amanha as 9", "--tz", BR)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(json.loads(self.store.read_text())["zone"], BR)

        # Same question, no --tz, a run later. It must not ask again, and the
        # answer still belongs to the person -- not to the server.
        again = self.run_cli("amanha as 9")
        self.assertEqual(again.returncode, 0, again.stderr)
        payload = json.loads(again.stdout)
        self.assertEqual(payload["zone"], BR)
        self.assertEqual(payload["zone_source"], "person")
        self.assertEqual(payload["assumed"], [])

    def test_a_corrupt_store_asks_rather_than_guessing(self):
        self.store.write_text("{not json at all")
        self.assertEqual(self.run_cli("amanha as 9").returncode, 2)

    def test_a_resolved_wall_clock_carries_the_three_read_back_numbers(self):
        done = self.run_cli("amanha as 9", "--tz", BR,
                            "--now", "2026-09-13T19:00:00-03:00")
        payload = json.loads(done.stdout)
        self.assertEqual(payload["agora"], "2026-09-13 19:00")
        self.assertEqual(payload["human"], "2026-09-14 09:00")
        self.assertEqual(payload["daqui"], "14:00")

    def test_a_relative_delay_publishes_no_wall_clock_it_cannot_vouch_for(self):
        """Found while building the guard, and wider than the bug we chased.

        A delay needs no zone to SCHEDULE, so `zone_matters` is False and
        nothing was ever flagged -- but `human` was still rendered in the
        server's zone, and step 8 tells the agent to read `human` back. On a
        UTC server that is a sentence three hours wrong about a reminder that
        fires correctly.
        """
        blind = json.loads(self.run_cli("daqui a 10 minutos").stdout)
        self.assertIsNone(blind["human"])
        self.assertIsNone(blind["agora"])
        self.assertEqual(blind["daqui"], "0:10")   # true on every clock

        told = json.loads(self.run_cli("daqui a 10 minutos", "--tz", BR,
                                       "--now", "2026-09-13T19:00:00-03:00").stdout)
        self.assertEqual(told["agora"], "2026-09-13 19:00")
        self.assertEqual(told["human"], "2026-09-13 19:10")


if __name__ == "__main__":
    unittest.main(verbosity=2)
