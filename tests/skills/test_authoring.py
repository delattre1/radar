"""The authoring ruler, applied to every skill this project ships.

Standard library only. Add a skill under `skills/<name>/` and it is checked
here without touching this file.

These rules are THIS HOUSE'S, and the earlier claim that they were "HARDLINE
upstream (`NousResearch/hermes-agent`, checked by tests/skills/
test_authoring_standards.py there)" was retired on 14/09/2026: that file exists
in neither the reading clone nor the image, so the citation was never
checkable. The SHAPE of the ruler still comes from upstream's published
guidance and is worth keeping; the AUTHORITY is ours, and a number here is
changed by measuring, not by quoting. See `CONHECIMENTO.md` § 26.

Behaviour tests for an individual skill live beside this file in
`test_<name>_skill.py`.

    python3 tests/skills/test_authoring.py
"""

import re
import unittest
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"

SECTIONS = [
    "When to Use",
    "Prerequisites",
    "How to Run",
    "Quick Reference",
    "Procedure",
    "Pitfalls",
    "Verification",
]

MARKETING = ("powerful", "complete", "advanced", "comprehensive", "seamless",
             "cutting-edge", "robust", "effortless", "ultimate")

# Imports and constructs that force a platform lock. A skill whose scripts use
# any of these must say so in `platforms:` — upstream audits the claim.
PLATFORM_LOCKED = ("fcntl", "termios", "os.setsid", "signal.SIGKILL",
                   "osascript", "systemctl", "apt-get", "/proc/")


def skills():
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(p for p in SKILLS_DIR.iterdir()
                  if (p / "SKILL.md").is_file())


