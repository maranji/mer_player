#!/usr/bin/env python3
"""
Mother Earth Radio - Linux player - Requires mpv installed
"""

import curses
import subprocess
import sys
import threading
import json
import os
import time
import urllib.request

# ── Languages ─────────────────────────────────────────────────────────────────

LANGS = ["en", "de", "it", "fr", "es"]

STRINGS = {
    "en": {
        "instructions": [
            ("Arrows: navigate",  "ENTER: play"),
            ("S: stop/resume",    "Q: quit"),
            ("A: autoplay on/off","L: change language"),
            ("N: next track",     "H: show/hide help"),
            ("C: compact mode",   ""),
        ],
        "header_channel":  "CHANNEL",
        "header_quality":  "QUALITY",
        "autoplay_label":  "Autoplay",
        "status_idle":     "Press ENTER to start playback",
        "status_autoplay": "Autoplay starting...",
        "status_error":    "ERROR: stream unreachable",
        "status_stop":     "■  Stop",
        "now_playing":     "Now Playing",
        "now_next":        "Up Next",
        "label_artist":    "Artist",
        "label_title":     "Title",
        "label_album":     "Album",
        "label_duration":  "Duration",
        "label_remaining": "Remaining",
    },
    "de": {
        "instructions": [
            ("Pfeile: navigieren", "ENTER: spielen"),
            ("S: stop/weiter",     "Q: Ende"),
            ("A: autoplay on/off", "L: Sprache wechseln"),
            ("N: nächster Titel",  "H: Hilfe ein/aus"),
            ("C: kompakter Modus", ""),
        ],
        "header_channel":  "KANAL",
        "header_quality":  "QUALITÄT",
        "autoplay_label":  "Autoplay",
        "status_idle":     "ENTER drücken zum Starten",
        "status_autoplay": "Autoplay läuft...",
        "status_error":    "FEHLER: Stream nicht erreichbar",
        "status_stop":     "■  Stop",
        "now_playing":     "Läuft gerade",
        "now_next":        "Als Nächstes",
        "label_artist":    "Künstler",
        "label_title":     "Titel",
        "label_album":     "Album",
        "label_duration":  "Dauer",
        "label_remaining": "Verbleibend",
    },
    "it": {
        "instructions": [
            ("Frecce: naviga",    "INVIO: riproduci"),
            ("S: stop/riprendi",  "Q: esci"),
            ("A: autoplay on/off","L: cambia lingua"),
            ("N: prossimo brano", "H: mostra/nascondi"),
            ("C: modalità compatta", ""),
        ],
        "header_channel":  "CANALE",
        "header_quality":  "QUALITA'",
        "autoplay_label":  "Autoplay",
        "status_idle":     "Premi INVIO per avviare la riproduzione",
        "status_autoplay": "Autoplay in corso...",
        "status_error":    "ERRORE: stream non raggiungibile",
        "status_stop":     "■  Stop",
        "now_playing":     "In riproduzione",
        "now_next":        "Prossimo brano",
        "label_artist":    "Artista",
        "label_title":     "Titolo",
        "label_album":     "Album",
        "label_duration":  "Durata",
        "label_remaining": "Rimanente",
    },
    "fr": {
        "instructions": [
            ("Flèches: naviguer",   "ENTRÉE: jouer"),
            ("S: stop/reprendre",   "Q: quitter"),
            ("A: lecture auto on/off", "L: langue"),
            ("N: piste suivante",   "H: aide on/off"),
            ("C: mode compact",     ""),
        ],
        "header_channel":  "CHAÎNE",
        "header_quality":  "QUALITÉ",
        "autoplay_label":  "Lecture auto",
        "status_idle":     "Appuyez sur ENTRÉE pour démarrer",
        "status_autoplay": "Lecture auto en cours...",
        "status_error":    "ERREUR: flux inaccessible",
        "status_stop":     "■  Stop",
        "now_playing":     "En cours",
        "now_next":        "Suivant",
        "label_artist":    "Artiste",
        "label_title":     "Titre",
        "label_album":     "Album",
        "label_duration":  "Durée",
        "label_remaining": "Restant",
    },
    "es": {
        "instructions": [
            ("Flechas: navegar",    "ENTER: reproducir"),
            ("S: stop/reanudar",    "Q: salir"),
            ("A: autoplay on/off",  "L: idioma"),
            ("N: siguiente pista",  "H: ayuda on/off"),
            ("C: modo compacto",    ""),
        ],
        "header_channel":  "CANAL",
        "header_quality":  "CALIDAD",
        "autoplay_label":  "Autoplay",
        "status_idle":     "Pulsa ENTER para iniciar la reproducción",
        "status_autoplay": "Autoplay iniciando...",
        "status_error":    "ERROR: stream inaccesible",
        "status_stop":     "■  Stop",
        "now_playing":     "Reproduciendo",
        "now_next":        "Siguiente",
        "label_artist":    "Artista",
        "label_title":     "Título",
        "label_album":     "Álbum",
        "label_duration":  "Duración",
        "label_remaining": "Restante",
    },
}

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH = os.path.expanduser("~/.config/mer_player.json")

