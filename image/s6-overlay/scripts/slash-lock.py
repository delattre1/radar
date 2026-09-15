"""Close the slash-command gate, as root, after plow-init and before the gateway.

WHY THIS EXISTS

Hermes gates slash commands per platform, per scope, and the switch is the
presence of an admin list: `gateway/slash_access.py` computes
`enabled = bool(admin_ids)`. With no list, gating is not closed -- it is OFF,
and `is_allowed` returns true for everything. A stranger's `/whoami` answers
`Tier: unrestricted - Slash commands: all available`.

That is not only a listing of read-only conveniences. Measured in the image's
own handlers: `/yolo` toggles the dangerous-command approval bypass,
`/approvals` persists that mode profile-wide, `/set_home` repoints the
platform's home channel -- the address this agent delivers reminders to -- and
`/memory` toggles the memory approval gate. An agent whose whole promise is to
stop and ask before the irreversible would be handing the override to whoever
typed first. Plow's verification is eliminatory and its declared criterion is
security; this is the cheapest possible finding against us.

WHY IT CANNOT BE A CONSTANT IN THE IMAGE

The list holds USER ids, and `plow_chat`'s plugin compares them against a chat
participant's own `uid`. That id is different for every install. Baking the
author's id into a public image would make HIM an admin on a stranger's agent,
which is worse than the open door -- it is a back door. So the owner is
discovered at run time, every boot, exactly as this house's law requires of a
name, an hour or a place.

BOTH SCOPES, AND THAT IS NOT A DETAIL

DM and group keep separate lists and `slash_access.py` says so in as many
words: "Admin lists are NOT cross-scope". Writing only the DM list leaves every
group the agent is ever added to wide open -- and a group is precisely where
somebody who is not the owner can type.

WHY IT REUSES plow-init RATHER THAN REIMPLEMENTING IT

Asking Plow who the owner is means a credential, an endpoint, a retry policy
and a response shape -- all of them Plow's, all of them free to change. Upstream
warns in `Identity` that its own endpoints do not serialize alike. So this does
not copy any of that: it imports the image's own `plow-init.py` and calls the
functions that already do it. If Plow changes, that file changes with the image
and this inherits the fix instead of drifting away from it.

HOW IT FAILS, AND WHY NOT THE UPSTREAM WAY

`plow-init` refuses by parking: the oneshot never completes, the gateway never
starts, the agent never answers. That is right for an agent that cannot be told
who it is. It is wrong here. Losing every reminder because a slash-command lock
could not resolve is a cure worse than the disease -- this product's whole value
is arriving on time.

So a failure here degrades instead: a sentinel id nobody can ever present is
written as the sole admin. The gate turns ON (the list is non-empty), no live
person matches it, and with no `user_allowed_commands` nobody runs anything.
The agent still receives, still stores, still delivers. What it refuses is
commands -- from everyone, the owner included, until a later boot resolves the
real owner and replaces the sentinel. Closed, not open, and self-healing.
"""

import importlib.util
import json
import os
import pwd
import sys

from ruamel.yaml import YAML

PLOW_INIT = "/etc/s6-overlay/scripts/plow-init.py"
CONFIG = "/var/lib/hermes/config.yaml"

# What THIS script wrote last time, so it can tell its own past work from a
# choice the owner made by hand.
#
# Without it the two are indistinguishable, and the script stops updating the
# moment it succeeds once -- it reads its own output as somebody's decision and
# backs off forever. That is not theoretical: upstream warns, in `ask_plow`,
# that "a home volume outlives its tenant, and the failure that hides is a new
# tenant answering in the previous one's chat". Applied here, the previous
# tenant would keep every slash command on the new tenant's agent.
#
# Root-owned and root-readable only: the agent has no reason to read it, and
# an agent that could write it could nominate its own admin.
STATE = "/var/lib/hermes/.slash-lock-state"

# The platform this agent actually talks on. It is the one the seed enables and
# the one the plugin registers.
PLATFORM = "plow_chat"

# An id no participant can ever present, so the gate is ON and matches nobody.
# It is deliberately self-describing: whoever finds it in a config is reading a
# failure, not a configuration.
SENTINEL = "__slash_lock_owner_unresolved__"


class Unresolved(Exception):
    """plow-init refused, and we want the refusal as a value, not as a hang."""


