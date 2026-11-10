---
title: Winlink P2P directory — spec v1
---

# Winlink P2P directory — spec v1

A public list of amateur stations that welcome peer-to-peer Winlink connections, in a
form any Winlink client can read. This page is everything a client author needs, and
everything an operator needs to get listed.

- **Find a station:** [find.html](find.html)
- **The data:** [`v1/directory.json`](v1/directory.json) · [`v1/directory.csv`](v1/directory.csv) ·
  [`v1/directory.txt`](v1/directory.txt). The data is CC0; the code is MIT.
- **Conformance fixtures:** [`fixtures/`](https://github.com/cvp1/p2p-directory/tree/main/fixtures)
- **Reference parser:** [`p2pdir.py`](https://github.com/cvp1/p2p-directory/blob/main/p2pdir.py) (Python, stdlib only)

## Get listed

1. Write your listing (format below). Four lines is enough:

   ```
   P2PDIR 1
   grid: EM12
   entry: 7103.5 VARA_HF 500 attended daily 1400-1600Z
   note: NVIS dipole, 100 W
   ```

2. Send it as the **body** of an ordinary Winlink message to **N0CVP**, subject
   `P2PDIR listing`. The message coming from your callsign is how we know you asked.
   The template in [`templates/`](https://github.com/cvp1/p2p-directory/tree/main/templates)
   writes the body for you in Winlink Express or Pat.
   Or [open an issue](https://github.com/cvp1/p2p-directory/issues/new?template=listing.yml);
   you will get a Winlink message to your callsign to confirm before it is merged.
3. A person reads it and adds `listings/<CALL>.txt`. You are listed after the next build
   (minutes).

**To stay listed,** send the same listing (or the word `confirm`) at least every 90 days.
After 90 days without a word a listing shows as stale; after 180 it is removed.
**To be removed,** send `remove`. **Everything in a listing is public**, so keep the grid
to 4 characters unless you want to be found more precisely, and keep the note to station
facts.

## The listing format

Plain UTF-8 text, at most **2048 bytes**. Lines are `key: value`. Blank lines and
surrounding whitespace (spaces and tabs) are ignored. `CRLF`, a bare `CR` and a leading
byte-order mark are accepted. The version line, keys, modes and controls are all
case-insensitive: `p2pdir 1`, `Grid:`, `vara_hf` and `Attended` are fine, and the output
uses the canonical case (`VARA_HF`, `attended`; a grid as `FN31pr`, field and square upper,
subsquare lower).

| Line | Required | Rule |
|---|---|---|
| `P2PDIR 1` | yes, first non-blank line | The version. A client that sees another number must not guess. |
| `grid:` | yes, once | Maidenhead locator, 4 or 6 characters (`EM12`, `FN31pr`). |
| `entry:` | 1 to 12 | `<centre_khz> <mode> <width> <control> <hours>`, space separated; see below. |
| `note:` | no, once | Free text, at most 80 characters. |
| anything else | — | Ignored with a warning, so later versions can add keys. |

**The callsign is never in the text.** It comes from who sent the listing (the file name
in the repository is `<CALL>.txt`). A callsign matches `^[A-Z0-9]{1,3}[0-9][A-Z]{1,4}$`
after upper-casing: no SSID, no portable suffix.

### An entry

```
entry: 7103.5 VARA_HF 500 attended daily 1400-1600Z
       ^      ^       ^   ^        ^
       |      |       |   |        hours: free text to end of line, at most 40 characters
       |      |       |   control: attended | auto | sked
       |      |       width: occupied bandwidth in Hz, or baud for packet modes
       |      mode
       centre frequency in kHz, up to 3 decimals, inside an amateur band
```

| Mode | Width field | Allowed widths | Dial from centre |
|---|---|---|---|
| `VARA_HF` | Hz | 500, 2300, 2750 | centre − 1.5 kHz (USB) |
| `ARDOP` | Hz | 200, 500, 1000, 2000 | centre − 1.5 kHz (USB) |
| `PACTOR` | Hz | 500, 2400 | centre − 1.5 kHz (USB) |
| `VARA_FM` | Hz | 12500, 25000 | same as centre |
| `PACKET` | baud | 300, 1200, 9600 | same as centre |
| `ROBUST_PACKET` | baud | 300, 600 | not defined in v1: show centre only |

- **Centre, not dial.** The published number is the centre of the signal, as the Winlink
  gateway list and existing net schedules publish it, so it does not depend on the rig.
  The dial column is what a client sets on the radio. It matches Pat v1.0.0, whose
  `freq=` connect parameter is the dial frequency (`app/connect.go:148`, `app/freq.go:68-107`).
- **Control** is what the operator says about the station: `attended` (someone at the
  radio), `auto` (automatic control, a station that answers on its own), `sked` (by
  arrangement). The directory stores it and labels it; it does not judge it.
- **Hours** is free text: `daily 1400-1600Z`, `24/7`, `weekends`. Use UTC.
- **Numbers.** The frequency matches `^[0-9]{1,7}(\.[0-9]{1,3})?$` (no sign, no trailing
  dot, no thousands separator). The width is a whole number from the table. Lengths
  (note, hours) count characters, not bytes. Fields are separated by any run of spaces or
  tabs; hours is everything after the fourth field, trimmed.
- **Amateur bands** (the frequency must fall inside one, edges included; the union of the
  ITU regions, kHz): 1800-2000, 3500-4000, 5250-5450, 7000-7300, 10100-10150,
  14000-14350, 18068-18168, 21000-21450, 24890-24990, 28000-29700, 50000-54000,
  70000-71000, 144000-148000, 219000-225000, 420000-450000, 902000-928000,
  1240000-1300000. Only the centre is checked against these.

### What is rejected

A listing is accepted whole or not at all; a rejection changes nothing already published.
Checks run in this order and the **first** failure is the code reported: the callsign;
size; UTF-8; then each line in order (control characters, then the line's own rules);
then, at the end, the missing pieces. The 13th `entry:` line rejects at that line.

| Code | When |
|---|---|
| `bad-call` | The callsign does not match the pattern above. |
| `too-big` | Over 2048 bytes, counting a byte-order mark. |
| `not-utf8` | Not valid UTF-8. |
| `control-char` | A line holds a C0 or C1 control character or DEL (tab, CR and LF excepted). |
| `unsupported-version` | The first non-blank line, upper-cased with runs of spaces made one, is `P2PDIR ` plus digits other than exactly `1` (so `P2PDIR 01` too). |
| `no-header` | The first non-blank line is anything else, or the listing is empty. |
| `not-key-value` | A line after the header has no `:`. |
| `duplicate-key` | A second `grid:` or `note:` (an empty `note:` still counts). |
| `bad-grid` | The grid is not 4 or 6 Maidenhead characters. |
| `note-too-long` | The note is over 80 characters. |
| `entry-fields` | An entry has fewer than five fields. |
| `bad-frequency` | The frequency does not match the number pattern. |
| `out-of-band` | The frequency is outside every amateur band. |
| `unknown-mode` | The mode is not in the table. |
| `bad-width` | The width is not one the table allows for that mode. |
| `bad-control` | The control is not `attended`, `auto` or `sked`. |
| `hours-too-long` | Hours is over 40 characters. |
| `too-many-entries` | A 13th entry. |
| `no-grid` | No `grid:` line. |
| `no-entries` | No `entry:` line. |

### What a parser returns

For an accepted listing, the reference parser returns the station row without the
fields only the directory adds (`confirmed`, `source`, `stale`):

```json
{"call": "N9ABC", "grid": "EM12", "note": "", "entries": [{"centre_khz": 7103.5,
  "mode": "VARA_HF", "bw_hz": 500, "control": "attended", "hours": "daily", "flags": []}],
 "warnings": ["line 5: unknown key 'location' ignored"]}
```

The width key is `bw_hz` for the Hz modes and `baud` for `PACKET` and `ROBUST_PACKET`.
`call` is upper-case. `centre_khz` is a JSON integer when the value is whole (`7090`, not `7090.0`). `note` is
`""` when there is none. `warnings` appears only when there is at least one: one string
per unknown key line, `line <n>: unknown key '<key>' ignored`, where `n` counts every line
from 1 (blank lines and the header included) and `key` is lower-cased. Warnings are never
published. A later `P2PDIR 1` line is an unknown-format line and rejects as `not-key-value`.

### Flags

A flag is a label for clients to show, never a reason to refuse a listing. v1 has one:

- `hf-auto-outside-97.221b`: a US-looking callsign (starts with `AA`-`AL`, `K`, `N` or `W`),
  control `auto`, centre below 50000 kHz, and the occupied signal (centre ± width/2 Hz;
  `PACKET` and `ROBUST_PACKET` count as 500 Hz wide) not wholly inside one of the nine
  segments of 47 CFR 97.221(b), edges included. The segments, kHz: 3585-3600, 7100-7105,
  10140-10150, 14095-14099.5, 14100.5-14112, 18105-18110, 21090-21100, 24925-24930,
  28120-28189. Guidance, not certification; 97.221(c) allows other automatic operation.

An entry's `flags` is an array of these strings, empty when none apply.

## The published files

`v1/directory.json`:

```json
{"schema": 1, "generated": "2026-11-10T18:00:00Z", "licence": "CC0-1.0", "count": 1,
 "stations": [{"call": "N9ABC", "grid": "EM12", "note": "NVIS dipole, 100 W",
   "confirmed": "2026-11-10", "source": "maintainer", "stale": false,
   "entries": [{"centre_khz": 7103.5, "mode": "VARA_HF", "bw_hz": 500, "control": "attended",
                "hours": "daily 1400-1600Z", "flags": []}]}]}
```

| Field | Meaning |
|---|---|
| `schema` | 1. Refuse any other value. |
| `generated` | UTC time of the build. The build runs nightly; older than 26 h means something is wrong. |
| `count` | Number of stations. |
| `call`, `grid`, `note` | As listed. `note` is `""` when absent. |
| `confirmed` | The date the operator last said the listing is right. **It does not mean the station is on the air.** Show its age. |
| `source` | `maintainer` (added by hand from a request) or `message` (self-listed; later version). |
| `stale` | True from 90 days after `confirmed`. Removed at 180. |
| `entries[]` | `centre_khz` (number), `mode`, `bw_hz` **or** `baud` (by mode, see the table), `control`, `hours`, `flags` (array of strings). |

`directory.csv` has one row per entry with columns `call, grid, confirmed, stale,
centre_khz, dial_khz, mode, bw_hz, baud, control, hours, flags, note`; a cell that would
start with `=`, `+`, `-` or `@` gets a leading `'`. `directory.txt` is for people.

### Reading it from a client

- Fetch at most every 6 hours; the files are served with `access-control-allow-origin: *`
  and a 10-minute cache.
- Check `schema == 1`. Validate every row with the rules above and **drop a bad row,
  never the whole file**.
- Keep the last good copy and show its age when a fetch fails.
- Treat every string as untrusted text: never insert `note` or `hours` as HTML.
- **Never connect on the operator's behalf.** A listing is a claim. Fill in the call, dial
  frequency and mode, and let the operator press connect.
- Nothing in the directory is a telnet host, password or URL to dial.

## Versioning

`P2PDIR 1` and `"schema": 1` change only for a change an old reader would misread. New
optional keys in the listing and new fields in the JSON are added without a version change;
readers ignore what they do not know.
