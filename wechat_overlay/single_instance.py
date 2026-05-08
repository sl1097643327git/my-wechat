from __future__ import annotations

import os

import psutil


def is_overlay_command(command_line: str | None) -> bool:
    return bool(command_line and "-m wechat_overlay.app" in command_line)


def current_process_ids_to_stop(processes: list[tuple[int, str | None]], *, current_pid: int) -> list[int]:
    return [pid for pid, command_line in processes if pid != current_pid and is_overlay_command(command_line)]


def stop_existing_overlay_processes() -> list[int]:
    current_pid = os.getpid()
    candidates: list[tuple[int, str | None]] = []
    for process in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmdline = process.info.get("cmdline") or []
            command_line = " ".join(cmdline)
            candidates.append((int(process.info["pid"]), command_line))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, TypeError):
            continue

    stopped: list[int] = []
    for pid in current_process_ids_to_stop(candidates, current_pid=current_pid):
        try:
            psutil.Process(pid).terminate()
            stopped.append(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return stopped
