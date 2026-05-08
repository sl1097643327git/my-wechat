from wechat_overlay.input_keys import KeyAction, classify_enter_key


def test_plain_enter_sends_message():
    assert classify_enter_key(shift=False, control=False) == KeyAction.SEND


def test_shift_enter_inserts_newline():
    assert classify_enter_key(shift=True, control=False) == KeyAction.NEWLINE


def test_control_enter_inserts_newline():
    assert classify_enter_key(shift=False, control=True) == KeyAction.NEWLINE


def test_shift_control_enter_inserts_newline():
    assert classify_enter_key(shift=True, control=True) == KeyAction.NEWLINE
