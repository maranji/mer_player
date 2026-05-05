#!/usr/bin/env python3
"""
Mother Earth Radio - Player per Linux
Richiede: vlc oppure mpv installato sul sistema
Installa dipendenze Python: pip install requests
"""

import subprocess
import sys
import os

# ── Canali disponibili ────────────────────────────────────────────────────────

CHANNELS = {
    "1": {
        "name": "🌍 Main (Eclectic)",
        "streams": {
            "FLAC 192kHz": "https://stream.motherearthradio.de/listen/motherearth/motherearth",
            "FLAC 96kHz":  "https://stream.motherearthradio.de/listen/motherearth/motherearth.flac-lo",
            "AAC 320kbps": "https://stream.motherearthradio.de/listen/motherearth/motherearth.aac",
            "MP3 320kbps": "https://stream.motherearthradio.de/listen/motherearth/motherearth.mp3",
        }
    },
    "2": {
        "name": "🎷 Jazz",
        "streams": {
            "FLAC 192kHz": "https://stream.motherearthradio.de/listen/motherearth_jazz/motherearth.jazz",
            "FLAC 96kHz":  "https://stream.motherearthradio.de/listen/motherearth_jazz/motherearth.jazz.flac-lo",
            "AAC 320kbps": "https://stream.motherearthradio.de/listen/motherearth_jazz/motherearth.jazz.aac",
            "MP3 320kbps": "https://stream.motherearthradio.de/listen/motherearth_jazz/motherearth.jazz.mp3",
        }
    },
    "3": {
        "name": "🎻 Classical (Klassik)",
        "streams": {
            "FLAC 192kHz": "https://stream.motherearthradio.de/listen/motherearth_klasseik/motherearth.klasseik",
            "FLAC 96kHz":  "https://stream.motherearthradio.de/listen/motherearth_klasseik/motherearth.klasseik.flac-lo",
            "AAC 320kbps": "https://stream.motherearthradio.de/listen/motherearth_klasseik/motherearth.klasseik.aac",
            "MP3 320kbps": "https://stream.motherearthradio.de/listen/motherearth_klasseik/motherearth.klasseik.mp3",
        }
    },
    "4": {
        "name": "🎸 Instrumental",
        "streams": {
            "FLAC 192kHz": "https://stream.motherearthradio.de/listen/motherearth_instrumental/motherearth.instrumental",
            "FLAC 96kHz":  "https://stream.motherearthradio.de/listen/motherearth_instrumental/motherearth.instrumental.flac-lo",
            "AAC 320kbps": "https://stream.motherearthradio.de/listen/motherearth_instrumental/motherearth.instrumental.aac",
            "MP3 320kbps": "https://stream.motherearthradio.de/listen/motherearth_instrumental/motherearth.instrumental.mp3",
        }
    },
}

QUALITY_ORDER = ["FLAC 192kHz", "FLAC 96kHz", "AAC 320kbps", "MP3 320kbps"]

# ── Colori ANSI ───────────────────────────────────────────────────────────────

GREEN   = "\033[92m"
CYAN    = "\033[96m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
RESET   = "\033[0m"

# ── Utility ───────────────────────────────────────────────────────────────────

def clear():
    os.system("clear")

def detect_player():
    """Rileva il player disponibile sul sistema."""
    for player in ["mpv", "vlc", "ffplay"]:
        if subprocess.call(["which", player], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
            return player
    return None

def build_command(player, url):
    """Costruisce il comando per il player scelto."""
    if player == "mpv":
        return ["mpv", "--no-video", "--msg-level=all=error", url]
    elif player == "vlc":
        return ["vlc", "--no-video", "--quiet", url]
    elif player == "ffplay":
        return ["ffplay", "-nodisp", "-loglevel", "error", url]

# ── UI ────────────────────────────────────────────────────────────────────────

def print_banner():
    print(f"""
{GREEN}{BOLD}╔══════════════════════════════════════════════════╗
║        🌿  Mother Earth Radio  Player  🌿        ║
║         Hi-Res FLAC Streaming · 192kHz           ║
╚══════════════════════════════════════════════════╝{RESET}
""")

def choose_channel():
    print(f"{CYAN}{BOLD}  Scegli un canale:{RESET}\n")
    for key, ch in CHANNELS.items():
        print(f"  {BOLD}{key}{RESET}  {ch['name']}")
    print(f"  {BOLD}q{RESET}  Esci\n")

    while True:
        choice = input(f"{YELLOW}  Canale [{'/'.join(CHANNELS.keys())}/q]: {RESET}").strip().lower()
        if choice == "q":
            print(f"\n{DIM}  Arrivederci!{RESET}\n")
            sys.exit(0)
        if choice in CHANNELS:
            return choice
        print(f"{RED}  Scelta non valida.{RESET}")

def choose_quality(channel_key):
    ch = CHANNELS[channel_key]
    print(f"\n{CYAN}{BOLD}  Qualità audio per {ch['name']}:{RESET}\n")
    keys = list(ch["streams"].keys())
    for i, q in enumerate(keys, 1):
        star = f"{GREEN}★{RESET}" if q == "FLAC 192kHz" else " "
        print(f"  {BOLD}{i}{RESET}  {star} {q}")
    print(f"  {BOLD}b{RESET}  ← Indietro\n")

    while True:
        choice = input(f"{YELLOW}  Qualità [1-{len(keys)}/b]: {RESET}").strip().lower()
        if choice == "b":
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(keys):
            return keys[int(choice) - 1]
        print(f"{RED}  Scelta non valida.{RESET}")

def play(player, channel_key, quality):
    ch = CHANNELS[channel_key]
    url = ch["streams"][quality]
    cmd = build_command(player, url)

    clear()
    print_banner()
    print(f"  {GREEN}▶  In riproduzione:{RESET}  {BOLD}{ch['name']}{RESET}")
    print(f"  {DIM}Qualità:{RESET}  {quality}")
    print(f"  {DIM}Player: {player}{RESET}")
    print(f"  {DIM}URL:    {url}{RESET}")
    print(f"\n  {YELLOW}Premi Ctrl+C per fermare e tornare al menu.{RESET}\n")

    proc = None
    try:
        proc = subprocess.Popen(cmd)
        proc.wait()
    except KeyboardInterrupt:
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
        print(f"\n  {DIM}Riproduzione interrotta.{RESET}\n")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    clear()
    print_banner()

    player = detect_player()
    if not player:
        print(f"{RED}{BOLD}  Errore: nessun player trovato.{RESET}")
        print(f"  Installa VLC o MPV con:\n")
        print(f"  {CYAN}sudo apt install mpv{RESET}  oppure  {CYAN}sudo apt install vlc{RESET}\n")
        sys.exit(1)

    print(f"  {DIM}Player rilevato: {BOLD}{player}{RESET}\n")

    while True:
        channel_key = choose_channel()
        quality = choose_quality(channel_key)
        if quality is None:
            clear()
            print_banner()
            continue
        play(player, channel_key, quality)
        clear()
        print_banner()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{DIM}  Uscita.{RESET}\n")
        sys.exit(0)