import os
import sys

from ptyprocess import PtyProcess, PtyProcessUnicode


# Consumer test: import the packaged API and exercise a real child process
# through the installed package, rather than testing only package metadata.
env = os.environ.copy()
env["PTYPROCESS_CONSUMER"] = "ok"
process = PtyProcess.spawn(
    ["sh", "-c", "printf 'consumer:%s\\n' \"$PTYPROCESS_CONSUMER\""],
    env=env,
)
output = process.read().decode("ascii")
assert "consumer:ok" in output
assert process.wait() == 0

unicode_process = PtyProcessUnicode.spawn(["sh", "-c", "printf 'unicode\\n'"])
assert "unicode" in unicode_process.read()
assert unicode_process.wait() == 0

print("ptyprocess consumer test passed", sys.version.split()[0])