DEFAULT_CONFIG = {
    "ch_idx":    0,
    "q_idx":     1,     # FLAC 96kHz
    "autoplay":  True,
    "lang":      "en",
    "show_help": True,
    "compact":   False,
}

def load_config():
    try:
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
        cfg["ch_idx"]   = int(cfg.get("ch_idx",   0))
        cfg["q_idx"]    = int(cfg.get("q_idx",    0))
        cfg["autoplay"] = bool(cfg.get("autoplay", False))
        cfg["lang"]      = cfg.get("lang", "en") if cfg.get("lang") in LANGS else "en"
        cfg["show_help"] = bool(cfg.get("show_help", True))
        cfg["compact"]   = bool(cfg.get("compact",   False))
        return cfg
    except Exception:
        return dict(DEFAULT_CONFIG)

def save_config():
    cfg = {
        "ch_idx":   state["ch_idx"],
        "q_idx":    state["q_idx"],
        "autoplay":  state["autoplay"],
        "lang":      state["lang"],
        "show_help": state["show_help"],
        "compact":   state["compact"],
    }
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

# ── Channels and streams ──────────────────────────────────────────────────────

CHANNELS = [
    {
        "name":    "Main (Eclectic)",
        "station": "motherearth",
        "streams": [
            ("FLAC 192kHz", "https://stream.motherearthradio.de/listen/motherearth/motherearth"),
            ("FLAC 96kHz",  "https://stream.motherearthradio.de/listen/motherearth/motherearth.flac-lo"),
            ("AAC 320kbps", "https://stream.motherearthradio.de/listen/motherearth/motherearth.aac"),
            ("MP3 320kbps", "https://stream.motherearthradio.de/listen/motherearth/motherearth.mp3"),
        ]
    },
    {
        "name":    "Jazz",
        "station": "motherearth_jazz",
        "streams": [
            ("FLAC 192kHz", "https://stream.motherearthradio.de/listen/motherearth_jazz/motherearth.jazz"),
            ("FLAC 96kHz",  "https://stream.motherearthradio.de/listen/motherearth_jazz/motherearth.jazz.flac-lo"),
            ("AAC 320kbps", "https://stream.motherearthradio.de/listen/motherearth_jazz/motherearth.jazz.mp4"),
            ("MP3 320kbps", "https://stream.motherearthradio.de/listen/motherearth_jazz/motherearth.jazz.mp3"),
        ]
    },
    {
        "name":    "Classical",
        "station": "motherearth_klassik",
        "streams": [
            ("FLAC 192kHz", "https://stream.motherearthradio.de/listen/motherearth_klassik/motherearth.klassik"),
            ("FLAC 96kHz",  "https://stream.motherearthradio.de/listen/motherearth_klassik/motherearth.klassik.flac-lo"),
            ("AAC 320kbps", "https://stream.motherearthradio.de/listen/motherearth_klassik/motherearth.klassik.aac"),
            ("MP3 320kbps", "https://stream.motherearthradio.de/listen/motherearth_klassik/motherearth.klassik.mp3"),
        ]
    },
    {
        "name":    "Instrumental",
        "station": "motherearth_instrumental",
        "streams": [
            ("FLAC 192kHz", "https://stream.motherearthradio.de/listen/motherearth_instrumental/motherearth.instrumental"),
            ("FLAC 96kHz",  "https://stream.motherearthradio.de/listen/motherearth_instrumental/motherearth.instrumental.flac-lo"),
            ("AAC 320kbps", "https://stream.motherearthradio.de/listen/motherearth_instrumental/motherearth.instrumental.aac"),
            ("MP3 320kbps", "https://stream.motherearthradio.de/listen/motherearth_instrumental/motherearth.instrumental.mp3"),
        ]
    },
]

