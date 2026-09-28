"""End-to-end consumer test for the installed mmc binary.

It reproduces the real consumer flow: a card information directory, as
exported by the kernel under /sys/class/mmc_host/mmcX/mmcX:XXXX, is built
and the shipped 'mmc cid read' command is executed on it, then every decoded CID
field is then validated, and the inline register interface is cross-checked.
"""
import os
import subprocess
import sys

MMC = sys.argv[1]
CID = "035344534430303180011a35960180b6"

EXPECTED = [
    "manufacturer: 'SanDisk' 'SD'",
    "product: 'SD001' 8.0",
    "serial: 0x011a3596",
    "manufacturing date: 2024 jan",
]

CARD = os.path.join(os.getcwd(), "mmc-card")
os.makedirs(CARD, exist_ok=True)

with open(os.path.join(CARD, "type"), "w") as handle:
    handle.write("SD")

with open(os.path.join(CARD, "cid"), "w") as handle:
    handle.write(CID)

by_dir = subprocess.run([MMC, "cid", "read", CARD], capture_output=True, text=True)
print("run: mmc cid read", CARD)
print("exit code:", by_dir.returncode)
print(by_dir.stdout, end="")
print(by_dir.stderr, end="")

by_reg = subprocess.run(
    [MMC, "cid", "read", "-b", "sd", "-r", CID], capture_output=True, text=True
)
print("run: mmc cid read -b sd -r", CID)
print("exit code:", by_reg.returncode)
print(by_reg.stdout, end="")
print(by_reg.stderr, end="")

checks = [
    ("directory flow exit code 0", by_dir.returncode == 0),
    ("inline register flow exit code 0", by_reg.returncode == 0),
    ("inline flow matches directory flow", by_reg.stdout == by_dir.stdout),
]
for line in EXPECTED:
    checks.append((line, line in by_dir.stdout))

for label, ok in checks:
    print("PASS" if ok else "FAIL", label)

failed = len([label for label, ok in checks if not ok])
print("consumer end-to-end checks:", len(checks), "failed:", failed)
sys.exit(1 if failed else 0)
