# HarmonyOS PC device validation

## Environment collection

```bash
uname -a
uname -m
cat /etc/os-release 2>/dev/null || true
clang --version
conan --version
```

## Minimal verification package

The verified bundle contains only:

| Source | Device path | Purpose | Size | SHA256 |
|---|---|---|---:|---|
| `ruckig_test` | `/data/local/tmp/ruckig-0.19.4/ruckig_test` | C++ API validation executable | 76224 | `5afe4ffa48dc787773ecb67db6fcf45dec9fff65d2b7c2c77a7b2892b39d09f9` |
| `run_test.sh` | `/data/local/tmp/ruckig-0.19.4/run_test.sh` | Shared Conan/device runner | 996 | `67ec7080df3a4ab89934d694147a58e6fe9fc8794b8c81431bad1d0c946b764e` |
| `libruckig.so` | `/data/local/tmp/ruckig-0.19.4/lib/libruckig.so` | Package runtime library | 129344 | `77b5469b21ab499e856d411f3f0a769d1637f5b841d4657d7823ac8be7ded5dc` |

## Transfer and run

```bash
hdc shell mkdir -p /data/local/tmp/ruckig-0.19.4/lib
hdc file send ruckig_test /data/local/tmp/ruckig-0.19.4/ruckig_test
hdc file send run_test.sh /data/local/tmp/ruckig-0.19.4/run_test.sh
hdc file send libruckig.so /data/local/tmp/ruckig-0.19.4/lib/libruckig.so
hdc shell chmod 755 /data/local/tmp/ruckig-0.19.4/ruckig_test
hdc shell "cd /data/local/tmp/ruckig-0.19.4 && LD_LIBRARY_PATH=./lib bash ./run_test.sh ./ruckig_test > ruckig-device.log 2>&1"
set +e
hdc shell "cd /data/local/tmp/ruckig-0.19.4 && LD_LIBRARY_PATH=./lib bash ./run_test.sh ./ruckig_test --self-test-failure > ruckig-negative-control.log 2>&1"
negative_rc=$?
set -e
test "$negative_rc" -eq 1
hdc file recv /data/local/tmp/ruckig-0.19.4/ruckig-device.log .
hdc file recv /data/local/tmp/ruckig-0.19.4/ruckig-negative-control.log .
```

The normal run must exit 0 with 18/18 assertions. The negative control must exit
1 and print `[FAIL]`; an exit 0 from the negative control is itself a failure.

## Result

- Environment: HarmonyOS PC, HongMeng Kernel 1.12.0, aarch64
- Toolchain: OHOS SDK 26.0.0.18, Clang 15.0.4, Conan 2.29.1
- Normal test: 18/18 assertions, exit 0
- Negative control: intentional assertion failure observed, exit 1
- W3 local CI: 1/1 packages, 100%
- W3 log SHA256: `8db7bfff14c07982dc036e3d581cc684a162b6a5428fe10ab989894db67957d2`
