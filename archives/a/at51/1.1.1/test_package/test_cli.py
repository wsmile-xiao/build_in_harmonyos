HELP_COMMANDS = (
    "--help",
    "stat --help",
    "base --help",
    "kinit --help",
    "libfind --help",
)


def expected_executable_magic(os_name):
    return b"MZ" if os_name == "Windows" else b"\x7fELF"


def assert_executable_magic(path, os_name):
    with open(path, "rb") as f:
        magic = f.read(4)

    expected = expected_executable_magic(os_name)
    if not magic.startswith(expected):
        raise RuntimeError(f"Unexpected executable magic for {path!r}")
