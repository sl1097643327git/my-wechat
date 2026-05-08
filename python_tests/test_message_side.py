from wechat_overlay.message_side import SentCipherRegistry, message_side


def test_message_side_treats_file_transfer_messages_as_own() -> None:
    assert message_side("ENC[v1]:abc", is_file_transfer_chat=True, sent_registry=SentCipherRegistry()) == "right"


def test_message_side_treats_unmarked_non_file_transfer_messages_as_other() -> None:
    assert message_side("ENC[v1]:abc", is_file_transfer_chat=False, sent_registry=SentCipherRegistry()) == "left"


def test_message_side_treats_locally_sent_cipher_as_own() -> None:
    registry = SentCipherRegistry()
    registry.remember("ENC[v1]:abc")

    assert message_side("ENC[v1]:abc", is_file_transfer_chat=False, sent_registry=registry) == "right"
