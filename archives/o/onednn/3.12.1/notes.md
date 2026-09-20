# onednn 3.12.1 适配笔记

## 编译环境
- 构建系统: cmake（Conan CMakeToolchain，`ONEDNN_*` + `DNNL_*` 双前缀，靠 `cmake/dnnl_compat.cmake` 互通）
- 编译日期: 2026-09-20
- 编译器: ohos-sdk 26.0.0.18 的 clang/clang++ 15.0.4，target `aarch64-linux-ohos`，musl
- CPU runtime: OpenMP（`-fopenmp` + `libomp.so`）；workload `TRAINING`；无 GPU/ACL/graph
- 上游坐标: tag `v3.12.1` = `c8c37fdbecb5aa4dcf5ea7e77fba0fd1a98bd16f`，
  tarball sha256 `e1db6e9c3771ba137a6e9292c31870471362977760d0ca00adef2fd39e23840b`
  （本机 `github.com/.../archive/refs/tags/v3.12.1.tar.gz` 与 `codeload.github.com` 两种
  URL 字节同 sha256；真机 curl 同一 URL 亦同 sha）

## 真机取证（独立 CONAN_HOME，不碰共享 `~/.conan2`）
```
CONAN_HOME=~/work/psj/ch-onednn
conan create archives/o/onednn/3.12.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
CREATE_EXIT:0
95% tests passed, 3 tests failed out of 63
Total Test time (real) = 2600.11 sec
The following tests FAILED:
	 15 - test_eltwise (Timeout)        # 600.06s
	 40 - test_reorder (Failed)         # 4.07s，12/237 用例
	 57 - test_api (Timeout)            # 600.03s
onednn version=3.12.1 engine=cpu ok: 12/12 assertions passed   # test_package 消费者
```
- 配方 rev `29fdb6dfdc6b13404a7eef654119d1fd`、包ID `01d92cf349a0dd98ff915f4bd99a04430171517f`、
  包 rev `abab0793a59d6689e43559a6e7e794c3`
- 产物 `p/lib/libdnnl.so` 60308096 B，`ELF 64-bit LSB arm64`，NEEDED 仅
  `libc.so` / `libc++_shared.so` / `libomp.so`；`p/include` 26 个头 + `licenses/LICENSE`
- 日志 `~/work/psj/onednn121/create2.log`；上游源码 `~/work/psj/onednn121/onednn-3.12.1.tar.gz`
  （经 `OHC_TARBALL` 注入，绕过真机到 github 的 30s 连接超时；URL 与 sha 已由 curl 单独验证）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `util_impl_linux.h` 报 `use of undeclared identifier '_SC_LEVEL1_ICACHE_SIZE'` | OHOS musl 的 confname 表有 141 个 `_SC_*` 但 0 个 `_SC_LEVEL*`；真机也没有 `/sys/devices/system/cpu/cpuN/cache`（`ls -d` 计数 0），xbyak_aarch64 的「字典→sysfs→sysconf」三级探测前两级空、第三级不存在 | 配方 `source()` 把 sysconf 兜底分支 4 行写成常量（L1i/L1d 32KiB、L2 256KiB、L3 0）；机制与更好的上游形态（`#ifdef _SC_*` 存在性守卫）见 `knowledge/drafts/DRAFT-onednn-3.12.1-musl-sysconf-cache-keys-unavailable` |
| 2 | 默认按 X64 编、强加 `-msse4.1` | `CMAKE_SYSTEM_PROCESSOR` 探测不到 OHOS | 显式 `DNNL_TARGET_ARCH=AARCH64` + `ONEDNN_TARGET_ARCH=AARCH64` + `CMAKE_SYSTEM_PROCESSOR=aarch64` |
| 3 | `R_AARCH64_* relocation ... must be bound to definition` / OBJECT 库非 PIC | 上游目标未开 PIC | `CMAKE_POSITION_INDEPENDENT_CODE=ON` |
| 4 | benchdnn 参与构建拖长 CI | 它是独立基准套件、0 个 `TEST` 宏、不注册 ctest 用例 | `tests/CMakeLists.txt` 注释 `add_subdirectory(benchdnn)` |
| 5 | 运行期 `libomp.so` 找不到 | OpenMP runtime 在 SDK 的 `native/llvm/lib`，不在默认搜索路径 | `_run_ctest()` 把该目录并入 `LD_LIBRARY_PATH`（profile 的 `[buildenv]` 已含同一路径，故 `test_package` 无需额外处理） |
| 6 | 真机直连 `github.com` 拉源码 `ConnectTimeout (connect timeout=30)` | 真机到 github 的连通性时好时坏（同 URL curl 需 4 分钟） | 本机 + 真机双侧核 sha256 后用 `OHC_TARBALL` 离线注入；配方里的 `sources.url` 保持单值官方 URL 不变（CI 侧走它自己的镜像注入） |

## 与已合入 3.13 的差异
- 3.12.1 的 `tests/CMakeLists.txt` 用 `include_directories_with_host_compiler(${PROJECT_SOURCE_DIR}/third_party)`
  取代 3.13 的按 `DNNL_TARGET_ARCH` 分支写法；两处 `replace_in_file` 目标（sysconf 块、
  `add_subdirectory(benchdnn)`）在 3.12.1 源码上逐字命中，补丁上下文零改动复用。
- 真机结果优于 3.13：3.13 为 58/63（`test_pooling_forward`/`test_pooling_backward` SEGFAULT），
  3.12.1 两个 pooling 二进制均 Passed（`test_pooling_backward` 82.34s），失败集合缩小到 3 个。

## 依赖
无（googletest 由 `tests/third_party/gtest` 内置随源码发布，不联网拉取）