def owner_uid() -> str:
    """The uid of the member whose line this is, asked of Plow at run time."""
    spec = importlib.util.spec_from_file_location("plow_init", PLOW_INIT)
    plow_init = importlib.util.module_from_spec(spec)
    # Registrado ANTES de executar, e isso nao e formalidade de importlib: o
    # `plow-init.py` abre com `from __future__ import annotations`, entao
    # `chats: list[Chat]` chega ao pydantic como TEXTO, e ele so resolve esse
    # nome na primeira validacao -- procurando em `sys.modules[__module__]`.
    # Modulo fora do `sys.modules` faz a busca voltar vazia, e `Identity` morre
    # como "is not fully defined". Medido em 14/09/2026, no primeiro boot com o
    # plow-init REAL: as seis provas anteriores usaram um duple, que nao tem
    # anotacao adiada, e por isso passaram por cima do defeito.
    sys.modules[spec.name] = plow_init
    try:
        spec.loader.exec_module(plow_init)
    except Exception:
        # Nao deixar meio-modulo registrado: a proxima tentativa acharia o
        # cadaver em vez de carregar de novo.
        sys.modules.pop(spec.name, None)
        raise

    # Everything in that module refuses by calling park(), which never returns
    # and never completes -- correct for the boot gate, fatal for us. Swapped
    # for an exception so a refusal degrades here instead of hanging the agent.
    def refuse(reason: str):
        raise Unresolved(reason)

    plow_init.park = refuse

    identity = plow_init.ask_plow(plow_init.read_credentials())
    home = plow_init.home_chat(identity)
    owners = [
        participant
        for participant in home.participants
        if isinstance(participant, plow_init.MemberParticipant)
        and participant.role == "owner"
    ]
    # `home_chat` already refuses anything but exactly one owner, so this is a
    # belt-and-braces check rather than a branch anybody expects to take.
    if len(owners) != 1:
        raise Unresolved("home chat holds %d owners, not 1" % len(owners))
    return owners[0].uid


def main() -> int:
    if not os.path.isfile(CONFIG) or os.path.islink(CONFIG):
        print("slash-lock: no config to write; leaving it alone", file=sys.stderr)
        return 0

    try:
        admin = owner_uid()
        resolved = True
    except Exception as error:  # noqa: BLE001 -- any failure degrades, none hangs
        admin = SENTINEL
        resolved = False
        print("slash-lock: could not resolve the owner (%s)" % error, file=sys.stderr)

    # Round-trip, so the comments upstream wrote next to each key survive. A
    # load-and-dump through plain yaml would delete every one of them, in the
    # owner's own file. Measured 13/09/2026: 36 of them live in a real home.
    yaml = YAML()
    yaml.preserve_quotes = True
    with open(CONFIG, encoding="utf-8") as handle:
        config = yaml.load(handle)

    if config is None:
        print("slash-lock: config is empty; leaving it alone", file=sys.stderr)
        return 0

    platforms = config.setdefault("platforms", {})
    platform = platforms.setdefault(PLATFORM, {})
    previous = read_state()

    # SCOPE BY SCOPE, and that is the whole point of this loop.
    #
    # An earlier version asked only about the DM list and returned when it found
    # one. That honoured the owner's choice and quietly left `group_*` unset --
    # which does not mean "closed", it means the gate is OFF in every group the
    # agent is ever added to. A group is exactly where somebody who is not the
    # owner can type. An omission in one scope is not a decision about it, and
    # the default underneath is the open door.
    #
    # So: a scope the owner filled in is left exactly as they wrote it; a scope
    # nobody filled in gets closed. The two never borrow from each other --
    # `slash_access.py` is explicit that admin lists are not cross-scope, so
    # each is written on its own rather than inherited from the other.
    changed = False
    untouched = []
    for admin_key, cmd_key in (
        ("allow_admin_from", "user_allowed_commands"),
        ("group_allow_admin_from", "group_user_allowed_commands"),
    ):
        existing = _as_list(platform.get(admin_key))
        # The owner meant what they wrote -- the same rule the STT script
        # follows. Two things are NOT that, and both must be overwritten:
        #   - our own sentinel, which is a previous boot's failure, not a
        #     choice, and replacing it is the point of running again;
        #   - whatever we ourselves wrote last boot, recorded in STATE. Reading
        #     our own output as the owner's decision is what would let a
        #     previous tenant keep commands on a new tenant's agent.
        ours = _as_list(previous.get(admin_key))
        if existing and SENTINEL not in existing and existing != ours:
            untouched.append(admin_key)
            continue
        if existing != [admin]:
            platform[admin_key] = [admin]
            changed = True
        # Explicit rather than relying on the default: unset already means
        # "non-admins get nothing", but writing it says so to whoever reads the
        # file, and survives a change of default upstream.
        if platform.get(cmd_key) is None:
            platform[cmd_key] = []
            changed = True

    if untouched:
        print("slash-lock: left the owner's own list alone in %s"
              % ", ".join(untouched), file=sys.stderr)
    if not changed:
        return 0  # Already exactly this. Nothing to write.

    tmp = CONFIG + ".slash-lock-tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        yaml.dump(config, handle)

    # The gateway reads this as the agent, not as root.
    hermes = pwd.getpwnam("hermes")
    os.chown(tmp, hermes.pw_uid, hermes.pw_gid)
    os.chmod(tmp, 0o640)
    # Renamed onto the real name, so the config is either untouched or whole.
    os.replace(tmp, CONFIG)

    # Recorded only after the config is safely in place, so a crash between the
    # two leaves the state describing what is really on disk -- never claiming
    # authorship of a write that did not land.
    write_state({key: _as_list(platform.get(key))
                 for key in ("allow_admin_from", "group_allow_admin_from")})

    if resolved:
        print("slash-lock: slash commands restricted to the line's owner", file=sys.stderr)
    else:
        print(
            "slash-lock: OWNER UNRESOLVED -- gate closed against everyone, "
            "including the owner, until a later boot resolves it",
            file=sys.stderr,
        )
    return 0