class AuthoringRuler(unittest.TestCase):

    def setUp(self):
        self.skills = skills()
        if not self.skills:
            self.skipTest("no skills in skills/ yet")

    def frontmatter(self, skill):
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"),
                        "%s: SKILL.md must open with YAML frontmatter" % skill.name)
        return text.split("---\n")[1]

    def field(self, skill, key):
        match = re.search(r'^%s:\s*"?(.+?)"?\s*$' % key, self.frontmatter(skill), re.M)
        self.assertIsNotNone(match, "%s: missing `%s:`" % (skill.name, key))
        return match.group(1)

    def test_name_matches_the_directory(self):
        for skill in self.skills:
            with self.subTest(skill=skill.name):
                self.assertEqual(self.field(skill, "name"), skill.name)

    def test_description_is_one_short_sentence(self):
        """60 chars, and this number was CHECKED — unlike the line ceiling.

        The description is the only part of a skill that travels in every
        single message (CONHECIMENTO.md § 17), so the ruler here is paid
        forever, not per read.

        This test used to carry no justification at all, which is the same
        symptom that exposed the 200-line ceiling in § 26. Measured
        15/09/2026 across the image's 137 optional skills:

            min 38 | median 55 | mean 54 | max 60
            ABOVE 60 CHARS: 0 of 137 (0%)

        A distribution that touches 60 and never crosses it is an enforced
        cap, not a style. No validator was found in the Hermes code, so the
        measurement is what holds this number up — and it holds. Unlike the
        200, this ruler and upstream's practice agree exactly.

        When a description does not fit, shorten the sentence. Raising this
        would hand this house the fattest index line on the shelf.
        """
        for skill in self.skills:
            with self.subTest(skill=skill.name):
                text = self.field(skill, "description")
                self.assertLessEqual(len(text), 60,
                                     "%d chars: %r" % (len(text), text))
                self.assertTrue(text.endswith("."), "must end in a period")
                self.assertEqual(text.count("."), 1, "must be a single sentence")

    def test_description_avoids_marketing_words(self):
        for skill in self.skills:
            lowered = self.field(skill, "description").lower()
            for word in MARKETING:
                with self.subTest(skill=skill.name, word=word):
                    self.assertNotIn(word, lowered)

    def test_description_does_not_repeat_the_name(self):
        for skill in self.skills:
            with self.subTest(skill=skill.name):
                self.assertNotIn(skill.name.lower(),
                                 self.field(skill, "description").lower())

    def test_author_credits_the_human(self):
        for skill in self.skills:
            with self.subTest(skill=skill.name):
                author = self.field(skill, "author")
                self.assertEqual(author, "Matheus Sousa",
                                 "never 'Claude', never 'Hermes Agent'")

    def test_version_and_license_are_declared(self):
        for skill in self.skills:
            with self.subTest(skill=skill.name):
                self.assertRegex(self.field(skill, "version"), r"^\d+\.\d+\.\d+$")
                self.assertTrue(self.field(skill, "license"))

    def test_sections_are_in_the_fixed_order(self):
        for skill in self.skills:
            with self.subTest(skill=skill.name):
                text = (skill / "SKILL.md").read_text(encoding="utf-8")
                self.assertEqual(re.findall(r"^## (.+)$", text, re.M), SECTIONS)

    def test_there_is_an_intro_before_the_first_section(self):
        """Two or three sentences: what it does AND what it does not do."""
        for skill in self.skills:
            with self.subTest(skill=skill.name):
                text = (skill / "SKILL.md").read_text(encoding="utf-8")
                body = text.split("---\n", 2)[2]
                intro = body.split("## ")[0]
                intro = re.sub(r"^#\s+.+$", "", intro, flags=re.M).strip()
                self.assertTrue(intro, "no intro paragraph")
                self.assertGreaterEqual(intro.count("."), 2,
                                        "intro should be 2-3 sentences")

    def test_body_stays_under_the_reading_ceiling(self):
        """The agent reads a skill whole — there is no pagination.

        The reason is sound and measured: a skill body is read in one piece,
        so a runaway file is paid in one gulp. The NUMBER was not. It came
        from `MATERIAL-plow.md`, which says "~200 for a complex skill, ~100
        for a simple one" — a tilde, hardened here into an assert — and it
        justified itself with "every word of the file is paid PER ROUND, not
        per read", which `CONHECIMENTO.md` § 17 measured as false: only the
        frontmatter index line travels every round.

        Measured 14/09/2026 on the 137 optional skills the image ships:
        median 241 lines, 64% of them above 200, largest 1.627. The house's
        own research file had already listed "every skill fits in ~200 lines"
        among the premises it disproved, and said what the real pattern is:
        SIZE FOLLOWS RISK, not complexity.

        So the ceiling stays, to catch a runaway, and the number is the
        house's own: above upstream's median, far below its monsters.
        """
        for skill in self.skills:
            with self.subTest(skill=skill.name):
                lines = (skill / "SKILL.md").read_text(encoding="utf-8").splitlines()
                self.assertLessEqual(len(lines), 300, "%d lines" % len(lines))

    def test_platforms_claim_matches_what_the_scripts_import(self):
        for skill in self.skills:
            declared = self.field(skill, "platforms")
            scripts = sorted((skill / "scripts").glob("*.py")) \
                if (skill / "scripts").is_dir() else []
            for script in scripts:
                source = script.read_text(encoding="utf-8")
                for locked in PLATFORM_LOCKED:
                    with self.subTest(skill=skill.name, script=script.name,
                                      locked=locked):
                        if locked in source:
                            self.assertNotIn("windows", declared,
                                             "%s uses %s but claims windows"
                                             % (script.name, locked))
            if scripts:
                with self.subTest(skill=skill.name):
                    self.assertTrue(declared.startswith("["),
                                    "platforms must be a list")

    def test_scripts_are_runnable_python(self):
        """A script the SKILL.md points at must at least compile."""
        for skill in self.skills:
            if not (skill / "scripts").is_dir():
                continue
            for script in sorted((skill / "scripts").glob("*.py")):
                with self.subTest(skill=skill.name, script=script.name):
                    compile(script.read_text(encoding="utf-8"), str(script), "exec")


if __name__ == "__main__":
    unittest.main(verbosity=2)
