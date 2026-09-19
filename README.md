# RadaR

Takes what you can't forget — typed, shot or spoken — and comes back with it on
time. Never guesses a deadline.

A to-do list waits to be opened. RadaR doesn't wait: you text it whatever you
have, in whatever form you have it, it asks **when**, and then it comes back to
you before the time runs out.

- **Send it anything.** Text, a photo of a receipt, a voice note. It keeps the
  original and works from it.
- **It asks when.** If you didn't say a deadline, it asks instead of inventing
  one. A wrong date is worse than no date.
- **It comes to you.** The reminder arrives as a message at the time you set —
  nobody has to open an app for it to happen.

---

## What you need

| | |
|---|---|
| **Docker** | with `docker compose` — that is the whole runtime |
| **A free Plow account** | you log in with a code sent by SMS |
| **A phone that texts** | Android or iPhone, either is fine |

**What you do *not* need:** no API key, no model subscription, no paid account,
no Mac, no iPhone. The agent talks to a model through your Plow line.

---

## Install

### 1. Get RadaR

```bash
git clone https://github.com/thematheussousa-bitnoob/radar.git
cd radar
```

Everything below runs from that folder.

### 2. Get the Plow CLI

```bash
git clone https://github.com/plow-pbc/plow-agents.git
mkdir -p ~/.config/plow
```

The CLI is Linux and macOS only — it calls a system function Windows does not
have, and it fails *after* burning your single-use login code. **Run it in a
container instead**, which is the environment it expects. This works the same on
Linux, macOS and Windows:

```bash
docker run --rm -it \
  -v "$PWD/plow-agents/bin":/cli \
  -v "$HOME/.config/plow":/root/.config/plow \
  -v "$PWD":/work -w /work \
  python:3-slim python -u /cli/plow-agents login
```

> On Windows, run this from Git Bash and prefix the command with
> `MSYS_NO_PATHCONV=1` — otherwise the shell rewrites the container paths and
> the mounts land in the wrong place.

`login` prints a line like `Text  Plow Activate: <code>  to  <number>`. Send
that text from your phone. The command then waits for the confirmation, checking
every few seconds, for up to 15 minutes.

### 3. Pick a line and mint its credential

Replace `login` in the command above with `lines` to see what you have:

```
LINE     NAME     NUMBER           STATE
ln_xxx   Aspen    +1650xxxxxxx     free
```

Then mint the credential for a **free** line:

```bash
# same docker run as above, with:  /cli/plow-agents mint ln_xxx
```

This writes a `plow-credentials` file into the current folder. That file is a
secret — it is your agent's badge. Never commit it, never share it.

> The line's name comes from a pool Plow offers (Alder, Aspen, Elm, Spruce,
> Willow). Whichever you pick is the name *your* copy of the agent will answer
> to — it is your line, not ours.

### 4. Start it

```bash
docker compose up --build -d
docker compose logs -f agent
```

The first build takes about a minute from cold, nearly all of it pulling the
public base image. Wait for:

```
hermes-gateway successfully started
```

### 5. Text it

Send a message to your line's number. Try:

> *me lembra de renovar o passaporte* — it will ask you when.

Messages take a couple of minutes to arrive in each direction. That delay is on
the messaging side, not the agent.

---

## Keeping it running

```bash
docker compose up --build -d    # rebuild after any change; keeps your data
docker compose down             # stop it; your data stays
docker compose logs -f agent    # watch it work
```

**Do not run `docker compose down -v`.** The `-v` deletes the volume that holds
the agent's home — its sessions, its setup and its identity. Use it only when
you mean to throw this agent away for good.

---

## What it does not do

Stated plainly, because an agent that overpromises wastes your time:

- **It does not see your screen or drive your computer.** It lives in a
  container with no display and no hands.
- **It does not reach WhatsApp, Telegram or your email.** When you ask it to
  write a message for someone, it hands you the text and *you* send it.
- **It does not guess deadlines.** If it can't tell when something is due, it
  asks. That is the point.

---

## What it reports

RadaR's Plow base image ships the AI Worth Using **agent-index client**, which posts this
install's token usage to a public leaderboard every five minutes. There is no
switch to turn it off — that decision belongs to whoever builds the image, and
this image was built with it.

What leaves your machine is narrow, and worth stating exactly:

- **Day-by-day, model-by-model token counts. Nothing else.**
- **No prompts, no message content, no task titles, no file paths, no costs.**
- One install id, drawn from random bytes so two copies of RadaR can be told
  apart. It says nothing about you or your machine.

---

## What's inside

| Skill | What it does |
|---|---|
| `lembrete` | Saves what must not be forgotten, delivers it on time, and calls it off or moves it when you change your mind. |
| `recado` | Drafts a ready-to-send message for someone else. |
| `maps` | Turns "stop by the post office" into *which* post office, and how far. |

The agent is built on Plow's public Hermes base image, pinned to an exact
commit. It ships with three skills and nothing else: it answers one question —
what you can't forget, and when — and everything that didn't serve that question
was removed.

---

## License

MIT. See [LICENSE](LICENSE).

Built by **Matheus Sousa**.
