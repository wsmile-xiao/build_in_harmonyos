# HarmonyOS PC device validation

## 1. Capture device identity

```sh
uname -a
getconf LONG_BIT
python3 --version
clang --version
conan --version
```

Save the unedited output as `device-environment.log`.

## 2. Build with the repository profile

From the checked-out `feat/pygame-2.6.1` branch:

```sh
export REPO_DIR="$PWD"
export RECIPE="$REPO_DIR/archives/p/pygame/2.6.1"
export PROFILE="$REPO_DIR/ci/conan/profiles/ohos-aarch64"
export TMPDIR="$HOME/tmp/pygame-2.6.1"
mkdir -p "$TMPDIR"
conan create "$RECIPE" -pr:h="$PROFILE" -pr:b="$PROFILE" \
  --build=missing --user=ohpcd --channel=stable \
  2>&1 | tee "$HOME/pygame-2.6.1-conan-create.log"
test "${PIPESTATUS[0]}" -eq 0
```

The recipe derives private shared `libpygame_sdl2.so` and
`libpygame_sdl2_mixer.so` runtimes from the published PIC-static packages
before building pygame. The log must contain both private-runtime PASS markers,
the full upstream result marker, and the consumer summary `assertions=34/34`.

## 3. Export the minimal validation bundle

Locate the generated wheel after `conan create`:

```sh
VERIFY_DIR="$HOME/pygame-2.6.1-device"
rm -rf "$VERIFY_DIR"
mkdir -p "$VERIFY_DIR"
WHEEL="$(find "${CONAN_HOME:-$HOME/.conan2}/p/b" -path \
  '*/p/res/wheels/pygame-2.6.1-cp312-cp312-ohos_aarch64.whl' \
  -type f -print -quit)"
test -n "$WHEEL"
cp "$WHEEL" "$VERIFY_DIR/"
cp "$RECIPE/test_package/test_pygame.py" "$VERIFY_DIR/"
find "$VERIFY_DIR" -type f -exec sha256sum {} \; | sort \
  > "$VERIFY_DIR/SHA256SUMS"
```

The minimal bundle contains the signed wheel, the same consumer test used by
Conan, and its SHA256 manifest. It does not contain the source tree or build
cache.

The in-build upstream run uses SDL dummy video/audio. Its test runner probes
system fonts, PortMidi, OGG, and SDL_ttf script-shaping capabilities without
injecting a provider. Unavailable system-font, PortMidi, and pure OGG cases are
explicit skips; mixed OGG/WAV tests retain and execute their WAV branches, and
the script-shaping case validates the unsupported-feature error path.

## 4. Validate the installed wheel with headless SDL drivers

```sh
TEST_ROOT="$HOME/pygame-2.6.1-device"
SITE="$TEST_ROOT/site-packages"
WORK="$TEST_ROOT/work"
rm -rf "$SITE" "$WORK"
mkdir -p "$SITE" "$WORK"
python3 -m pip install --no-index --no-deps --target "$SITE" \
  "$TEST_ROOT/pygame-2.6.1-cp312-cp312-ohos_aarch64.whl"
export PYTHONPATH="$SITE"
export LD_LIBRARY_PATH="$SITE/pygame/.libs${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export SDL_VIDEODRIVER=dummy
export SDL_AUDIODRIVER=dummy
unset SDL_DYNAMIC_API
python3 "$TEST_ROOT/test_pygame.py" --work-dir "$WORK" \
  > "$TEST_ROOT/device-consumer.log" 2>&1
RC=$?
cat "$TEST_ROOT/device-consumer.log"
echo "exit_code=$RC"
test "$RC" -eq 0

set +e
python3 "$TEST_ROOT/test_pygame.py" --work-dir "$WORK/negative" \
  --self-test-failure > "$TEST_ROOT/device-negative-control.log" 2>&1
NEGATIVE_RC=$?
set -e
cat "$TEST_ROOT/device-negative-control.log"
echo "negative_exit_code=$NEGATIVE_RC"
test "$NEGATIVE_RC" -eq 1
```

## 5. Transfer and retrieve with HDC

If the build is prepared on another machine, use a task-private device path:

```sh
hdc -t "$HDC_TARGET" shell "mkdir -p /data/local/tmp/pygame-2.6.1"
hdc -t "$HDC_TARGET" file send pygame-2.6.1-device \
  /data/local/tmp/pygame-2.6.1
hdc -t "$HDC_TARGET" file recv \
  /data/local/tmp/pygame-2.6.1/device-consumer.log .
```

Preserve the raw environment, Conan, consumer, and negative-control logs in the
auxiliary delivery directory after execution.
