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

# ── Canali e stream ───────────────────────────────────────────────────────────

CHANNELS = [
    {
        "name": "Main (Eclectic)",
        "streams": [
            ("FLAC 192kHz", "https://stream.motherearthradio.de/listen/motherearth/motherearth"),
            ("FLAC 96kHz",    "https://stream.motherearthradio.de/listen/motherearth/motherearth.flac-lo"),
            ("AAC 320kbps",   "https://stream.motherearthradio.de/listen/motherearth/motherearth.aac"),
            ("MP3 320kbps",   "https://stream.motherearthradio.de/listen/motherearth/motherearth.mp3"),
        ]
    },
    {
        "name": "Jazz",
        "streams": [
            ("FLAC 192kHz", "https://stream.motherearthradio.de/listen/motherearth_jazz/motherearth.jazz"),
            ("FLAC 96kHz",    "https://stream.motherearthradio.de/listen/motherearth_jazz/motherearth.jazz.flac-lo"),
            ("AAC 320kbps",   "https://stream.motherearthradio.de/listen/motherearth_jazz/motherearth.jazz.aac"),
            ("MP3 320kbps",   "https://stream.motherearthradio.de/listen/motherearth_jazz/motherearth.jazz.mp3"),
        ]
    },
    {
        "name": "Classical",
        "streams": [
            ("FLAC 192kHz", "https://stream.motherearthradio.de/listen/motherearth_klasseik/motherearth.klasseik"),
            ("FLAC 96kHz",    "https://stream.motherearthradio.de/listen/motherearth_klasseik/motherearth.klasseik.flac-lo"),
            ("AAC 320kbps",   "https://stream.motherearthradio.de/listen/motherearth_klasseik/motherearth.klasseik.aac"),
            ("MP3 320kbps",   "https://stream.motherearthradio.de/listen/motherearth_klasseik/motherearth.klasseik.mp3"),
        ]
    },
    {
        "name": "Instrumental",
        "streams": [
            ("FLAC 192kHz", "https://stream.motherearthradio.de/listen/motherearth_instrumental/motherearth.instrumental"),
            ("FLAC 96kHz",    "https://stream.motherearthradio.de/listen/motherearth_instrumental/motherearth.instrumental.flac-lo"),
            ("AAC 320kbps",   "https://stream.motherearthradio.de/listen/motherearth_instrumental/motherearth.instrumental.aac"),
            ("MP3 320kbps",   "https://stream.motherearthradio.de/listen/motherearth_instrumental/motherearth.instrumental.mp3"),
        ]
    },
]

# ── Stato globale ─────────────────────────────────────────────────────────────

state = {
    "proc":       None,
    "ch_idx":     0,
    "q_idx":      0,
    "playing_ch": None,
    "playing_q":  None,
    "focus":      "channel",   # "channel" | "quality"
    "status":     "Premi INVIO per avviare la riproduzione",
}

proc_lock = threading.Lock()

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
        return ["mpv", "--no-video", "--msg-level=all=error", url]
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

def start_playback(player, ch_idx, q_idx):
    stop_playback()
    url = CHANNELS[ch_idx]["streams"][q_idx][1]
    cmd = build_cmd(player, url)
    with proc_lock:
        state["proc"] = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    state["playing_ch"] = ch_idx
    state["playing_q"]  = q_idx
    ch_name = CHANNELS[ch_idx]["name"]
    q_name  = CHANNELS[ch_idx]["streams"][q_idx][0]
    state["status"] = f">> {ch_name}  |  {q_name}"

# ── Disegno curses ────────────────────────────────────────────────────────────

BANNER = [
    "╔══════════════════════════════════════════════════╗",
    "║       Mother Earth Radio  Player  Hi-Res         ║",
    "║         FLAC Streaming  192kHz / 24bit           ║",
    "╚══════════════════════════════════════════════════╝",
]

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
    curses.init_pair(6, curses.COLOR_BLACK,  curses.COLOR_WHITE)  # cursore: barra grigia

    GREEN  = curses.color_pair(1) | curses.A_BOLD
    CYAN   = curses.color_pair(2)
    YELLOW = curses.color_pair(3) | curses.A_BOLD
    SEL    = curses.color_pair(6)  # cursore: barra grigia testo nero
    DIM    = curses.A_DIM

    stdscr.erase()

    # Banner
    row = 0
    for line in BANNER:
        safe_add(stdscr, row, 0, line, GREEN)
        row += 1
    row += 1

    # Intestazioni
    safe_add(stdscr, row, 2, "CANALE", CYAN | curses.A_BOLD if state["focus"] == "channel" else CYAN)
    safe_add(stdscr, row, 30, "QUALITA'", CYAN | curses.A_BOLD if state["focus"] == "quality" else CYAN)
    row += 1
    safe_add(stdscr, row, 2,  "─" * 24, DIM)
    safe_add(stdscr, row, 30, "─" * 20, DIM)
    row += 1

    ch_idx = state["ch_idx"]
    q_idx  = state["q_idx"]
    focus  = state["focus"]

    # Colonna canali
    for i, ch in enumerate(CHANNELS):
        is_sel = (i == ch_idx)
        name_label = f"  {ch['name']:<22}"
        safe_add(stdscr, row + i, 2, name_label, SEL if is_sel else 0)

    # Colonna qualità
    streams = CHANNELS[ch_idx]["streams"]
    for i, (q_name, _) in enumerate(streams):
        is_sel = (i == q_idx)
        name_label = f"  {q_name:<20}"
        safe_add(stdscr, row + i, 30, name_label, SEL if is_sel else 0)

    # Stato
    status_row = row + max(len(CHANNELS), len(streams)) + 2
    safe_add(stdscr, status_row,     0, "─" * 52, DIM)
    safe_add(stdscr, status_row + 1, 2, state["status"], YELLOW)

    # Legenda
    leg = status_row + 3
    safe_add(stdscr, leg,     2, "Frecce: naviga   ->/<-: cambia colonna", DIM)
    safe_add(stdscr, leg + 1, 2, "INVIO: riproduci   S: stop   Q: esci", DIM)

    stdscr.refresh()

# ── Loop principale ───────────────────────────────────────────────────────────

def main_loop(stdscr, player):
    curses.curs_set(0)
    stdscr.timeout(300)

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
                state["q_idx"]  = 0
            else:
                state["q_idx"] = (q_idx - 1) % n_q

        elif key == curses.KEY_DOWN:
            if focus == "channel":
                state["ch_idx"] = (ch_idx + 1) % n_ch
                state["q_idx"]  = 0
            else:
                state["q_idx"] = (q_idx + 1) % n_q

        elif key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
            threading.Thread(
                target=start_playback,
                args=(player, state["ch_idx"], state["q_idx"]),
                daemon=True,
            ).start()

        elif key in (ord('s'), ord('S')):
            stop_playback()
            state["playing_ch"] = None
            state["playing_q"]  = None
            state["status"]     = "[] Stop"

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    player = detect_player()
    if not player:
        print("Errore: nessun player trovato.")
        print("Installa mpv con:  sudo apt install mpv")
        sys.exit(1)

    try:
        curses.wrapper(lambda stdscr: main_loop(stdscr, player))
    except KeyboardInterrupt:
        pass
    finally:
        stop_playback()
        print("\nArrivederci!\n")

if __name__ == "__main__":
    main()