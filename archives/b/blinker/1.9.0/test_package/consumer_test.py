"""Consumer-level integration test for the installed blinker package."""

import blinker


def test_consumer_can_connect_and_send_signal():
    signal = blinker.Signal("consumer-event")
    received = []

    def consumer(sender, **kwargs):
        received.append((sender, kwargs))

    signal.connect(consumer)
    sender = object()
    signal.send(sender, value=42)

    assert received == [(sender, {"value": 42})]
