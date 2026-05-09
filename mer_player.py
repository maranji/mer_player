#!/usr/bin/env python3
"""
Mother Earth Radio - Player per Linux con interfaccia curses
Naviga con i tasti freccia, seleziona con INVIO, esci con Q
Richiede: mpv installato sul sistema
"""

import curses
import subprocess
import sys
import threading
import json
import os
import time
import urllib.request

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH = os.path.expanduser("~/.config/mer_player.json")

DEFAULT_CONFIG = {
    "ch_idx":   0,
    "q_idx":    0,
    "autoplay": False,
}

def load_config():
    try:
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
        cfg["ch_idx"]   = int(cfg.get("ch_idx",   0))
        cfg["q_idx"]    = int(cfg.get("q_idx",    0))
        cfg["autoplay"] = bool(cfg.get("autoplay", False))
        return cfg
    except Exception:
        return dict(DEFAULT_CONFIG)

def save_config():
    cfg = {
        "ch_idx":   state["ch_idx"],
        "q_idx":    state["q_idx"],
        "autoplay": state["autoplay"],
    }
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

# ── Canali e stream ───────────────────────────────────────────────────────────

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

# ── Stato globale ─────────────────────────────────────────────────────────────

state = {
    "proc":           None,
    "ch_idx":         0,
    "q_idx":          0,
    "playing_ch":     None,
    "playing_q":      None,
    "focus":          "channel",
    "autoplay":       False,
    "status":         "Premi INVIO per avviare la riproduzione",
    # Metadata brano corrente
    "track_artist":   "",
    "track_title":    "",
    "track_album":    "",
    "track_duration": 0,
    "track_elapsed":  0,
    "track_updated":  0.0,   # timestamp dell'ultimo poll riuscito
}

proc_lock = threading.Lock()

# ── Metadata polling ──────────────────────────────────────────────────────────

_meta_stop   = threading.Event()
_meta_wakeup = threading.Event()   # segnala al poller di non aspettare il timeout

def _meta_poll_loop():
    """Interroga l'API AzuraCast e dorme fino alla fine del brano corrente.

    Usa i campi 'remaining' (e 'duration'/'elapsed') per calcolare esattamente
    quando il brano finirà, evitando polling inutili durante la riproduzione.
    Viene svegliato anticipatamente (via _meta_wakeup) al cambio di canale.
    """
    while not _meta_stop.is_set():
        _meta_wakeup.clear()
        ch_idx = state["playing_ch"]
        if ch_idx is not None:
            station = CHANNELS[ch_idx]["station"]
            url = f"{API_BASE}/{station}"
            wait = 30  # fallback in caso di errore
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "MERPlayer/1.0"}
                )
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
                # Dormi fino a 2s dopo la fine del brano (margine per aggiornamento API)
                remaining = int(np.get("remaining", 0))
                wait = max(remaining, 1) + 2
            except Exception:
                pass  # riprova tra 30s
        else:
            wait = 5  # nessuna riproduzione attiva, controlla presto
        _meta_wakeup.wait(wait)

def _clear_metadata():
    state["track_artist"]   = ""
    state["track_title"]    = ""
    state["track_album"]    = ""
    state["track_duration"] = 0
    state["track_elapsed"]  = 0
    state["track_updated"]  = 0.0

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
        return ["vlc", "--no-video", "--quiet", url]
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
    """Monitora il processo: se muore entro 5s è un errore di stream."""
    start = time.time()
    proc.wait()
    elapsed = time.time() - start
    with proc_lock:
        current = state["proc"]
    if current is proc or current is None:
        if elapsed < 5.0 and state["playing_ch"] == ch_idx:
            state["status"]     = "ERRORE: stream non raggiungibile"
            state["playing_ch"] = None
            state["playing_q"]  = None
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
    state["playing_ch"] = ch_idx
    state["playing_q"]  = q_idx
    _meta_wakeup.set()   # sveglia il poller per il nuovo canale
    ch_name = CHANNELS[ch_idx]["name"]
    q_name  = CHANNELS[ch_idx]["streams"][q_idx][0]
    state["status"] = f">> {ch_name}  |  {q_name}"
    save_config()
    threading.Thread(
        target=_watch_process,
        args=(proc, ch_idx, q_idx),
        daemon=True,
    ).start()