API_BASE = "https://stream.motherearthradio.de/api/nowplaying"

# ── Global state ──────────────────────────────────────────────────────────────

state = {
    "proc":           None,
    "ch_idx":         0,
    "q_idx":          0,
    "playing_ch":     None,
    "playing_q":      None,
    "focus":          "channel",
    "autoplay":       False,
    "lang":           "en",
    "status_key":     "idle",    # idle | autoplay_start | playing | error | stop
    "status_info":    "",        # used by "playing": "Channel | Quality"
    # Current track metadata
    "track_artist":   "",
    "track_title":    "",
    "track_album":    "",
    "track_duration": 0,
    "track_elapsed":  0,
    "track_updated":  0.0,
    # Next track metadata
    "track_next_artist": "",
    "track_next_title":  "",
    "track_next_album":  "",
    # Show next track (N key held)
    "show_next":       False,
    "next_pressed_at": 0.0,
    "show_help":          True,
    "compact":            False,
    "compact_navigating": False,
}

proc_lock = threading.Lock()

# ── Metadata polling ──────────────────────────────────────────────────────────

_meta_stop   = threading.Event()
_meta_wakeup = threading.Event()

def _meta_poll_loop():
    """Polls the AzuraCast API and sleeps until the current track ends."""
    while not _meta_stop.is_set():
        _meta_wakeup.clear()
        ch_idx = state["playing_ch"]
        if ch_idx is not None:
            station = CHANNELS[ch_idx]["station"]
            url = f"{API_BASE}/{station}"
            wait = 30
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "MERPlayer/1.0"})
                with urllib.request.urlopen(req, timeout=6) as r:
                    data = json.loads(r.read())
                np   = data.get("now_playing", {})
                song = np.get("song", {})
                state["track_artist"]   = song.get("artist", "")
                state["track_title"]    = song.get("title",  "")
                state["track_album"]    = song.get("album",  "")
                state["track_duration"] = int(np.get("duration", 0))
                state["track_elapsed"]  = int(np.get("elapsed",  0))
                state["track_updated"]  = time.time()
                pn      = data.get("playing_next") or {}
                pn_song = pn.get("song") or {}
                state["track_next_artist"] = pn_song.get("artist", "")
                state["track_next_title"]  = pn_song.get("title",  "")
                state["track_next_album"]  = pn_song.get("album",  "")
                remaining = int(np.get("remaining", 0))
                wait = max(remaining, 1) + 2
            except Exception:
                pass
        else:
            wait = 5
        _meta_wakeup.wait(wait)

def _clear_metadata():
    state["track_artist"]   = ""
    state["track_title"]    = ""
    state["track_album"]    = ""
    state["track_duration"] = 0
    state["track_elapsed"]  = 0
    state["track_updated"]  = 0.0
    state["track_next_artist"] = ""
    state["track_next_title"]  = ""
    state["track_next_album"]  = ""

