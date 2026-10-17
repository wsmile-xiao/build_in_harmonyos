# p0f 3.09b HarmonyOS PC adaptation notes

## Build environment
- Build system: custom build.sh and Makefile
- Compiler: Clang 15
- Target: HarmonyOS PC aarch64
- Dependency: libpcap/1.10.6

## Build steps

The upstream `build.sh all` target was executed with Conan-provided compiler and libpcap include/library paths. The helper programs were then built with `make -C tools -j1`.

The upstream script uses `#!/bin/bash`, while the OHOS environment provides bash at `/data/service/hnp/bin/bash`; the Conan recipe invokes the script explicitly with that interpreter without modifying upstream source.

## Problems and solutions

| Problem | Root cause | Solution |
|---|---|---|
| `pcap.h` not found | libpcap is not a system development dependency in the clean worker | Inject `libpcap/1.10.6` include and library paths from Conan |
| `./build.sh` cannot execute directly | Upstream shebang points to `/bin/bash`, unavailable on OHOS worker | Invoke `bash ./build.sh all` using the Conan profile's OHOS bash |

## Upstream tests

p0f 3.09b has no test directory, test target, or automated test command. Its documented build checks are part of `build.sh all`; these were executed and recorded separately from consumer tests.

## Verification

- `conan download libpcap/1.10.6 -r=ohpcd --only-recipe`: passed
- `bash ./build.sh all`: passed with Conan libpcap paths
- `make -C tools -j1`: passed
- Consumer tests: 4/4 passed (real TCP SYN offline pcap path plus three helper usage paths)
---

### 对话 #1

完成 p0f 3.09b 的 Conan 配方、libpcap 依赖注入、主程序与三个工具构建，并完成 4/4 消费者测试、W3 定向本地 CI 和 W4 独立审计。

**编译结束**: 2026-09-05 01:18
**最终状态**: built
