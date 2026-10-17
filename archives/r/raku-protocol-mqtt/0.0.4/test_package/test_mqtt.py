#!/usr/bin/env python3
"""Execute and verify Protocol::MQTT consumer behavior."""

import subprocess
import sys


raku, script = sys.argv[1:]
result = subprocess.run([raku, script], check=True, text=True, capture_output=True)
actual = result.stdout.splitlines()
expected = [
    "connect-wire=101b00044d5154540402001e000f61746f6d636f64652d636c69656e74",
    "publish-wire=3214000c73656e736f72732f74656d70002a32332e35",
    "decoded-type=Protocol::MQTT::Packet::Publish",
    "decoded-topic=sensors/temp",
    "decoded-packet-id=42",
    "decoded-payload=23.5",
    "filter-match=yes",
    "filter-reject=yes",
    "oversize-length=rejected",
    "mqtt-consumer=ok",
]
assert actual == expected, f"unexpected Protocol::MQTT output: {actual!r}"
print("Protocol::MQTT consumer behavior checks passed: 10/10")
