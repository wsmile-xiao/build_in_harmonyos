#!/usr/bin/env python3
"""Deterministic consumer checks for the packaged xmodem public API."""

from io import BytesIO

from xmodem import ACK, CAN, CRC, EOT, SOH, STX, XMODEM, XMODEM1k


checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


def transmit(mode, payload):
    replies = iter((CRC, ACK, ACK))
    writes = []

    def getc(size, timeout=1):
        del size, timeout
        return next(replies)

    def putc(data, timeout=1):
        del timeout
        writes.append(bytes(data))
        return len(data)

    modem = XMODEM(getc, putc, mode=mode)
    status = modem.send(BytesIO(payload), retry=1, timeout=1, quiet=True)
    return modem, status, writes


modem, status, writes = transmit("xmodem", b"hello")
check(status is True, "xmodem transfer failed")
check(len(writes) == 2, "xmodem write count mismatch")
check(writes[0][0:1] == SOH, "xmodem header byte mismatch")
check(writes[0][1] == 1, "xmodem sequence mismatch")
check(writes[0][2] == 0xFE, "xmodem complement mismatch")
check(writes[0][3:8] == b"hello", "xmodem payload mismatch")
check(writes[0][8:131] == b"\x1a" * 123, "xmodem padding mismatch")
check(len(writes[0]) == 133, "xmodem CRC frame length mismatch")
check(writes[0][-2:] == b"\x74\x90", "xmodem CRC mismatch")
check(writes[1] == EOT, "xmodem EOT mismatch")

modem1k, status1k, writes1k = transmit("xmodem1k", b"abc")
check(status1k is True, "xmodem1k transfer failed")
check(len(writes1k) == 2, "xmodem1k write count mismatch")
check(writes1k[0][0:1] == STX, "xmodem1k header byte mismatch")
check(len(writes1k[0]) == 1029, "xmodem1k CRC frame length mismatch")
check(writes1k[0][3:6] == b"abc", "xmodem1k payload mismatch")
check(writes1k[1] == EOT, "xmodem1k EOT mismatch")

check(modem.calc_checksum(b"abc") == 38, "checksum vector mismatch")
check(modem.calc_crc(b"123456789") == 0x31C3, "CRC vector mismatch")

abort_writes = []


def record_abort(data, timeout=1):
    del timeout
    abort_writes.append(data)
    return len(data)


abort_modem = XMODEM(lambda size, timeout=1: None, record_abort)
abort_modem.abort()
check(abort_writes == [CAN, CAN], "abort sequence mismatch")
check(
    isinstance(
        XMODEM1k(lambda size, timeout=1: None, lambda data: None),
        XMODEM,
    ),
    "XMODEM1k constructor mismatch",
)

expected_checks = 20
if checks != expected_checks:
    raise AssertionError(
        f"consumer assertion count mismatch: expected {expected_checks}, got {checks}"
    )

print(f"PASS: xmodem packaged API consumer test ({checks}/{expected_checks} assertions)")
