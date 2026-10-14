#!/usr/bin/env python3
"""Consumer verification for the installed udiskie 2.6.2 conan package.

Usage:
    test_udiskie_pkg.py <pkg> <site-packages> [<dep site-packages> ...]

Everything is executed for real (no mocks/stubs):
  * package layout (bin/ launchers + lib/pythonX.Y/site-packages/udiskie)
  * the four console scripts are executable, carry the OHOS-portable
    ``#!/usr/bin/env python3`` shebang and inject the package-relative
    site-packages (OHOS has no /usr/bin/python3 and no system site-packages)
  * ``import udiskie`` -> version, and the config/matcher logic exercised with
    the exact upstream ``test_match`` scenarios
  * OHOS packaging invariants: the module resolves under the package folder,
    the package is relocatable, and ``XDG_CONFIG_HOME`` is honoured

Prints a machine readable ``ASSERTIONS: passed=<n> failed=<m> total=<t>`` line
and exits non-zero (listing every failure) if any check fails.
"""
import os
import shutil
import subprocess
import sys
import tempfile

SCRIPTS = {
    "udiskie": "Daemon",
    "udiskie-mount": "Mount",
    "udiskie-umount": "Umount",
    "udiskie-info": "Info",
}
SITE_REL = None  # filled from argv
PASSED = 0
FAILURES = []


def check(ok, label, detail=""):
    global PASSED
    if ok:
        PASSED += 1
    else:
        FAILURES.append(f"{label}: {detail}")


def run_py(code, env):
    return subprocess.run([sys.executable, "-c", code], env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          timeout=120)


