import ast
import hashlib
import os
import subprocess
import sys
import tempfile
import uuid


EXPECTED_VERSION = "laniakea-spark 0.1.1"
EXPECTED_UUID = str(
    uuid.uuid5(uuid.UUID("d44a99a2-0b5d-415b-808a-790ad4684309"), "ohpcd-builder")
)
EXPECTED_SHA256 = hashlib.sha256(b"abc").hexdigest()


def run_python_tool(tool, *args):
    env = os.environ.copy()
    return subprocess.run(
        [sys.executable, tool, *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


def output(result):
    return (
        f"exit={result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def main():
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: test_laniakea_spark.py <lk-spark> <package-folder> <pydeps>"
        )

    tool = sys.argv[1]
    package_folder = sys.argv[2]
    pydeps = sys.argv[3]
    python_root = os.path.join(package_folder, "lib", "python")
    assert os.path.isdir(python_root), f"missing packaged Python root: {python_root}"
    assert os.path.isdir(pydeps), f"missing Python dependency root: {pydeps}"
    sys.path.insert(0, pydeps)
    sys.path.insert(1, python_root)

    version = run_python_tool(tool, "--version")
    assert version.returncode == 0, output(version)
    assert version.stdout.strip() == EXPECTED_VERSION, output(version)

    help_result = run_python_tool(tool, "--help")
    assert help_result.returncode == 0, output(help_result)
    assert "usage: lk-spark" in help_result.stdout, output(help_result)

    import spark

    assert spark.__appname__ == "laniakea-spark"
    assert spark.__version__ == "0.1.1"

    from spark.config import LocalConfig

    config = LocalConfig()
    config._make_client_uuid("ohpcd-builder")
    assert config.client_uuid == EXPECTED_UUID

    with tempfile.TemporaryDirectory(prefix="lkspark-test-") as tmpdir:
        bad_toml = os.path.join(tmpdir, "bad.toml")
        with open(bad_toml, "w", encoding="utf-8") as handle:
            handle.write("MachineName = [\n")
        try:
            LocalConfig().load(bad_toml)
        except SystemExit as exc:
            assert exc.code == 6
        else:
            raise AssertionError("malformed TOML did not raise SystemExit(6)")

        payload = os.path.join(tmpdir, "payload.txt")
        with open(payload, "wb") as handle:
            handle.write(b"abc")

        from spark.utils.deb822 import Changes

        changes = Changes()
        changes.add_file(payload)
        assert changes["Files"][0]["size"] == 3
        assert changes["Checksums-Sha256"][0]["sha256"] == EXPECTED_SHA256

    connection_py = os.path.join(python_root, "spark", "connection.py")
    with open(connection_py, encoding="utf-8") as handle:
        connection_tree = ast.parse(handle.read(), filename=connection_py)
    job_status = next(
        (
            node
            for node in connection_tree.body
            if isinstance(node, ast.ClassDef) and node.name == "JobStatus"
        ),
        None,
    )
    assert job_status is not None
    assert any(
        isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "SUCCESS"
            for target in node.targets
        )
        and isinstance(node.value, ast.Constant)
        and node.value.value == "success"
        for node in job_status.body
    )

    from spark.utils.firehose import create_firehose

    report = create_firehose("source", "sample", "1.0-1", "amd64", lambda: ("probe", "1"))
    assert type(report).__name__ == "Analysis"
    assert len(report.results) == 0

    try:
        create_firehose("invalid", "sample", "1.0-1", "amd64", lambda: ("probe", "1"))
    except KeyError:
        pass
    else:
        raise AssertionError("invalid firehose report type did not raise KeyError")

    print(
        "PASS: laniakea-spark command wrapper, imports, config, deb822, and firehose"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
