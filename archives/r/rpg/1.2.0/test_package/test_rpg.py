import os
import shutil
import subprocess
import sys
import tempfile


EXPECTED_DIGEST = "\n".join(
    (
        ">Input_0_Arg-C_2_2_289.29138_6.73",
        "DR",
        ">Input_1_Arg-C_10_8_1025.21818_7.88",
        "VYIHPFHL",
    )
)


def run(tool, *args, home):
    env = os.environ.copy()
    env["HOME"] = home
    return subprocess.run(
        [tool, *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def output(result):
    return (
        f"exit={result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def main():
    tool = shutil.which("rpg")
    assert tool, "the packaged rpg command is not on PATH"

    with tempfile.TemporaryDirectory(prefix="rpg-test-") as home:
        version = run(tool, "--version", home=home)
        assert version.returncode == 0, output(version)
        assert version.stdout.strip() == "rpg 1.2.0 from 2021-02-03", output(
            version
        )

        digest = run(
            tool,
            "-s",
            "DRVYIHPFHL",
            "-e",
            "1",
            "-f",
            "fasta",
            home=home,
        )
        assert digest.returncode == 0, output(digest)
        assert digest.stdout.strip() == EXPECTED_DIGEST, output(digest)

        invalid = run(
            tool,
            "-s",
            "DRVYIHPFHL",
            "-e",
            "999",
            home=home,
        )
        assert invalid.returncode != 0, output(invalid)
        assert "does not correspond to any enzyme" in invalid.stderr, output(
            invalid
        )

    print("PASS: rpg version, deterministic digestion, and invalid input")
    return 0


if __name__ == "__main__":
    sys.exit(main())
