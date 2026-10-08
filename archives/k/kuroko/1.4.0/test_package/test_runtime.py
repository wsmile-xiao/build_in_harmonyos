"""Validate the installed layout without using the source tree."""

import os
import subprocess
import sys


package, consumer = sys.argv[1:3]
interpreter = os.path.join(package, "bin", "kuroko")
libdir = os.path.join(package, "lib")
env = os.environ.copy()
env["LD_LIBRARY_PATH"] = libdir + os.pathsep + env.get("LD_LIBRARY_PATH", "")


def run(command):
    result = subprocess.run(command, env=env, cwd=os.path.dirname(consumer),
                            capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise AssertionError((command, result.returncode, result.stdout, result.stderr))
    return result.stdout


assert run([interpreter, "--version"]).strip() == "Kuroko 1.4.0"
paths = run([interpreter, "-M"])
assert os.path.join(libdir, "kuroko") in paths, paths

program = os.path.join(os.path.dirname(consumer), "smoke.krk")
with open(program, "w", encoding="utf-8") as stream:
    stream.write("import foo.bar.baz\nprint(foo.bar.baz.qux)\n")
output = run([interpreter, program])
assert "This is it!" in output, output

output = run([consumer])
assert "Kuroko 1.4.0" in output, output
output = run([os.path.join(package, "bin", "krk-demo")])
assert "Kuroko 1.4.0" in output, output
print("Kuroko packaged interpreter, module import, tool and C API: PASS")
