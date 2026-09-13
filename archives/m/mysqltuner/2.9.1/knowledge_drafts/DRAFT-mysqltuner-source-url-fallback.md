# DRAFT-mysqltuner-source-url-fallback - GitHub tag archives need checked mirror fallback on OHOS shadow CI

- Trigger event: mysqltuner 2.9.1 source() on OHOS shadow CI
- Path: Path B knowledge extension
- Phase: Conan source()

## Symptom

The recipe originally used only the official GitHub tag archive:

```text
https://github.com/major/MySQLTuner-perl/archive/refs/tags/v2.9.1.tar.gz
```

On the OHOS device, `source()` timed out while connecting to GitHub. The same
source identity had already been verified locally by SHA256.

## Root Cause

The device network path to GitHub was unstable, while the recipe's source()
used a single URL. This made an otherwise pure Perl package fail before any
actual build or test logic was reached.

## Fix

Use a Conan URL list and keep the official tarball SHA256 as the source-of-truth
guard:

```python
_source_urls = [
    "https://ghfast.top/https://github.com/major/MySQLTuner-perl/archive/refs/tags/v2.9.1.tar.gz",
    "https://gh-proxy.com/https://github.com/major/MySQLTuner-perl/archive/refs/tags/v2.9.1.tar.gz",
    "https://mirror.ghproxy.com/https://github.com/major/MySQLTuner-perl/archive/refs/tags/v2.9.1.tar.gz",
    "https://github.com/major/MySQLTuner-perl/archive/refs/tags/v2.9.1.tar.gz",
]
get(self, url=self._source_urls, sha256=self._source_sha256, strip_root=True)
```

Do not accept mirror content without the original SHA256. The mirrors are only
transport fallbacks.

## Verification

After adding fallback URLs, OHOS shadow CI downloaded from `ghfast.top`, passed
the SHA256 check, unpacked the source, and proceeded into build and TAP tests.

## Reuse

For GitHub-only pure script packages, a source network failure can look like an
adaptation failure. Add mirror fallback early, but keep the official GitHub URL
as a final entry and retain the official content hash.