def read_state() -> dict:
    """What this script wrote last boot. An unreadable state means none."""
    try:
        with open(STATE, encoding="utf-8") as handle:
            state = json.load(handle)
        return state if isinstance(state, dict) else {}
    except Exception:  # noqa: BLE001 -- absent, truncated or not JSON: same answer
        # Treated as "we have never written here". The safe direction: every
        # existing list then reads as the owner's and is left alone, rather
        # than this overwriting a real choice on the strength of a damaged file.
        return {}


def write_state(written: dict) -> None:
    """Record what we just wrote, so the next boot can recognise it as ours."""
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(written, handle)
    os.chmod(tmp, 0o600)
    os.replace(tmp, STATE)


def _as_list(raw):
    """Compare what YAML gave us against a plain list, whatever type it wears."""
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    return list(raw)


def emergency_close() -> None:
    """Last resort: shut the gate with the plainest tools in the image.

    Reached only when the path above raised something nobody predicted. Simply
    giving up there would leave the gate OFF, which is the open door this file
    exists to shut -- a bug of ours must not become a permission for everyone
    else. So this retries with no ruamel, no plow-init, no network: stdlib yaml
    and the sentinel.

    It accepts the one cost that version refuses, because in an emergency the
    order of priorities changes: yaml.safe_dump drops the comments upstream
    wrote. A config that lost its comments is a shame; a gate that stayed open
    through the verification is the product.
    """
    import yaml

    with open(CONFIG, encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    platform = config.setdefault("platforms", {}).setdefault(PLATFORM, {})
    platform["allow_admin_from"] = [SENTINEL]
    platform["group_allow_admin_from"] = [SENTINEL]
    platform["user_allowed_commands"] = []
    platform["group_user_allowed_commands"] = []

    tmp = CONFIG + ".slash-lock-emergency"
    with open(tmp, "w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, allow_unicode=True, sort_keys=False)
    hermes = pwd.getpwnam("hermes")
    os.chown(tmp, hermes.pw_uid, hermes.pw_gid)
    os.chmod(tmp, 0o640)
    os.replace(tmp, CONFIG)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 -- a bug here must not hold the boot
        import traceback

        traceback.print_exc()
        try:
            emergency_close()
            print("slash-lock: emergency close applied after the error above", file=sys.stderr)
        except Exception:
            traceback.print_exc()
            print(
                "slash-lock: COULD NOT CLOSE THE GATE -- slash commands are open "
                "to every sender. Do not request verification in this state.",
                file=sys.stderr,
            )
        # Deliberately 0, even now. This oneshot is a dependency of the gateway:
        # a non-zero exit would keep the agent from ever starting, and losing
        # every reminder is a worse failure than an open command gate that the
        # two lines above name out loud.
        sys.exit(0)
