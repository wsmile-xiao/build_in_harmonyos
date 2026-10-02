#!/usr/bin/env python3
"""Consumer test for the packaged keyd-application-mapper 2.6.0.

The packaged command is executed through the Conan run environment - the
interpreter is deliberately not launched directly, so the patched shebang has to
resolve on its own, exactly as it does on a user's machine.

Everything asserted here is observable without a display server and without a
running keyd daemon, which is what the CI worker can offer: the packaged
command, its interpreter line, its argument surface, the config discovery path,
the single-instance lock and the installed man page.
"""
import gzip
import os
import shutil
import subprocess
import sys
import tempfile

failures = []
checks = 0


def check(condition, message):
    global checks
    checks += 1
    if not condition:
        failures.append(message)


TOOL = shutil.which("keyd-application-mapper")
check(TOOL is not None, "keyd-application-mapper is not on the Conan run PATH")
if not TOOL:
    print("FATAL: the packaged command is not on PATH")
    sys.exit(1)
print("keyd-application-mapper:", TOOL)

PACKAGE = os.path.dirname(os.path.dirname(os.path.realpath(TOOL)))
DE_ENV = ("DISPLAY", "WAYLAND_DISPLAY", "XDG_CURRENT_DESKTOP",
          "GNOME_SETUP_DISPLAY", "KDE_SESSION_VERSION")

# -- 1. OHOS adaptation: the interpreter line must not be the absolute path that
#       upstream hard-codes for its build machine.
with open(TOOL, "r", encoding="utf-8") as handle:
    shebang = handle.readline().strip()
check(shebang == "#!/usr/bin/env python3",
      "shebang should be '#!/usr/bin/env python3' after the OHOS patch, got %r"
      % shebang)
check(os.path.exists("/usr/bin/env"), "/usr/bin/env is missing on this platform")

# -- 2. The declared python/3.12.9 dependency must supply the interpreter the
#       shebang resolves to.
check(shutil.which("python3") is not None,
      "python3 is not on PATH - the declared python dependency is not consumed")

# -- 3. Command is executable and documents its own argument surface.
check(bool(os.stat(TOOL).st_mode & 0o111) or os.access(TOOL, os.X_OK),
      "the packaged command is not executable")
result = subprocess.run([TOOL, "-h"], capture_output=True, text=True, timeout=180)
check(result.returncode == 0, "`-h` should exit 0, got %d" % result.returncode)
check("usage: keyd-application-mapper" in result.stdout,
      "`-h` does not print the usage line")
check("--daemonize" in result.stdout and "--verbose" in result.stdout,
      "`-h` does not document --daemonize/--verbose")

with tempfile.TemporaryDirectory() as home:
    env = {key: value for key, value in os.environ.items() if key not in DE_ENV}
    env["HOME"] = home

    # -- 4. Config discovery without ~/.config/keyd/app.conf.
    result = subprocess.run([TOOL], capture_output=True, text=True,
                            timeout=180, env=env)
    output = result.stdout + result.stderr
    check("could not find app.conf" in output,
          "missing-config path not reached, output was %r" % output[:200])

    # -- 5. Real execution path: with a config file present the script parses it,
    #       takes the single-instance lock and then fails to find a window
    #       monitor because no display server is available.
    config_dir = os.path.join(home, ".config", "keyd")
    os.makedirs(config_dir)
    with open(os.path.join(config_dir, "app.conf"), "w", encoding="utf-8") as handle:
        handle.write("[kitty]\nalt.] = C-tab\nalt.[ = C-S-tab\n")

    result = subprocess.run([TOOL], capture_output=True, text=True,
                            timeout=180, env=env)
    output = result.stdout + result.stderr
    check("Could not detect app environment" in output,
          "headless run did not reach window-monitor detection, output was %r"
          % output[:200])
    check(result.returncode != 0,
          "headless run should fail once no window monitor is available (rc=%d)"
          % result.returncode)
    lock = os.path.join(config_dir, "app.lock")
    lock_exists = os.path.isfile(lock)
    check(lock_exists, "the single-instance lock file app.lock was not created")
    check(lock_exists and os.path.getsize(lock) == 0,
          "app.lock should exist and be empty (exists=%s, size=%s)"
          % (lock_exists, os.path.getsize(lock) if lock_exists else "n/a"))

    # -- 6. -v is accepted alongside a config file.
    result = subprocess.run([TOOL, "-v"], capture_output=True, text=True,
                            timeout=180, env=env)
    check("Could not detect app environment" in (result.stdout + result.stderr),
          "`-v` run did not reach window-monitor detection")

# -- 7. Documentation shipped together with the command.
man = os.path.join(PACKAGE, "share", "man", "man1", "keyd-application-mapper.1.gz")
check(os.path.isfile(man), "share/man/man1/keyd-application-mapper.1.gz is not installed")
if os.path.isfile(man):
    with gzip.open(man, "rt", encoding="utf-8", errors="replace") as handle:
        manpage = handle.read(2048)
    check("keyd-application-mapper" in manpage and ".TH" in manpage,
          "the installed man page does not look like the upstream document")

print("checks: %d, failures: %d" % (checks, len(failures)))
for failure in failures:
    print("FAIL:", failure)
sys.exit(1 if failures else 0)
