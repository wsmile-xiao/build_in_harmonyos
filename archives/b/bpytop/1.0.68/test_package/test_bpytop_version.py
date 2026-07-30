#!/usr/bin/env python3
"""Verify the packaged bpytop wrapper and psutil dependency."""
import os
import glob
import shutil
import subprocess
import sys
import tempfile
import textwrap


def prepend_pythonpath(env, path):
    updated = env.copy()
    updated["PYTHONPATH"] = (
        path if not updated.get("PYTHONPATH")
        else path + os.pathsep + updated["PYTHONPATH"]
    )
    return updated


def is_ohos_runtime():
    return (
        sys.platform.startswith("ohos")
        or os.environ.get("HNP_PUBLIC_HOME") == "/data/service/hnp"
    )


def verify_ohos_signatures(extensions):
    if not is_ohos_runtime():
        return

    objdump = "/data/service/hnp/bin/llvm-objdump"
    if not os.path.isfile(objdump):
        raise AssertionError(f"Missing OHOS ELF inspection tool: {objdump}")

    for extension in extensions:
        result = subprocess.run(
            [objdump, "-h", extension],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"Unable to inspect packaged extension {extension}:\n"
                f"{result.stdout}"
            )
        if ".codesign" not in result.stdout:
            raise AssertionError(
                f"Packaged OHOS extension is not signed: {extension}"
            )