def fmt_time(seconds):
    m, s = divmod(max(0, int(seconds)), 60)
    return f"{m:02d}:{s:02d}"

# ── Player ────────────────────────────────────────────────────────────────────

def detect_player():
    for p in ["mpv", "vlc", "ffplay"]:
        if subprocess.call(["which", p],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL) == 0:
            return p
    return None

def build_cmd(player, url):
    if player == "mpv":
        return ["mpv", "--no-video", "--no-ytdl", "--msg-level=all=error", url]
    elif player == "vlc":
        return ["vlc", "--intf", "dummy", "--no-video", "--quiet", url]
    else:
        return ["ffplay", "-nodisp", "-loglevel", "error", url]

def stop_playback():
    with proc_lock:
        proc = state["proc"]
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
        state["proc"] = None
    _clear_metadata()

def _watch_process(proc, ch_idx, q_idx):
    """Watches the process: if it exits within 5s it's a stream error."""
    start = time.time()
    proc.wait()
    elapsed = time.time() - start
    with proc_lock:
        current = state["proc"]
    if current is proc or current is None:
        if elapsed < 5.0 and state["playing_ch"] == ch_idx:
            state["status_key"]  = "error"
            state["status_info"] = ""
            state["playing_ch"]  = None
            state["playing_q"]   = None
            _clear_metadata()

def start_playback(player, ch_idx, q_idx):
    stop_playback()
    url = CHANNELS[ch_idx]["streams"][q_idx][1]
    cmd = build_cmd(player, url)
    with proc_lock:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        state["proc"] = proc
    state["playing_ch"]  = ch_idx
    state["playing_q"]   = q_idx
    _meta_wakeup.set()
    ch_name = CHANNELS[ch_idx]["name"]
    q_name  = CHANNELS[ch_idx]["streams"][q_idx][0]
    state["status_key"]  = "playing"
    state["status_info"] = f"{ch_name}  ·  {q_name}"
    save_config()
    threading.Thread(
        target=_watch_process,
        args=(proc, ch_idx, q_idx),
        daemon=True,
    ).start()

# ── Curses drawing ────────────────────────────────────────────────────────────

# Static banner lines (radio title, untranslated)
BANNER = [
    "┌──────────────────────────────────────────────────┐",
    "│       Mother Earth Radio  Player  Hi-Res         │",
    "│         FLAC Streaming  192kHz / 24bit           │",
]
BANNER_SEP   = "├──────────────────────────────────────────────────┤"
BANNER_CLOSE = "└──────────────────────────────────────────────────┘"
BOX_WIDTH    = 52   # total width of the green box (including │ borders)

def safe_add(win, y, x, text, attr=0):
    try:
        h, w = win.getmaxyx()
        if y < 0 or y >= h or x < 0 or x >= w:
            return
        win.addstr(y, x, text[:max(0, w - x - 1)], attr)
    except curses.error:
        pass

def _box_line(stdscr, y, text, border_attr, inner_attr):
    """Box row: │ borders with border_attr, inner text (2 spaces + text) with inner_attr."""
    inner = ("  " + text).ljust(50)[:50]
    safe_add(stdscr, y, 0,  "│", border_attr)
    safe_add(stdscr, y, 1,  inner, inner_attr)
    safe_add(stdscr, y, 51, "│", border_attr)

def _wrap_text(text, first_width, cont_width):
    """Splits text into lines respecting word boundaries."""
    words = text.split()
    if not words:
        return ["—"]
    lines, current, width = [], "", first_width
    for word in words:
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= width:
            current += " " + word
        else:
            lines.append(current)
            current = word
            width = cont_width
    if current:
        lines.append(current)
    return lines

