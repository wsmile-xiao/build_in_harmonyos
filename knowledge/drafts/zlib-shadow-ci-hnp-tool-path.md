# zlib shadow CI HNP tool PATH

## Error signature

The zlib recipe configures successfully with `/data/service/hnp/bin/clang`, then fails at the first make step:

```text
zlib/1.3.1.1.1: RUN: make -j1
/system/bin/sh: make: inaccessible or not found
```

## Root cause

The Conan profile can provide absolute compiler paths, so `./configure` works even when the runner PATH is incomplete. Recipe calls such as `self.run("make -j1")` still need `make` to be discoverable through PATH.

## Recommended runner command

When running zlib single-package shadow CI, prepend the HNP tool directory:

```sh
EXTRA_PATH=/data/service/hnp/bin:/data/service/hnp/cmake.org/cmake_4.1.2/bin:$HOME/usr/local/bin:$HOME/.local/bin:$HOME/ohpc-ci-shadow/python-user/bin

sh "$HOME/bin/ohos-test-runner.sh" \
  --user codex \
  --lib zlib \
  --task zlib-1.3.1.1.1-r3-pathfix \
  --mode smoke \
  --try-lock \
  --path "$EXTRA_PATH" \
  --workdir "$CI_REPO_ROOT" \
  -- zsh ci/conan/build_and_test.sh archives/z/zlib/1.3.1.1.1
```

## Validation evidence

The first zlib run failed with `make: inaccessible or not found`. After adding `/data/service/hnp/bin` to runner PATH, the r3 run passed:

```text
Build Summary
  Total:   1
  Success: 1
  Failed:  0
```

The r3 run directory was:

```text
codex-zlib-zlib-1.3.1.1.1-r3-pathfix-20260825-20260825-193939-59953
```

## Notes

During the CMake test_package build, GNU make may print:

```text
make: jobserver mkfifo: ... Operation not permitted
```

For this zlib run it was a warning and the build completed. If a future package turns this into a hard failure, retry with lower parallelism before changing package source code.