# ── Disegno curses ────────────────────────────────────────────────────────────

BANNER = [
    "╔══════════════════════════════════════════════════╗",
    "║       Mother Earth Radio  Player  Hi-Res         ║",
    "║         FLAC Streaming  192kHz / 24bit           ║",
    "╠══════════════════════════════════════════════════╣",
    "║  Frecce: naviga   ->/<-: cambia colonna          ║",
    "║  INVIO: riproduci   S: stop/riprendi   Q: esci   ║",
    "║  A: attiva/disattiva autoplay                    ║",
    "╠══════════════════════════════════════════════════╣",
]
BANNER_CLOSE = "╚══════════════════════════════════════════════════╝"

def safe_add(win, y, x, text, attr=0):
    try:
        h, w = win.getmaxyx()
        if y < 0 or y >= h or x < 0 or x >= w:
            return
        win.addstr(y, x, text[:max(0, w - x - 1)], attr)
    except curses.error:
        pass

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

    focus  = state["focus"]
    ch_idx = state["ch_idx"]
    q_idx  = state["q_idx"]

    stdscr.erase()

    # Banner + autoplay (dentro il box)
    # Linee 0-3 e 6 sono bordi/titoli → verdi; linee 4-5 (istruzioni) → bordi verdi, testo bianco
    row = 0
    for i, line in enumerate(BANNER):
        if i in (4, 5, 6):
            safe_add(stdscr, row, 0, "║", GREEN)
            safe_add(stdscr, row, 1, line[1:-1], WHITE)
            safe_add(stdscr, row, len(line) - 1, "║", GREEN)
        else:
            safe_add(stdscr, row, 0, line, GREEN)
        row += 1
    # Riga autoplay: bordi verdi, testo bianco, ON/OFF colorato
    ap_val  = "ON " if state["autoplay"] else "OFF"
    ap_attr = GREEN if state["autoplay"] else DIM
    safe_add(stdscr, row, 0,  "║", GREEN)
    safe_add(stdscr, row, 1,  f"  Autoplay: [{ap_val}]{'':>33}", WHITE)
    safe_add(stdscr, row, 14, ap_val, ap_attr)
    safe_add(stdscr, row, 51, "║", GREEN)
    row += 1
    safe_add(stdscr, row, 0, BANNER_CLOSE, GREEN)
    row += 2

    # Intestazioni — grassetto sulla colonna attiva
    ch_attr = CYAN | curses.A_BOLD if focus == "channel" else CYAN
    q_attr  = CYAN | curses.A_BOLD if focus == "quality"  else CYAN
    safe_add(stdscr, row, 2,  "CANALE",   ch_attr)
    safe_add(stdscr, row, 30, "QUALITA'", q_attr)
    row += 1
    safe_add(stdscr, row, 2,  "─" * 24, DIM)
    safe_add(stdscr, row, 30, "─" * 20, DIM)
    row += 1

    # Colonna canali
    for i, ch in enumerate(CHANNELS):
        is_sel = (i == ch_idx)
        safe_add(stdscr, row + i, 2, f"{ch['name']:<22}", SEL if is_sel else 0)

    # Colonna qualità
    streams = CHANNELS[ch_idx]["streams"]
    for i, (q_name, _) in enumerate(streams):
        is_sel = (i == q_idx)
        safe_add(stdscr, row + i, 30, f"{q_name:<20}", SEL if is_sel else 0)

    # Stato
    status_row = row + max(len(CHANNELS), len(streams)) + 1
    safe_add(stdscr, status_row, 0, "─" * 52, DIM)
    is_err = state["status"].startswith("ERRORE")
    safe_add(stdscr, status_row + 1, 2, state["status"], RED if is_err else YELLOW)

    # Info brano corrente
    meta_row = status_row + 2
    if state["track_updated"] > 0:
        _, w     = stdscr.getmaxyx()
        max_len  = max(0, w - 14)
        artist    = (state["track_artist"] or "—")[:max_len]
        title     = (state["track_title"]  or "—")[:max_len]
        album     = (state["track_album"]  or "—")[:max_len]
        duration  = state["track_duration"]
        elapsed   = state["track_elapsed"] + int(time.time() - state["track_updated"])
        remaining = max(0, duration - elapsed)

        safe_add(stdscr, meta_row,     2, f"Artista:  {artist}", CYAN)
        safe_add(stdscr, meta_row + 1, 2, f"Titolo:   {title}",  CYAN)
        safe_add(stdscr, meta_row + 2, 2, f"Album:    {album}",  CYAN)
        if duration > 0:
            safe_add(stdscr, meta_row + 3, 2,
                     f"Durata:   {fmt_time(duration)}  |  Rimanente: {fmt_time(remaining)}",
                     DIM)
        meta_row += 4

    stdscr.refresh()

