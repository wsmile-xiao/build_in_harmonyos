import os
import subprocess
import sys
import tempfile


def main():
    package, rakudo, platform = sys.argv[1:4]
    raku = os.path.join(rakudo, "bin", "raku")
    env = os.environ.copy()
    env["RAKULIB"] = os.path.join(package, "lib")
    env["LD_LIBRARY_PATH"] = os.pathsep.join(
        filter(None, [os.path.join(rakudo, "lib"), env.get("LD_LIBRARY_PATH", "")])
    )
    env["MVM_JIT_DISABLE"] = "1"
    env["RAKUDO_NO_PRECOMPILATION"] = "1"

    with tempfile.TemporaryDirectory(
        prefix="raku-log-test-", dir=os.path.expanduser("~")
    ) as temp_dir:
        env["TMPDIR"] = temp_dir
        tests = ["test_module.raku"]
        if platform == "OHOS":
            tests.append("test_ohos.raku")
        for name in tests:
            subprocess.run(
                [raku, os.path.join(os.path.dirname(__file__), name)],
                check=True,
                env=env,
            )


if __name__ == "__main__":
    main()
