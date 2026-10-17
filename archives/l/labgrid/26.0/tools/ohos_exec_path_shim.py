"""OHOS worker exec-PATH emulation shim — upstream-test runs only.

Copied by ``conanfile.py`` to ``<build>/testshim/sitecustomize.py`` and exposed
through ``PYTHONPATH``, so it is imported by the outer pytest process *and* by
every interpreter the suite spawns (they inherit the variable).

Why it exists
-------------
On the HarmonyOS worker sandbox the HAP-bundled interpreter cannot resolve a
*bare* program name the way POSIX requires. Handing the very same binary to
``subprocess`` as an absolute path works, as a bare name it does not::

    shutil.which("true")            -> '/bin/true'
    subprocess.run(["/bin/true"])   -> rc=0
    subprocess.run(["true"])        -> FileNotFoundError: [Errno 2] 'true'

A shell child is unaffected (``/bin/sh -c 'true'`` works), because the PATH
lookup then happens inside the shell instead of in the interpreter's spawn
path. This is a property of the sandbox the recipe builds in, not of the code
under test: labgrid is plain POSIX and spawns bare ``ssh`` / ``rsync`` / ``cat``
on real devices (``labgrid/util/ssh.py``, ``labgrid/driver/…``), and its test
suite spawns bare ``true`` / ``false`` / ``cat`` on purpose.

The shim restores the POSIX behaviour for the duration of the test run by
resolving the name in Python before the kernel is asked to execute it. Nothing
in the delivery is affected: the same upstream tree is built and packaged with
or without it, and the shim never reaches ``package_folder``.

``python`` has no on-disk binary on this worker at all (the interpreter is only
installed as ``python3``), yet several upstream test modules hardcode the name
``python``. It is therefore aliased to the running interpreter — which is also
what those tests mean by ``python``. (``conanfile.py`` additionally puts a
one-line ``python`` exec wrapper on PATH so that pexpect's own ``which()``
pre-check resolves it too.)

Both patches are idempotent and are applied once per interpreter.
"""

import os
import shutil
import sys

_which = shutil.which
_applied_flag = "_ohos_exec_path_shim_applied"

#: Bare names that have no binary of their own and must map to the interpreter
#: that is running the suite (and, by inheritance, its children).
ALIASES = {"python": sys.executable}


def resolve_program(name):
    """Return an executable path for `name`, or `name` unchanged.

    Absolute/relative paths are passed through untouched; a bare name is looked
    up in PATH with the platform's own resolver.
    """
    if not isinstance(name, str) or not name:
        return name
    if os.sep in name:
        return name
    if os.altsep and os.altsep in name:
        return name
    if name in ALIASES:
        return ALIASES[name]
    found = _which(name)
    return found or name


def _apply():
    if getattr(sys, _applied_flag, False):
        return
    setattr(sys, _applied_flag, True)

    import subprocess

    real_popen = subprocess.Popen

    class Popen(real_popen):
        """`subprocess.Popen` that resolves a bare program name first."""

        def __init__(self, args, *pargs, **kwargs):
            if kwargs.get("executable") is None and isinstance(args, (list, tuple)) and args:
                argv = list(args)
                argv[0] = resolve_program(argv[0])
                args = argv
            super().__init__(args, *pargs, **kwargs)

    subprocess.Popen = Popen

    def wrap(func):
        def wrapper(file, *pargs, **kwargs):
            return func(resolve_program(file), *pargs, **kwargs)

        wrapper.__name__ = getattr(func, "__name__", "exec")
        wrapper.__doc__ = getattr(func, "__doc__", None)
        return wrapper

    # `os.execv*` is the path taken by ptyprocess, i.e. every pexpect-based
    # spawn: ExternalConsoleDriver, the `…-client`/`…-exporter` subprocesses the
    # suite starts, and the upstream tests' own `pexpect.spawn("cat")`.
    for attr in ("execv", "execve", "execvp", "execvpe"):
        func = getattr(os, attr, None)
        if func is not None:
            setattr(os, attr, wrap(func))


_apply()
