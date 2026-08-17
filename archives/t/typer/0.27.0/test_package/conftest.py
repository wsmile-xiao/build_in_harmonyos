"""Pytest configuration injected by the typer Conan test_package.

On HarmonyOS PC the sandbox blocks reads of ``/proc/1/stat`` which
``shellingham.detect_shell`` walks while detecting the current shell.
Any import of ``typer._completion_shared`` (transitively, ``import
typer``) triggers that walk and raises ``PermissionError``.

This conftest stubs ``shellingham.detect_shell`` before any test module
is imported, so:

1. The smoke gate in ``test_package/conanfile.py::test()`` can
   ``import typer`` cleanly.
2. The upstream pytest suite launched by ``run_upstream.py`` inherits
   the stub in the pytest main process; child ``coverage run``
   subprocesses get their own stub via the ``sitecustomize.py`` that
   ``run_upstream.py`` drops into the deps target dir.

The stub returns a fixed ``("bash", "/bin/bash")`` shell, matching what
``shellingham`` would detect on a normal Linux login session.
"""
import shellingham


def _stub_detect_shell(pid=None, max_depth=10):
    return ("bash", "/bin/bash")


if not getattr(shellingham, "_ohos_stubbed", False):
    shellingham.detect_shell = _stub_detect_shell
    shellingham._ohos_stubbed = True
