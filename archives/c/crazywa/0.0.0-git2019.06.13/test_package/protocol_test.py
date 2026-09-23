#!/usr/bin/env python3
"""Real, bounded XBoard protocol tests; each case starts an isolated engine."""
import os
import re
import selectors
import subprocess
import sys
import time
import unittest

EXECUTABLE = os.path.abspath(sys.argv.pop(1))


class ProtocolTest(unittest.TestCase):
    def setUp(self):
        self.engine = subprocess.Popen([EXECUTABLE], stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.engine.stdout, selectors.EVENT_READ)
        self.received = b""

    def tearDown(self):
        try:
            if self.engine.poll() is None:
                self.send("quit\n")
                self.engine.wait(timeout=3)
            self.assertEqual(self.engine.returncode, 0)
        finally:
            if self.engine.poll() is None:
                self.engine.kill()
                self.engine.wait()
            self.selector.close()
            self.engine.stdin.close()
            self.engine.stdout.close()

    def send(self, commands):
        self.engine.stdin.write(commands.encode())
        self.engine.stdin.flush()

    def receive(self, pattern):
        deadline = time.monotonic() + 15
        while True:
            match = re.search(pattern, self.received, re.MULTILINE)
            if match:
                result = self.received[:match.end()]
                self.received = self.received[match.end():]
                self.assertNotIn(b"Error:", result)
                self.assertNotIn(b"tellusererror", result)
                return result
            self.assertLess(time.monotonic(), deadline, repr(self.received))
            if self.selector.select(0.25):
                block = os.read(self.engine.stdout.fileno(), 65536)
                self.assertTrue(block, "Engine exited before the expected response")
                self.received += block

    def test_handshake(self):
        self.send("xboard\nprotover 2\n")
        output = self.receive(rb"^feature done=1\r?\n")
        self.assertIn(b'myname="CrazyWa 1.0.5"', output)
        self.assertIn(b"setboard=1", output)
        self.assertIn(b"crazywa,kyotoshogi", output)

    def test_ping(self):
        self.send("xboard\nping 7219\n")
        self.receive(rb"^pong 7219\r?\n")

    def test_malformed_move(self):
        self.send("new\nvariant crazyhouse\nforce\nusermove invalid\nping 7220\n")
        output = self.receive(rb"^pong 7220\r?\n")
        self.assertIn(b"Illegal move", output)

    def test_setboard(self):
        self.send("new\nvariant crazyhouse\nforce\n"
                  "setboard rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR[] b KQkq - 0 1\n"
                  "sd 1\ngo\n")
        output = self.receive(rb"^move [^\r\n]+\r?\n")
        move = re.search(rb"^move (\S+)", output, re.MULTILINE).group(1).decode()
        legal = {f"{f}7{f}{r}" for f in "abcdefgh" for r in "65"}
        legal.update(["b8a6", "b8c6", "g8f6", "g8h6"])
        self.assertIn(move, legal)


def variant_case(variant):
    def test(self):
        self.send(f"new\nvariant {variant}\nforce\nsd 1\ngo\n")
        output = self.receive(rb"^move [^\r\n]+\r?\n")
        self.assertRegex(output, rb"(?m)^move (?:[a-k][0-9]+[a-k][0-9]+[a-z+]?|[A-Z]@[a-k][0-9]+)\r?\n")
        self.assertNotIn(b"Illegal move", output)
    return test


for name in ("crazyhouse", "shogi", "minishogi", "judkinshogi", "torishogi", "euroshogi", "crazywa", "kyotoshogi"):
    setattr(ProtocolTest, "test_variant_" + name, variant_case(name))

if __name__ == "__main__":
    unittest.main(verbosity=2)
