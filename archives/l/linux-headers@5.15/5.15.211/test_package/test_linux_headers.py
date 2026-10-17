#!/usr/bin/env python3
"""Smoke tests for installed Linux 5.15 UAPI headers."""
import importlib.util
import os
import sys
import tempfile


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def load_recipe(recipe_folder):
    recipe_path = os.path.join(recipe_folder, "conanfile.py")
    spec = importlib.util.spec_from_file_location("linux_headers_recipe", recipe_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load recipe: {recipe_path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise AssertionError(
            f"Unable to execute recipe {recipe_path}: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    try:
        return module.LinuxHeadersConan
    except AttributeError as exc:
        raise AssertionError(
            f"Recipe {recipe_path} does not define LinuxHeadersConan"
        ) from exc


def verify_recipe_load_failures(recipe_folder):
    missing_folder = os.path.join(recipe_folder, "missing-recipe")
    missing_path = os.path.join(missing_folder, "conanfile.py")
    try:
        load_recipe(missing_folder)
    except AssertionError as exc:
        message = str(exc)
        if "FileNotFoundError" not in message or missing_path not in message:
            raise AssertionError(
                f"Recipe load failure lacks useful context: {message}"
            ) from exc
    else:
        raise AssertionError("Missing recipe must fail with AssertionError")

    with tempfile.TemporaryDirectory(prefix="linux-headers-bad-recipe-") as temp_dir:
        wrong_class_path = os.path.join(temp_dir, "conanfile.py")
        with open(wrong_class_path, "w", encoding="utf-8") as handle:
            handle.write("class NotLinuxHeadersConan:\n    pass\n")
        try:
            load_recipe(temp_dir)
        except AssertionError as exc:
            message = str(exc)
            if (
                "does not define LinuxHeadersConan" not in message
                or wrong_class_path not in message
            ):
                raise AssertionError(
                    f"Missing recipe class lacks useful context: {message}"
                ) from exc
        else:
            raise AssertionError("Missing recipe class must fail with AssertionError")


def verify_download_settings(recipe):
    names = (
        "OHPCD_SOURCE_MAX_SECONDS",
        "OHPCD_SOURCE_MIN_BYTES_PER_SECOND",
        "OHPCD_SOURCE_MIN_RATE_GRACE",
        "OHPCD_SOURCE_READ_TIMEOUT",
    )
    original = {name: os.environ.get(name) for name in names}
    try:
        for name in names:
            os.environ.pop(name, None)
        if recipe._download_settings() != (1500, 65536, 120, 30):
            raise AssertionError("Download settings must use documented defaults")

        valid = ("1800", "131072", "0", "45")
        for name, value in zip(names, valid):
            os.environ[name] = value
        if recipe._download_settings() != (1800, 131072, 0, 45):
            raise AssertionError("Download settings must accept valid overrides")

        invalid = {
            "OHPCD_SOURCE_MAX_SECONDS": "abc",
            "OHPCD_SOURCE_MIN_BYTES_PER_SECOND": "",
            "OHPCD_SOURCE_MIN_RATE_GRACE": "-1",
            "OHPCD_SOURCE_READ_TIMEOUT": "0",
        }
        for invalid_name, invalid_value in invalid.items():
            for name, value in zip(names, valid):
                os.environ[name] = value
            os.environ[invalid_name] = invalid_value
            try:
                recipe._download_settings()
            except Exception as exc:
                message = str(exc)
                if (
                    type(exc).__name__ != "ConanException"
                    or invalid_name not in message
                    or repr(invalid_value) not in message
                ):
                    raise AssertionError(
                        f"Invalid setting lacks useful context: {message}"
                    ) from exc
            else:
                raise AssertionError(
                    f"{invalid_name}={invalid_value!r} must be rejected"
                )
    finally:
        for name, value in original.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: test_linux_headers.py <package-folder> <recipe-folder>",
            file=sys.stderr,
        )
        return 2

    package_folder, recipe_folder = sys.argv[1:]
    include = os.path.join(package_folder, "include")
    required_headers = [
        os.path.join(include, "linux", "version.h"),
        os.path.join(include, "linux", "types.h"),
        os.path.join(include, "linux", "errno.h"),
        os.path.join(include, "asm", "unistd.h"),
        os.path.join(include, "asm-generic", "unistd.h"),
    ]
    for header in required_headers:
        if not os.path.isfile(header):
            raise AssertionError(f"Missing installed header: {header}")

    version_h = read_text(os.path.join(include, "linux", "version.h"))
    if "#define LINUX_VERSION_CODE" not in version_h:
        raise AssertionError("linux/version.h is missing LINUX_VERSION_CODE")
    if "#define KERNEL_VERSION" not in version_h:
        raise AssertionError("linux/version.h is missing KERNEL_VERSION")

    unistd_h = read_text(os.path.join(include, "asm-generic", "unistd.h"))
    if "__NR_read" not in unistd_h:
        raise AssertionError("asm-generic/unistd.h is missing syscall definitions")

    recipe = load_recipe(recipe_folder)
    if recipe._kernel_arch("armv8") != "arm64":
        raise AssertionError("armv8 must map to the kernel arm64 architecture")
    if recipe._kernel_arch("armv8.5") != "arm64":
        raise AssertionError("armv8.5 must map to the kernel arm64 architecture")
    if recipe._kernel_arch("armv8.7") != "arm64":
        raise AssertionError("armv8.7 must map to the kernel arm64 architecture")
    if recipe._kernel_arch("x86_64") != "x86":
        raise AssertionError("x86_64 must map to the kernel x86 architecture")
    if recipe._kernel_arch("riscv64") != "riscv64":
        raise AssertionError("unknown architectures must not be forced to arm64")
    expected = 'PATH="/tmp/rsync/bin:$PATH" make headers_install'
    if recipe._path_prefix_command("/tmp/rsync/bin", "make headers_install") != expected:
        raise AssertionError("rsync bin directory must be prepended for headers_install")
    verify_recipe_load_failures(recipe_folder)
    verify_download_settings(recipe)

    print(
        "PASS: linux-headers layout, UAPI contents, architecture mapping, "
        "rsync tool PATH setup, recipe-load diagnostics, and download settings are valid"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