def _draw_field(stdscr, row, label, text, attr, term_width):
    """Draws a metadata field with word wrap. Returns the number of rows used."""
    prefix     = f"{label}:  "
    col        = 2
    text_col   = col + len(prefix)
    first_w    = max(1, term_width - text_col)
    cont_w     = max(1, term_width - text_col)
    lines      = _wrap_text(text or "—", first_w, cont_w)
    safe_add(stdscr, row, col, prefix + lines[0], attr)
    for i, line in enumerate(lines[1:], 1):
        safe_add(stdscr, row + i, text_col, line, attr)
    return len(lines)

def draw(stdscr):
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN,  -1)
    curses.init_pair(2, curses.COLOR_CYAN,   -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_RED,    -1)
    curses.init_pair(6, curses.COLOR_BLACK,  curses.COLOR_WHITE)
    curses.init_pair(7, curses.COLOR_WHITE,  -1)

    GREEN  = curses.color_pair(1) | curses.A_BOLD
    CYAN   = curses.color_pair(2)
    YELLOW = curses.color_pair(3) | curses.A_BOLD
    RED    = curses.color_pair(4) | curses.A_BOLD
    SEL    = curses.color_pair(6)
    DIM    = curses.A_DIM
    WHITE  = curses.color_pair(7)

    s      = STRINGS[state["lang"]]
    focus  = state["focus"]
    ch_idx = state["ch_idx"]
    q_idx  = state["q_idx"]

    stdscr.erase()

    # Banner (radio title + optional instructions)
    row = 0
    for line in BANNER:
        safe_add(stdscr, row, 0, line, GREEN)
        row += 1
    if state["show_help"]:
        safe_add(stdscr, row, 0, BANNER_SEP, GREEN)
        row += 1
        for left, right in s["instructions"]:
            _box_line(stdscr, row, f"{left:<22}{right}", GREEN, WHITE)
            row += 1
    safe_add(stdscr, row, 0, BANNER_CLOSE, GREEN)
    row += 1 if state["compact"] else 2

    # Compact mode: selection row — shown after an arrow key, hidden after ENTER or S
    if state["compact"] and state["compact_navigating"]:
        ch_name = CHANNELS[ch_idx]["name"]
        q_name  = CHANNELS[ch_idx]["streams"][q_idx][0]
        sep     = "  ·  "
        ch_attr = curses.A_BOLD if focus == "channel" else DIM
        q_attr  = curses.A_BOLD if focus == "quality"  else DIM
        safe_add(stdscr, row, 2, ch_name, ch_attr)
        safe_add(stdscr, row, 2 + len(ch_name), sep, DIM)
        safe_add(stdscr, row, 2 + len(ch_name) + len(sep), q_name, q_attr)

    # Column headers (hidden in compact mode)
    streams = CHANNELS[ch_idx]["streams"]
    if not state["compact"]:
        ch_attr = CYAN | curses.A_BOLD if focus == "channel" else CYAN
        q_attr  = CYAN | curses.A_BOLD if focus == "quality"  else CYAN
        safe_add(stdscr, row, 2,  s["header_channel"], ch_attr)
        safe_add(stdscr, row, 30, s["header_quality"],  q_attr)
        row += 1
        safe_add(stdscr, row, 2,  "─" * 24, DIM)
        safe_add(stdscr, row, 30, "─" * 20, DIM)
        row += 1

        # Channel column
        for i, ch in enumerate(CHANNELS):
            is_sel = (i == ch_idx)
            safe_add(stdscr, row + i, 2, f"{ch['name']:<22}", SEL if is_sel else 0)

        # Quality column
        for i, (q_name, _) in enumerate(streams):
            is_sel = (i == q_idx)
            safe_add(stdscr, row + i, 30, f"{q_name:<20}", SEL if is_sel else 0)

        row += max(len(CHANNELS), len(streams))

    # Status
    status_row = row + 1
    sk = state["status_key"]
    if sk in ("playing", "stop"):
        icon  = "▶" if sk == "playing" else "■"
        label = (s["now_next"] if state["show_next"] else s["now_playing"]) if sk == "playing" else s["status_stop"]
        safe_add(stdscr, status_row,     2, f"{icon}  {state['status_info']}", YELLOW)
        safe_add(stdscr, status_row + 1, 2, "─" * 48, DIM)
        safe_add(stdscr, status_row + 2, 2, label, YELLOW)
    else:
        if sk == "error":
            status_text = s["status_error"]
            is_err = True
        elif sk == "autoplay_start":
            status_text = s["status_autoplay"]
            is_err = False
        else:
            status_text = s["status_idle"]
            is_err = False
        safe_add(stdscr, status_row,     2, "─" * 48, DIM)
        safe_add(stdscr, status_row + 1, 2, status_text, RED if is_err else YELLOW)

    # Current track info
    meta_row = status_row + (3 if sk in ("playing", "stop") else 2)
    if state["track_updated"] > 0:
        _, w      = stdscr.getmaxyx()
        duration  = state["track_duration"]
        elapsed   = state["track_elapsed"] + int(time.time() - state["track_updated"])
        remaining = max(0, duration - elapsed)

        lw = max(len(s["label_artist"]), len(s["label_title"]),
                 len(s["label_album"]),  len(s["label_duration"]))
        def lbl(key): return f"{s[key]:<{lw}}"

        if state["show_next"] and sk == "playing":
            meta_row += _draw_field(stdscr, meta_row, lbl("label_artist"), state["track_next_artist"], CYAN, BOX_WIDTH)
            meta_row += _draw_field(stdscr, meta_row, lbl("label_title"),  state["track_next_title"],  CYAN, BOX_WIDTH)
            meta_row += _draw_field(stdscr, meta_row, lbl("label_album"),  state["track_next_album"],  CYAN, BOX_WIDTH)
        else:
            meta_row += _draw_field(stdscr, meta_row, lbl("label_artist"), state["track_artist"], CYAN, BOX_WIDTH)
            meta_row += _draw_field(stdscr, meta_row, lbl("label_title"),  state["track_title"],  CYAN, BOX_WIDTH)
            meta_row += _draw_field(stdscr, meta_row, lbl("label_album"),  state["track_album"],  CYAN, BOX_WIDTH)
            if duration > 0:
                left  = f"{lbl('label_duration')}:  {fmt_time(duration)}"
                right = f"{s['label_remaining']}:  {fmt_time(remaining)}"
                safe_add(stdscr, meta_row, 2,
                         f"{left}{right:>{BOX_WIDTH - 2 - len(left)}}",
                         DIM)
                meta_row += 1

    # Autoplay box (always visible, at the bottom)
    meta_row += 1
    safe_add(stdscr, meta_row, 0, BANNER[0], GREEN)
    meta_row += 1
    ap_val  = "ON " if state["autoplay"] else "OFF"
    ap_attr = GREEN if state["autoplay"] else DIM
    h_hint  = "" if state["show_help"] else s["instructions"][3][1]
    safe_add(stdscr, meta_row, 0,  "│", GREEN)
    safe_add(stdscr, meta_row, 1,  f"  {s['autoplay_label']}: [{ap_val}]{h_hint:>33}", WHITE)
    safe_add(stdscr, meta_row, 14, ap_val, ap_attr)
    safe_add(stdscr, meta_row, 51, "│", GREEN)
    meta_row += 1
    safe_add(stdscr, meta_row, 0, BANNER_CLOSE, GREEN)

    stdscr.refresh()

