from __future__ import annotations

import threading
import time

try:
    from .config import LAST_COMMAND_SENT, load_config
    from .serial_comms import initialize_serial
    from .voice_control import (
        V_CURRENT_VOICE_STATUS,
        V_LAST_SPEECH,
        V_VOICE_AVAIL,
        V_WAKE_DETECTED,
        voice_recognition_thread,
    )
    from .voice_web_bridge import publish_voice_command, publish_voice_snapshot
except ImportError:
    from config import LAST_COMMAND_SENT, load_config
    from serial_comms import initialize_serial
    from voice_control import (
        V_CURRENT_VOICE_STATUS,
        V_LAST_SPEECH,
        V_VOICE_AVAIL,
        V_WAKE_DETECTED,
        voice_recognition_thread,
    )
    from voice_web_bridge import publish_voice_command, publish_voice_snapshot


def main() -> None:
    load_config()
    initialize_serial()

    voice_thread = threading.Thread(target=voice_recognition_thread, daemon=True)
    voice_thread.start()

    last_command = LAST_COMMAND_SENT[0]
    while True:
        status = V_CURRENT_VOICE_STATUS[0]
        transcript = V_LAST_SPEECH[0]
        current_command = LAST_COMMAND_SENT[0]

        publish_voice_snapshot(
            {
                "status_text": status,
                "transcript": transcript,
                "available": bool(V_VOICE_AVAIL[0]),
                "awake": bool(V_WAKE_DETECTED[0]),
                "last_command": current_command,
            }
        )

        if current_command != last_command:
            if current_command and not str(current_command).startswith("失败"):
                publish_voice_command(current_command, {"status": status, "transcript": transcript})
            last_command = current_command

        time.sleep(0.2)


if __name__ == "__main__":
    main()