# ── Loop principale ───────────────────────────────────────────────────────────

def main_loop(stdscr, player):
    curses.curs_set(0)
    stdscr.timeout(300)

    if state["autoplay"]:
        state["status"] = "Autoplay in corso..."
        threading.Thread(
            target=start_playback,
            args=(player, state["ch_idx"], state["q_idx"]),
            daemon=True,
        ).start()

    while True:
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

        elif key == curses.KEY_LEFT:
            state["focus"] = "channel"

        elif key == curses.KEY_UP:
            if focus == "channel":
                state["ch_idx"] = (ch_idx - 1) % n_ch
                state["q_idx"]  = min(q_idx, len(CHANNELS[state["ch_idx"]]["streams"]) - 1)
            else:
                state["q_idx"] = (q_idx - 1) % n_q

        elif key == curses.KEY_DOWN:
            if focus == "channel":
                state["ch_idx"] = (ch_idx + 1) % n_ch
                state["q_idx"]  = min(q_idx, len(CHANNELS[state["ch_idx"]]["streams"]) - 1)
            else:
                state["q_idx"] = (q_idx + 1) % n_q

        elif key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
            threading.Thread(
                target=start_playback,
                args=(player, state["ch_idx"], state["q_idx"]),
                daemon=True,
            ).start()

        elif key in (ord('s'), ord('S')):
            proc = state["proc"]
            if proc and proc.poll() is None:
                # in riproduzione → ferma, ricorda il canale
                stop_playback()
                state["status"] = "[] Stop  (S per riprendere)"
            elif state["playing_ch"] is not None:
                # fermo con canale salvato → riprendi
                threading.Thread(
                    target=start_playback,
                    args=(player, state["playing_ch"], state["playing_q"]),
                    daemon=True,
                ).start()

        elif key in (ord('a'), ord('A')):
            state["autoplay"] = not state["autoplay"]
            save_config()

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    player = detect_player()
    if not player:
        print("Errore: nessun player trovato.")
        print("Installa mpv con:  sudo apt install mpv")
        sys.exit(1)

    cfg = load_config()
    state["ch_idx"]   = min(cfg["ch_idx"], len(CHANNELS) - 1)
    state["q_idx"]    = min(cfg["q_idx"],  len(CHANNELS[state["ch_idx"]]["streams"]) - 1)
    state["autoplay"] = cfg["autoplay"]

    _meta_stop.clear()
    threading.Thread(target=_meta_poll_loop, daemon=True).start()

    try:
        curses.wrapper(lambda stdscr: main_loop(stdscr, player))
    except KeyboardInterrupt:
        pass
    finally:
        _meta_stop.set()
        stop_playback()
        print("\nArrivederci!\n")

if __name__ == "__main__":
    main()