def psutil_import_probe(python_exe, runtime_site, env):
    probe_env = prepend_pythonpath(env, runtime_site)
    probe = textwrap.dedent(
        """
        import psutil
        import psutil._psutil_linux
        import psutil._psutil_posix
        print("psutil native extensions importable")
        """
    )
    return subprocess.run(
        [python_exe, "-c", probe],
        check=False,
        env=probe_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def run_version_check(bpytop, env, context):
    result = subprocess.run(
        [bpytop, "--version"],
        check=False,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"bpytop --version failed during {context} "
            f"with exit code {result.returncode}:\n{result.stdout}"
        )
    if "bpytop version: 1.0.68" not in result.stdout:
        raise AssertionError(
            f"Unexpected bpytop version output during {context}: {result.stdout}"
        )


def stage_psutil_for_runtime(site_packages, python_exe, env):
    psutil_dir = os.path.join(site_packages, "psutil")
    extensions = sorted(glob.glob(os.path.join(psutil_dir, "*.so")))
    if not extensions:
        raise AssertionError(f"Missing packaged psutil native extensions in {psutil_dir}")
    for extension in extensions:
        with open(extension, "rb") as handle:
            if handle.read(4) != b"\x7fELF":
                raise AssertionError(f"Packaged extension is not an ELF object: {extension}")
        mode = os.stat(extension).st_mode
        if mode & 0o111 == 0:
            raise AssertionError(f"Packaged extension is not executable: {extension}")
    verify_ohos_signatures(extensions)

    direct_result = psutil_import_probe(python_exe, site_packages, env)
    if direct_result.returncode == 0:
        return site_packages
    if is_ohos_runtime() and "Permission denied" in direct_result.stdout:
        print(
            "OHOS hmmac blocks dlopen from the Conan user path; "
            "packaged psutil extensions passed ELF and code-signature checks. "
            "Runtime import requires installation through HNP."
        )
        return None

    errors = [
        f"{site_packages}: {direct_result.stdout.strip() or 'no output'}",
    ]

    candidates = [
        os.getcwd(),
        os.path.dirname(__file__),
        os.environ.get("BPYTOP_RUNTIME_DIR"),
        os.environ.get("DOWNLOAD_CACHE"),
        os.environ.get("TMPDIR"),
    ]
    if os.path.isdir("/data/local/tmp"):
        candidates.append("/data/local/tmp")

    seen = set()
    for runtime_parent in candidates:
        if not runtime_parent or runtime_parent in seen:
            continue
        seen.add(runtime_parent)
        runtime_site = os.path.join(
            runtime_parent,
            f"bpytop-psutil-test-{os.getpid()}",
        )
        try:
            os.makedirs(runtime_parent, exist_ok=True)
            shutil.rmtree(runtime_site, ignore_errors=True)
            shutil.copytree(psutil_dir, os.path.join(runtime_site, "psutil"))
            for root, dirs, files in os.walk(runtime_site):
                for directory in dirs:
                    os.chmod(os.path.join(root, directory), 0o755)
                for filename in files:
                    path = os.path.join(root, filename)
                    os.chmod(path, 0o755 if filename.endswith(".so") else 0o644)
            copy_result = psutil_import_probe(
                python_exe,
                runtime_site,
                env,
            )
            if copy_result.returncode == 0:
                return runtime_site
            errors.append(
                f"{runtime_site}: {copy_result.stdout.strip() or 'no output'}"
            )
            shutil.rmtree(runtime_site, ignore_errors=True)
        except (OSError, shutil.Error) as exc:
            errors.append(f"{runtime_site}: {exc}")
            shutil.rmtree(runtime_site, ignore_errors=True)

    raise AssertionError(
        "No runtime-loadable psutil extension location found:\n"
        + "\n".join(errors)
    )


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: test_bpytop_version.py <bpytop> <python>")

    bpytop, python_exe = sys.argv[1:]
    env = os.environ.copy()
    env["BPYTOP_PYTHON"] = python_exe
    prefix = os.path.dirname(os.path.dirname(bpytop))
    py_version = subprocess.check_output(
        [
            python_exe,
            "-c",
            "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')",
        ],
        text=True,
    ).strip()
    site_packages = os.path.join(prefix, "lib", f"python{py_version}", "site-packages")
    env["PYTHONPATH"] = (
        site_packages if not env.get("PYTHONPATH")
        else site_packages + os.pathsep + env["PYTHONPATH"]
    )
    runtime_site = stage_psutil_for_runtime(site_packages, python_exe, env)

    run_version_check(bpytop, env, "normal startup")

    with tempfile.TemporaryDirectory() as fault_dir:
        sitecustomize = textwrap.dedent(
            """
            import builtins

            original_import = builtins.__import__

            def reject_termios(name, *args, **kwargs):
                if name == "termios":
                    raise ImportError("fault-injected missing terminal module")
                return original_import(name, *args, **kwargs)

            builtins.__import__ = reject_termios
            """
        )
        with open(
            os.path.join(fault_dir, "sitecustomize.py"),
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(sitecustomize)
        fault_env = env.copy()
        fault_env = prepend_pythonpath(fault_env, fault_dir)
        run_version_check(
            bpytop,
            fault_env,
            "fault-injected missing termios module",
        )

    if runtime_site is not None:
        probe = textwrap.dedent(
            """
            import os
            import psutil
            import psutil._psutil_linux as linux_extension
            import psutil._psutil_posix as posix_extension

            assert psutil.__version__ == "5.9.8", psutil.__version__
            assert linux_extension.__file__.endswith(".so"), linux_extension.__file__
            assert posix_extension.__file__.endswith(".so"), posix_extension.__file__
            assert psutil.cpu_count() > 0

            cpu = psutil.cpu_percent(interval=0.1)
            assert isinstance(cpu, (int, float)) and 0.0 <= cpu <= 100.0, cpu

            memory = psutil.virtual_memory()
            assert memory.total > 0 and memory.available >= 0, memory

            disk = psutil.disk_usage("/")
            assert disk.total > 0, disk

            pids = psutil.pids()
            assert isinstance(pids, list) and os.getpid() in pids, pids

            process = psutil.Process(os.getpid())
            assert process.name(), process

            print("real psutil extension and system probes are valid")
            """
        )
        probe_env = (
            env if runtime_site == site_packages
            else prepend_pythonpath(env, runtime_site)
        )
        subprocess.run([python_exe, "-c", probe], check=True, env=probe_env)


if __name__ == "__main__":
    main()