def main():
    global SITE_REL
    pkg = sys.argv[1]
    site = sys.argv[2]
    dep_sites = sys.argv[3:]
    SITE_REL = os.path.relpath(site, pkg)

    env = dict(os.environ)
    # Prepend the udiskie package site-packages; conanrun has already put the
    # python dependency site-packages (PyYAML, docopt) on PYTHONPATH.
    env["PYTHONPATH"] = os.pathsep.join(
        [p for p in [site] + dep_sites + [env.get("PYTHONPATH", "")] if p])
    env.pop("PYTHONHOME", None)
    pypath = env["PYTHONPATH"]

    # ---- 1. package layout ------------------------------------------------
    bindir = os.path.join(pkg, "bin")
    check(os.path.isdir(bindir), "bin/ exists", bindir)
    check(os.path.isdir(os.path.join(site, "udiskie")),
          "site-packages/udiskie exists", "")
    check(os.path.isfile(os.path.join(site, "udiskie", "__init__.py")),
          "udiskie/__init__.py present", "")
    icons = os.path.join(site, "udiskie", "icons")
    n_svg = len([f for f in os.listdir(icons)]) if os.path.isdir(icons) else 0
    check(n_svg >= 9, "udiskie/icons/*.svg packaged", f"found {n_svg}")
    check(os.path.isfile(os.path.join(site, "udiskie", "password_dialog.ui")),
          "password_dialog.ui packaged", "")
    # vendored pure-Python runtime deps (make the launchers self-contained)
    check(os.path.isfile(os.path.join(site, "docopt.py")),
          "vendored docopt.py present", "")
    check(os.path.isfile(os.path.join(site, "yaml", "__init__.py")),
          "vendored yaml package present", "")

    # ---- 2. launchers (OHOS portability) ----------------------------------
    for name, cls in SCRIPTS.items():
        path = os.path.join(bindir, name)
        check(os.path.isfile(path), f"launcher {name} present", path)
        if not os.path.isfile(path):
            continue
        mode = os.stat(path).st_mode
        check(bool(mode & 0o111), f"launcher {name} executable", oct(mode))
        with open(path) as f:
            body = f.read()
        check(body.startswith("#!/usr/bin/env python3\n"),
              f"launcher {name} portable shebang", body.splitlines()[0])
        check(f"from udiskie.cli import {cls}" in body,
              f"launcher {name} entry point", cls)
        # OHOS-specific: package-relative site-packages bootstrap
        check(SITE_REL in body.replace("\\\\", "\\"),
              f"launcher {name} injects package site-packages", SITE_REL)

    # ---- 3. import + version ---------------------------------------------
    r = run_py(
        "import os,udiskie;"
        "print(udiskie.__version__);"
        "print(os.path.dirname(udiskie.__file__))", env)
    out = r.stdout.decode().strip().splitlines()
    check(r.returncode == 0 and out and out[0] == "2.6.2",
          "import udiskie -> version 2.6.2", r.stdout.decode()[-300:])
    resolved = out[1] if len(out) > 1 else ""
    check(os.path.realpath(resolved) == os.path.realpath(
        os.path.join(site, "udiskie")),
        "import resolves under package folder", resolved)

    # ---- 4. upstream config/matcher scenarios (test_match logic) ----------
    r = run_py(
        "from udiskie.config import Config, match_config\n"
        "import tempfile, os\n"
        "class D:\n"
        "    def __init__(s,p,t,u):\n"
        "        s.device_file=p; s.id_type=t; s.id_uuid=u\n"
        "        s.partition_slave=None; s.luks_cleartext_slave=None\n"
        "d=tempfile.mkdtemp(); cf=os.path.join(d,'filters.conf')\n"
        "open(cf,'wt').write('''mount_options:\n"
        "- id_uuid: device-with-options\n"
        "  options: noatime,nouser\n"
        "- id_type: vfat\n"
        "  options: ro,nouser\n"
        "ignore_device:\n"
        "- id_uuid: ignored-DEVICE\n''')\n"
        "f=Config.from_file(cf).device_config\n"
        "ig=lambda dev: match_config(f,dev,'ignore',False)\n"
        "mo=lambda dev: match_config(f,dev,'options',None)\n"
        "print('ignored', bool(ig(D('/i','vfat','IGNORED-device'))),"
        " bool(ig(D('/o','vfat','device-with-options'))),"
        " bool(ig(D('/n','vfat','no-matching-id'))))\n"
        "print('uuid_opts', mo(D('/o','vfat','device-with-options')))\n"
        "print('type_opts', mo(D('/f','vfat','no-matching-id')))\n"
        "print('nomatch', mo(D('/n','ext','no-matching-id')))\n", env)
    lines = r.stdout.decode().strip().splitlines()
    ok = r.returncode == 0 and len(lines) == 4
    check(ok, "upstream config scenarios run", r.stdout.decode()[-300:])
    if ok:
        check(lines[0] == "ignored True False False",
              "match_config ignore_device", lines[0])
        check(lines[1] == "uuid_opts ['noatime', 'nouser']",
              "match_config options by uuid", lines[1])
        check(lines[2] == "type_opts ['ro', 'nouser']",
              "match_config options by type", lines[2])
        check(lines[3] == "nomatch None",
              "match_config no match -> None", lines[3])

    # ---- 5. OHOS packaging invariants ------------------------------------
    # 5a. relocatable: a copied package must import identically (no absolute
    #     reference to the original conan cache path baked into the files).
    tmp = tempfile.mkdtemp(prefix="udiskie-reloc-")
    try:
        shutil.copytree(os.path.join(site, "udiskie"),
                        os.path.join(tmp, "udiskie"))
        renv = dict(env)
        renv["PYTHONPATH"] = tmp
        r = run_py("import udiskie;print(udiskie.__version__)", renv)
        check(r.returncode == 0 and b"2.6.2" in r.stdout,
              "OHOS: package is relocatable", r.stdout.decode()[-300:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # 5b. XDG_CONFIG_HOME is honoured (OHOS home layout: ~/.config may be
    #     absent; the config search path must follow the env override).
    r = run_py(
        "import os\n"
        "os.environ['XDG_CONFIG_HOME']='/tmp/xdg-udiskie'\n"
        "from udiskie.config import Config\n"
        "p=Config.default_pathes()\n"
        "print(all(x.startswith('/tmp/xdg-udiskie/udiskie/') for x in p))", env)
    check(r.returncode == 0 and r.stdout.strip() == b"True",
          "OHOS: XDG_CONFIG_HOME honoured", r.stdout.decode()[-300:])

    # 5c. OHOS: the packaged launchers must actually execute. `--version` (and
    #     `--help`) must work even where the gi (PyGObject) runtime cannot be
    #     loaded - the entry point defers that import - so this is a real smoke
    #     test of the OHOS packaging, not just a static layout check.
    for name in SCRIPTS:
        path = os.path.join(bindir, name)
        if not os.path.isfile(path):
            continue
        r = subprocess.run([sys.executable, path, "--version"], env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=60)
        out = r.stdout.decode()
        check(r.returncode == 0 and "2.6.2" in out,
              f"OHOS: {name} --version executes", out[-200:])

    total = PASSED + len(FAILURES)
    print(f"ASSERTIONS: passed={PASSED} failed={len(FAILURES)} total={total}")
    for fail in FAILURES:
        print(f"  FAIL {fail}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