# ── Main loop ─────────────────────────────────────────────────────────────────

def main_loop(stdscr, player):
    curses.curs_set(0)
    stdscr.timeout(100)

    if state["autoplay"]:
        state["status_key"] = "autoplay_start"
        threading.Thread(
            target=start_playback,
            args=(player, state["ch_idx"], state["q_idx"]),
            daemon=True,
        ).start()

    while True:
        # N key release: if not pressed for >600ms, revert to current track
        if state["show_next"] and time.time() - state["next_pressed_at"] > 0.6:
            state["show_next"] = False

        draw(stdscr)
        key = stdscr.getch()
        if key == -1:
            continue

        focus  = state["focus"]
        ch_idx = state["ch_idx"]
        q_idx  = state["q_idx"]
        n_ch   = len(CHANNELS)
        n_q    = len(CHANNELS[ch_idx]["streams"])

        if key in (ord('q'), ord('Q')):
            stop_playback()
            return

        elif key == curses.KEY_RIGHT:
            state["focus"] = "quality"
            if state["compact"]:
                state["compact_navigating"] = True

        elif key == curses.KEY_LEFT:
            state["focus"] = "channel"
            if state["compact"]:
                state["compact_navigating"] = True

        elif key == curses.KEY_UP:
            if focus == "channel":
                state["ch_idx"] = (ch_idx - 1) % n_ch
                state["q_idx"]  = min(q_idx, len(CHANNELS[state["ch_idx"]]["streams"]) - 1)
            else:
                state["q_idx"] = (q_idx - 1) % n_q
            if state["compact"]:
                state["compact_navigating"] = True

        elif key == curses.KEY_DOWN:
            if focus == "channel":
                state["ch_idx"] = (ch_idx + 1) % n_ch
                state["q_idx"]  = min(q_idx, len(CHANNELS[state["ch_idx"]]["streams"]) - 1)
            else:
                state["q_idx"] = (q_idx + 1) % n_q
            if state["compact"]:
                state["compact_navigating"] = True

        elif key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
            if state["compact"]:
                state["compact_navigating"] = False
            threading.Thread(
                target=start_playback,
                args=(player, state["ch_idx"], state["q_idx"]),
                daemon=True,
            ).start()

        elif key in (ord('s'), ord('S')):
            proc = state["proc"]
            if proc and proc.poll() is None:
                stop_playback()
                state["status_key"] = "stop"
                state["compact_navigating"] = False
            elif state["playing_ch"] is not None:
                threading.Thread(
                    target=start_playback,
                    args=(player, state["playing_ch"], state["playing_q"]),
                    daemon=True,
                ).start()

        elif key == 27 and state["compact"]:   # ESC
            state["compact_navigating"] = False

        elif key in (ord('a'), ord('A')):
            state["autoplay"] = not state["autoplay"]
            save_config()

        elif key in (ord('h'), ord('H')):
            state["show_help"] = not state["show_help"]
            save_config()

        elif key in (ord('c'), ord('C')):
            state["compact"] = not state["compact"]
            save_config()

        elif key in (ord('n'), ord('N')):
            state["show_next"]       = True
            state["next_pressed_at"] = time.time()

        elif key in (ord('l'), ord('L')):
            state["lang"] = LANGS[(LANGS.index(state["lang"]) + 1) % len(LANGS)]
            save_config()

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    player = detect_player()
    if not player:
        print("Error: no media player found.")
        print("Install mpv with:  sudo apt install mpv")
        sys.exit(1)

    cfg = load_config()
    state["ch_idx"]   = min(cfg["ch_idx"], len(CHANNELS) - 1)
    state["q_idx"]    = min(cfg["q_idx"],  len(CHANNELS[state["ch_idx"]]["streams"]) - 1)
    state["autoplay"]  = cfg["autoplay"]
    state["lang"]      = cfg["lang"]
    state["show_help"] = cfg["show_help"]
    state["compact"]   = cfg["compact"]

    _meta_stop.clear()
    threading.Thread(target=_meta_poll_loop, daemon=True).start()

    try:
        curses.wrapper(lambda stdscr: main_loop(stdscr, player))
    except KeyboardInterrupt:
        pass
    finally:
        _meta_stop.set()
        stop_playback()
        print("\nGoodbye!\n")

if __name__ == "__main__":
    main()
