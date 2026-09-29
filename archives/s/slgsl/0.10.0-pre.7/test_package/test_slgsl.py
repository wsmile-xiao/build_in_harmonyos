#!/usr/bin/env python3
"""Consumer test for slgsl/0.10.0-pre.7.

The S-Lang modules are dlopen()ed by the ``slsh`` interpreter, so the
consumer test runs a small S-Lang script through the packaged module set and
asserts real numerical output.  This Python driver exists so the package
ships a test source file recognised by CI L0c (.py); the S-Lang program below
is the artefact actually executed.
"""
import os
import subprocess
import sys
import tempfile

SCRIPT = r"""
% Load the packaged GSL bindings and exercise a real random-number API.
require ("gslrand");
require ("gslconst");

variable r = rng_alloc ();
variable a = ran_ugaussian (r, 1000);
variable mean = sum (a) / length (a);

% 1000 standard-normal samples: the mean must sit near zero.
if (abs (mean) > 0.2)
  {
     () = fprintf (stderr, "mean out of range: %g\n", mean);
     exit (1);
  }
() = fprintf (stdout, "sample mean %g over %d draws\n", mean, length (a));

% The constants module must expose real GSL constants.
if (CONST_MKSA_SPEED_OF_LIGHT < 2.9e8 || CONST_MKSA_SPEED_OF_LIGHT > 3.1e8)
  {
     () = fprintf (stderr, "bad c: %g\n", CONST_MKSA_SPEED_OF_LIGHT);
     exit (1);
  }
() = fprintf (stdout, "c = %g m/s\n", CONST_MKSA_SPEED_OF_LIGHT);
() = fprintf (stdout, "SLGSL-CONSUMER-OK\n");
exit (0);
"""


def main():
    pkgdir = sys.argv[1]
    slsh = sys.argv[2]
    assert os.path.isfile(slsh), "slsh interpreter missing: %s" % slsh

    tmp = tempfile.mkdtemp(prefix="slgsl-test-")
    script = os.path.join(tmp, "consumer.sl")
    with open(script, "w") as fh:
        fh.write(SCRIPT)

    env = dict(os.environ)
    env["SLSH_CONF_DIR"] = os.environ["SLGSL_SLSH_CONF_DIR"]
    env["SLSH_PATH"] = "%s:%s" % (os.path.join(pkgdir, "share", "slsh",
                                               "local-packages"),
                                  os.environ["SLGSL_SLANG_SLSH_PATH"])
    mods = []
    for root, _dirs, files in os.walk(os.path.join(pkgdir, "lib", "slang")):
        if any(f.endswith("-module.so") for f in files):
            mods.append(root)
    assert mods, "no *-module.so found under %s/lib/slang" % pkgdir
    env["SLANG_MODULE_PATH"] = ":".join(mods)

    proc = subprocess.run([slsh, script], capture_output=True, text=True,
                          env=env, timeout=300)
    out = (proc.stdout or "") + (proc.stderr or "")
    print(out)
    assert proc.returncode == 0, "slsh consumer failed (rc=%d)" % proc.returncode
    assert "SLGSL-CONSUMER-OK" in out, out


main()
