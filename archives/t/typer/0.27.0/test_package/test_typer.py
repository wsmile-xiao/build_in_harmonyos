#!/usr/bin/env python3
"""Consumer smoke test for the packaged typer 0.27.0.

This test exercises typer's public API end-to-end: it builds a real
``typer.Typer`` application, invokes it through ``CliRunner``, and
asserts on the produced output. Crucially it shells out to the
packaged ``bin/typer`` console-script entry point — resolved strictly
from the typer package folder, never from the system ``PATH`` — so the
CI destructive negative test (R34/L1e) correctly fails when ``bin/``
is moved away.
"""

import os
import subprocess
import sys

import typer
from typer.testing import CliRunner


def _build_app() -> typer.Typer:
    app = typer.Typer()

    @app.command()
    def greet(name: str, excited: bool = False) -> None:
        """Greet someone, optionally with excitement."""
        msg = f"Hello, {name}!"
        if excited:
            msg = msg.upper()
        typer.echo(msg)

    @app.command()
    def add(a: int, b: int) -> None:
        """Print the sum of two integers."""
        typer.echo(a + b)

    return app


def _packaged_entry() -> str:
    """Resolve the packaged ``bin/typer`` entry point.

    The conan package installs pip entry points under ``bin/`` in the
    package folder. We resolve strictly from the typer module's
    install location and do NOT fall back to the system ``PATH`` —
    this keeps the test tied to the packaged ``bin/`` artifact so the
    R34/L1e negative test correctly fails when ``bin/`` is removed.
    """
    pkg_root = os.path.dirname(os.path.dirname(typer.__file__))
    entry = os.path.join(pkg_root, "bin", "typer")
    if not os.path.exists(entry):
        raise AssertionError(
            f"packaged `bin/typer` entry point not found under {pkg_root}"
        )
    return entry


def main() -> int:
    checks = 0

    # Version + symbol presence.
    assert typer.__version__ == "0.27.0", f"version mismatch: {typer.__version__}"
    assert hasattr(typer, "Typer"), "typer should expose the Typer class"
    checks += 2

    app = _build_app()
    runner = CliRunner()

    # greet command — plain output.
    result = runner.invoke(app, ["greet", "world"])
    assert result.exit_code == 0, f"greet failed: {result.output}"
    assert "Hello, world!" in result.output, f"unexpected output: {result.output}"
    checks += 2

    # greet command — --excited flag flips casing.
    result = runner.invoke(app, ["greet", "world", "--excited"])
    assert result.exit_code == 0, f"excited greet failed: {result.output}"
    assert "HELLO, WORLD!" in result.output, f"excited output wrong: {result.output}"
    checks += 2

    # add command — integer arithmetic.
    result = runner.invoke(app, ["add", "2", "3"])
    assert result.exit_code == 0, f"add failed: {result.output}"
    assert "5" in result.output, f"add output wrong: {result.output}"
    checks += 2

    # Invalid integer should produce a non-zero exit code (Click error).
    result = runner.invoke(app, ["add", "two", "3"])
    assert result.exit_code != 0, f"add should fail on bad int: {result.output}"
    checks += 1

    # Exercise the PACKAGED console-script entry point (bin/typer).
    # Resolved strictly from the package folder, never from PATH,
    # so L1e/R34 negative test correctly fails when bin/ is moved away.
    entry = _packaged_entry()
    # Use the packaged python interpreter (the entry shebang points to
    # the build env python); invoking it directly is the most faithful
    # way to exercise the packaged artifact.
    proc = subprocess.run(
        [entry, "--version"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"`{entry} --version` failed: {proc.stderr}"
    assert "0.27.0" in proc.stdout, f"version output unexpected: {proc.stdout}"
    checks += 3

    print(f"✓ typer {typer.__version__} imported")
    print(f"✓ built Typer app with 2 commands")
    print(f"✓ CliRunner invoked greet/add/excited ({checks} assertions)")
    print(f"✓ packaged entry point {entry} reports version 0.27.0")
    print("\n✅ All consumer smoke tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
