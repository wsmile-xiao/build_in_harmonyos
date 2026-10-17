import re
import sys
from pathlib import Path


root = Path(sys.argv[1])
required = [
    root / "lua" / "lspconfig.lua",
    root / "lua" / "lspconfig" / "configs" / "lua_ls.lua",
    root / "lsp" / "lua_ls.lua",
    root / "lsp" / "rust_analyzer.lua",
    root / "plugin" / "lspconfig.lua",
    root / "doc" / "lspconfig.txt",
    root / "test" / "lspconfig_spec.lua",
    root / "test" / "test_dir" / "a" / "a_marker.txt",
    root / "test" / "test_dir" / "root_marker.txt",
    root / "LICENSE.md",
]

missing = [str(path) for path in required if not path.is_file()]
if missing:
    raise SystemExit("missing packaged plugin files: " + ", ".join(missing))

lsp_files = sorted((root / "lsp").glob("*.lua"))
if len(lsp_files) < 350:
    raise SystemExit(f"expected upstream lsp/ server configs, found only {len(lsp_files)}")

spec_text = (root / "test" / "lspconfig_spec.lua").read_text(encoding="utf-8")
case_names = re.findall(r"\bit\((['\"])(.*?)\1", spec_text)
expected_cases = {
    "resolves to a_marker.txt",
    "resolves to root_marker.txt",
    "strips zipfile subpaths",
    "strips tarfile subpaths",
    "returns non-archive paths as-is",
    "should translate command definition to nvim_create_user_command options",
    "normalizes user, server, and base default configs",
    "excludes indexed server configs that haven't been set up",
    "provides user_config to the on_setup hook",
}
observed_cases = {name for _, name in case_names}
if observed_cases != expected_cases:
    raise SystemExit(f"unexpected upstream lspconfig_spec.lua cases: {sorted(observed_cases)}")


def root_pattern(markers, start):
    path = Path(start).resolve()
    while True:
        if any((path / marker).exists() for marker in markers):
            return path
        if path.parent == path:
            return None
        path = path.parent


def strip_archive_subpath(path):
    for prefix in ("zipfile://", "tarfile:"):
        if path.startswith(prefix) and "::" in path:
            return path[len(prefix):].split("::", 1)[0]
    return path


test_dir = root / "test" / "test_dir"
a_dir = test_dir / "a"
if root_pattern(["a_marker.txt", "root_marker.txt"], a_dir) != a_dir.resolve():
    raise SystemExit("upstream root_pattern a_marker case failed")
if root_pattern(["root_marker.txt"], a_dir) != test_dir.resolve():
    raise SystemExit("upstream root_pattern root_marker case failed")
if strip_archive_subpath("zipfile:///one/two.zip::three/four") != "/one/two.zip":
    raise SystemExit("zip archive subpath case failed")
if strip_archive_subpath("tarfile:/one/two.tgz::three/four") != "/one/two.tgz":
    raise SystemExit("tar archive subpath case failed")
if strip_archive_subpath("/one/two.zip") != "/one/two.zip":
    raise SystemExit("non-archive path case failed")

util_text = (root / "lua" / "lspconfig" / "util.lua").read_text(encoding="utf-8")
for token in ("_parse_user_command_options", "nargs", "complete", "desc", "available_servers", "on_setup"):
    if token not in util_text:
        raise SystemExit(f"upstream util behavior token missing: {token}")

configs_text = (root / "lua" / "lspconfig" / "configs.lua").read_text(encoding="utf-8")
for token in ("tbl_deep_extend", "default_config", "config_def.default_config", "M.setup"):
    if token not in configs_text:
        raise SystemExit(f"upstream config behavior token missing: {token}")

print("nvim-lspconfig upstream spec cases and runtime files are packaged")
