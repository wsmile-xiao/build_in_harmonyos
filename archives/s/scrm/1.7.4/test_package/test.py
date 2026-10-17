"""Consumer checks execute the installed package, never a build-tree binary."""
import subprocess
import sys


def run(*args):
    return subprocess.run([sys.argv[1], *args], capture_output=True, text=True, timeout=30)


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    print("ok - " + label)


v = run("--version")
check(v.returncode == 0 and v.stdout.strip() == "scrm 1.7.4", "installed version")
h = run("--help")
check(h.returncode == 0 and "Usage" in h.stdout, "installed help")
args = ("4", "2", "-t", "5", "-T", "-seed", "78361")
a = run(*args)
check(a.returncode == 0, "simulation exits successfully")
check(a.stdout.count("//") == 2, "two simulated loci")
check("segsites:" in a.stdout and ";" in a.stdout, "mutations and Newick trees")
b = run(*args)
check(b.returncode == 0 and a.stdout == b.stdout, "fixed seed reproducibility")
bad = run("not-a-sample-size", "1")
check(bad.returncode != 0, "invalid input rejected")
