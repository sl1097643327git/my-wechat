import pytest

from wechat_overlay.wechat_uia import SendSafetyError, contains_file_transfer_assistant, is_wechat_process_name, require_file_transfer, should_show_overlay


def test_is_wechat_process_name_accepts_windows_wechat_processes():
    assert is_wechat_process_name("Weixin")
    assert is_wechat_process_name("WeChat")
    assert is_wechat_process_name("WeChatAppEx")
    assert not is_wechat_process_name("WindowsTerminal")


def test_contains_file_transfer_assistant_checks_texts():
    assert contains_file_transfer_assistant(["聊天", "文件传输助手"])
    assert not contains_file_transfer_assistant(["聊天", "张三"])


def test_require_file_transfer_rejects_other_chats():
    with pytest.raises(SendSafetyError):
        require_file_transfer(["聊天", "张三"])


def test_require_file_transfer_accepts_file_transfer():
    require_file_transfer(["聊天", "文件传输助手"])


def test_should_show_overlay_requires_foreground_wechat_process():
    assert should_show_overlay(wechat_pid=42, foreground_pid=42)
    assert not should_show_overlay(wechat_pid=42, foreground_pid=99)
    assert not should_show_overlay(wechat_pid=None, foreground_pid=42)
