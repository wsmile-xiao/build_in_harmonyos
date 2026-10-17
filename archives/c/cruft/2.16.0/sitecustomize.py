"""HarmonyOS subprocess compatibility shim for the Conan-packaged cruft app.

On OHOS the system Python uses ``posix_spawn`` to launch subprocesses.
When a bare command name (e.g. ``"git"``) is passed without an absolute
path, ``posix_spawn`` does **not** search ``PATH`` – the call silently
fails.  This module intercepts ``subprocess.Popen.__init__`` and resolves
bare commands to their absolute path via ``shutil.which`` so that cruft
(and its dependency cookiecutter) can invoke ``git`` normally.

The patch is applied **only** on OHOS and only once.
"""

import os
import shutil
import subprocess
import sys
import sysconfig


def _is_harmonyos():
    """Return True when running on an OHOS / HarmonyOS system."""
    platform = sysconfig.get_platform().lower()
    soabi = (sysconfig.get_config_var("SOABI") or "").lower()
    return (
        sys.platform.startswith(("ohos", "harmonyos"))
        or "ohos" in platform
        or "ohos" in soabi
    )


def _resolve_command(command):
    """Resolve a bare command name to an absolute path.

    Returns ``None`` when *command* is already an absolute/relative path
    or is not a string-like object.
    """
    if not isinstance(command, (str, bytes, os.PathLike)):
        return None
    command = os.fspath(command)
    if os.path.dirname(command):
        return None
    return shutil.which(command)


if _is_harmonyos() and not getattr(
    subprocess.Popen.__init__, "_ohos_path_fix", False
):
    _original_popen_init = subprocess.Popen.__init__

    def _popen_init(self, args, *popenargs, **kwargs):
        executable = kwargs.get("executable")
        if executable is not None:
            resolved = _resolve_command(executable)
            if resolved is not None:
                kwargs["executable"] = resolved
        elif isinstance(args, (list, tuple)) and args:
            resolved = _resolve_command(args[0])
            if resolved is not None:
                args = list(args)
                args[0] = resolved
        elif isinstance(args, (str, bytes, os.PathLike)):
            resolved = _resolve_command(args)
            if resolved is not None:
                args = resolved

        _original_popen_init(self, args, *popenargs, **kwargs)

    _popen_init._ohos_path_fix = True
    subprocess.Popen.__init__ = _popen_init
