# Legacy Python CLIs need an installed-entry-point test on HarmonyOS Python 3.12+

> Draft: `DRAFT-J2CLI-CPYTHON312-CLI-CONTRACT` (Path B knowledge expansion)
> Evidence source: task #12602, upstream j2cli tag `v0.3.12b`, local HarmonyOS PC Conan create on 2026-09-27.

## 问题

A pure-Python CLI may pass tests that import its source module and still fail on a current Python runtime or when a user invokes the advertised command. j2cli 0.3.12b declares the console entry point `j2 = j2cli:main`, requires Jinja2, and offers YAML through the optional `yaml` extra (PyYAML). Its legacy source uses `imp.load_source`, `ConfigParser.readfp`, and `pkg_resources.get_distribution`; Python 3.12 removed `imp`, and the HarmonyOS PC image used for this build runs Python 3.14.7. Its upstream test suite also uses `nose.collector`, while the device Python environment has no `nose` or setuptools.

A recipe that only imports `j2cli.cli` or counts a successful package step does not prove that the installed `j2` command, declared runtime dependencies, exit statuses, and optional YAML mode work for users.

## 根因

- `imp` was removed in CPython 3.12. Legacy dynamic filter loading through `imp.load_source` therefore fails before rendering on newer interpreters.
- `ConfigParser.readfp` is removed from current Python. A code path can fail later even after replacing `imp`.
- `pkg_resources` is supplied by setuptools, which is not a declared runtime dependency in this Conan environment. Importing it to discover a hard-coded package version adds an avoidable dependency.
- Upstream's test-suite declaration asks Nose to collect tests, but the suite itself is `unittest.TestCase` based. The HarmonyOS image lacks Nose; running `nose` is therefore unavailable even though the tests can run directly through `unittest`.
- Testing the module alone skips the `console_scripts` contract (`j2cli:main`), launcher permissions, Python module lookup, and dependency visibility. Conan's registered Jinja2/PyYAML recipes also do not export their Python `site-packages` through run-environment paths; the package must make declared pure-Python runtime modules visible to its launcher.

## 最小解决与边界

For this upstream version the recipe applies a narrow compatibility patch:

1. Replace each `imp.load_source` use with `importlib.util.spec_from_file_location`, `module_from_spec`, and `exec_module`.
2. Use `ConfigParser.read_file` and the upstream version string instead of importing `pkg_resources` solely for metadata.
3. Preserve the wrapped command's exit code so `j2 --version` exits successfully.
4. Run the 14 upstream `unittest` methods directly from `tests/render-test.py`; the device does not need Nose or setuptools.
5. Install `bin/j2` targeting `j2cli:main`, declare `jinja2/3.1.6` as required, and keep `pyyaml/6.0.2` behind `with_yaml=True`. The recipe packages the pure-Python runtime modules from these Conan dependencies because their recipes do not publish Python paths to Conan's run environment.
6. Exercise the installed command in `test_package` for version output, JSON rendering, output-file behavior, and the enabled YAML extra.

The upstream output-file test hard-codes `/tmp/j2-out`, which is read-only on the device. Its fixture was changed to use the suite's temporary-file helper while retaining the output-content assertion. This is a test portability adjustment, not a runtime change.

Do not solve this by adding setuptools/nose as unexplained runtime dependencies, by retaining `imp`, or by asserting only that a source module imports. If a future upstream version changes the entry point or gains a supported Python-version range, re-check the patch rather than applying it blindly. Bundling Python modules is specific to the current Conan dependency recipes' missing `PYTHONPATH` export; if those recipes later export a stable run environment, prefer that mechanism and avoid duplicate bundled modules.

## 验证

| Check | Result |
|---|---:|
| Upstream test cases in `tests/render-test.py` (14 methods) | 14/14 passed |
| Installed consumer assertions (`test_package/test_j2cli.py`) | 11/11 passed |
| `j2 --version` through packaged `bin/j2` | exit 0; reports `j2cli 0.3.12b` and Jinja2 |
| JSON render to stdout and `-o` file | passed; output exactly matches expected text |
| YAML render with default `with_yaml=True` | passed |
| Full device `conan create` for `j2cli/0.3.12b` | exit 0 |
| Optional YAML disabled | not exercised in this build |

The test package writes temporary fixtures beneath its writable build directory because `/tmp` is read-only. Upstream tests are loaded with a small `unittest` runner; no suite cases were skipped.

## 七轴查重表

| 轴 | 本草稿的边界 | 与已有条目的差异/反证 |
|---|---|---|
| 触发信号 | Python 3.12+ `imp` import/runtime failure; broken installed Python CLI | E319 is a generic Python packaging/noarch and runtime resource-loading record, not removed standard-library API migration. |
| 根因层 | CPython API removal and undeclared Python package metadata import | E424 concerns software-level `commands.json` registration; it does not diagnose Python runtime imports. |
| 阶段 | module import, CLI startup, and test/consumer execution | E428 concerns nested test subprocess PATH on HarmonyOS; this case is Python module resolution and entry-point behavior. |
| 适用对象 | Older pure-Python CLIs with plugin loaders, old config APIs, or implicit setuptools imports | Not a general Conan recipe layout rule; only applies when source/API inspection confirms these runtime patterns. |
| 修复机制 | `importlib.util`, supported config API, declared dependency contract, installed command test | No overlap with E319's generic wheel/site-packages advice beyond the package-path boundary called out above. |
| 验证方式 | Full upstream unittest count plus real packaged `j2` process and render output | A source import or self-authored assertion alone is insufficient; both upstream suite and executable consumer were run. |
| 反例/边界 | Python versions that still provide required APIs, or upstream code already migrated, do not need this patch | This is evidence from one upstream CLI and does not establish independent-library generality; validate another affected project before broad promotion. |

Searches at main tip found related E319 (resource-loading/noarch packaging), E424 (`commands.json` registration), and E428 (nested subprocess PATH), but no matching recipe/registry version and no entry for the CPython `imp` removal plus installed CLI contract. This draft records the distinct trigger and verification boundary; it does not claim those existing entries are irrelevant to all packaging behavior.

## 适用边界

Applies to pure-Python command-line packages running on CPython 3.12 or later when upstream imports removed APIs such as `imp`, uses removed configuration methods, or relies on `pkg_resources` without declaring setuptools. Verify source usage and the real entry point before patching. The j2cli evidence is specific to upstream tag `v0.3.12b`, HarmonyOS PC Python 3.14.7, the current Conan Jinja2/PyYAML recipes, and `with_yaml=True`. It does not prove compatibility for arbitrary Python versions, package recipes, plugins, or the YAML-disabled option; independent validation on another affected upstream project remains needed before general promotion.
