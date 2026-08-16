HELP_ARGS = (
    "--help",
    "validate --help",
)

BASE_BINARIES = (
    "alpm-repo-desc",
    "alpm-repo-files",
)


def binary_names(os_name):
    suffix = ".exe" if os_name == "Windows" else ""
    return [name + suffix for name in BASE_BINARIES]


def expected_executable_magic(os_name):
    return b"MZ" if os_name == "Windows" else b"\x7fELF"


def assert_executable_magic(path, os_name):
    with open(path, "rb") as f:
        magic = f.read(4)

    expected = expected_executable_magic(os_name)
    if not magic.startswith(expected):
        raise RuntimeError(f"Unexpected executable magic for {path!r}")
