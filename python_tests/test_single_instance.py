from wechat_overlay.single_instance import is_overlay_command, current_process_ids_to_stop


def test_is_overlay_command_matches_module_invocation():
    assert is_overlay_command("python -m wechat_overlay.app")
    assert is_overlay_command("C:/Python/python.exe -m wechat_overlay.app")
    assert not is_overlay_command("python other.py")


def test_current_process_ids_to_stop_excludes_self():
    processes = [
        (10, "python -m wechat_overlay.app"),
        (20, "python other.py"),
        (30, "python -m wechat_overlay.app"),
    ]

    assert current_process_ids_to_stop(processes, current_pid=10) == [30]
