# Pitfalls of the `cronjob` tool itself

Read when a job behaves oddly. These are about the tool, not about time — the
time ones stay in `SKILL.md`, where they are the point.

- **An omitted `deliver` is not a default — it is a silent drop.** It stores as
  `"local"`, and a local job runs, saves its output, and delivers nowhere. The
  origin is captured and stored either way, but it is never consulted unless the
  token `origin` is in `deliver`.

- **`"2h"` means *every* two hours, not *in* two hours.** One-shot by duration
  is `"in 2h"`. The resolver never emits the bare form.

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
