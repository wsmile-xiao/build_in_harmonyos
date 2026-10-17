# pyfavicon 0.1.1 OpenHarmony preparation

- Issue: #1747
- Worktree: `D:\harmonyos\worktrees\pyfavicon`
- Branch: `feat/pyfavicon-0.1.1-C0DX`
- Upstream: `https://github.com/bilelmoussaoui/pyfavicon`
- Source: `https://files.pythonhosted.org/packages/df/62/5e6731cd9477096152180d826aedfa63f470b3b29c1b3b489f3d914725aa/pyfavicon-0.1.1.tar.gz`
- SHA256: `fdd5a222f08488824877d8a00a272657c4e66bbe115520d1d68e6d9892ba8e97`

## W0 Dependency Check

Upstream `setup.py` lists runtime dependencies: `aiohttp`, `beautifulsoup4`, and `Pillow`. The module also imports `yarl` through the aiohttp stack. No matching adaptation directories were found under `archives/a`, `archives/b`, or `archives/p` in this worktree, and the local Windows PATH has no `conan` executable to query the remote recipe repository.

To avoid mixing dependency adaptations into the pyfavicon issue, this preparation uses a portability patch that removes those Python runtime dependencies and keeps the public async API using Python standard library modules.

## Source And Build Analysis

- Build system: `setuptools` (`setup.py`)
- Package type: pure Python library
- Upstream tests in sdist: none found
- CLI commands: none; no `commands.json` is needed
- Native compilation: none

## Patch Summary

`0001-use-python-stdlib-runtime.patch`:

- replaces `aiohttp` with `urllib.request` running in the event loop executor;
- replaces `beautifulsoup4` with `html.parser.HTMLParser`;
- replaces `Pillow` image sniffing with lightweight PNG/GIF/ICO/JPEG header parsing;
- replaces `yarl.URL` usage with `urllib.parse.urljoin/urlparse`;
- updates `__version__` from the upstream mismatch `0.0.1` to `0.1.1`;
- clears `install_requires` in `setup.py` after removing the third-party imports.

## Tests

The added `test_package` performs 14 consumer assertions covering import/version, data URI decoding, HTML parsing, meta icon discovery, relative URL resolution, duplicate filtering, largest-icon selection, file input, and saving a data icon to a temporary directory.

## Verification

Local checks:

- Official PyPI sdist downloaded and SHA256 verified.
- Patch dry-run with `git apply --check` passed.
- Python syntax checks for recipe and test files passed.
- Patched source plus consumer test passed locally with `14/14` assertions.

OHOS device check (`192.168.137.77:2222`):

```sh
CI_PACKAGES="archives/p/pyfavicon/0.1.1" zsh ci/conan/build_and_test.sh
```

Result:

- L0: pass
- L1: pass (`test_package` executed; `14/14` assertions)
- L2: skip (no `bin/` directory; package is a Python library)
- L4: pass
- L5: pass (`lib/` artifact exists)
- Build summary: Total 1, Success 1, Failed 0
- Full reference: `pyfavicon/0.1.1#c8166cc06206c5dc9bf220bf63030948:876049f3ae10a4560da345bb02378e03e212bc8c#ee718db0932aa495a3106ce7976a2057`

## Current Limits

- Local Windows `conan create` was not run because `conan` is not installed on the Windows host PATH.
- Shadow CI was intentionally not run for this round.
