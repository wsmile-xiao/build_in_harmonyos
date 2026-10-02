# DRAFT: GitHub release tarball + CMake ExternalProject 组合包在 OHOS aarch64 上的适配套路

- **草稿 id**: `DRAFT-SEQWISH-0711-SUBMODULE-CMAKE-OHOS-BUNDLE`
- **来源**: seqwish 0.7.11 适配（OHOS 26.0.0.18 / aarch64 / musl / clang 15 / cmake 4.1）
- **严重度**: 2（配置/编译期阻断，但每一环都有确定解法）

## 五类坑与解法（按命中顺序）

| # | 现象 | 根因 | 解法 |
|---|------|------|------|
| 1 | configure 报缺头文件 / 空目录 | GitHub `/archive/<ref>.tar.gz` 不含 submodule 内容（`deps/` 全空，mmmulti 还有 6 个嵌套、sdsl-lite 另引 `external/libdivsufsort`） | 按 `.gitmodules` 固定 commit 逐个取源并写进 `conandata.yml` 的 `sources.submodules`，由 `source()` 落盘（conandata 声明 13 个 submodule 仓库：11 个顶层 + mmmulti 的 mio + sdsl-lite 的 libdivsufsort）；**不要**依赖构建期 `git clone` |
| 2 | `cmake_minimum_required(VERSION 3.1)` 直接失败 | CMake 4 移除 `<3.5` 兼容层 | 父工程抬版本（补丁 0001）；子工程（ExternalProject 拉起）不改文件，改由父级 `CMAKE_ARGS` 透传 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 3 | `no known rule to make it`（Ninja） | 上游把子工程产物的**全路径库文件**写进 `target_link_libraries`，Ninja 无法推导规则 | 生成器换 `Unix Makefiles`（上游 CI 亦用 Make） |
| 4 | `Could NOT find OpenMP` / 链接缺 `libomp` | 上游只按 Darwin/Linux 分支配置 OpenMP，OHOS 的 `CMAKE_SYSTEM_NAME=HarmonyOS` 两分支都不命中 | 配方显式补 `-fopenmp` 编译与链接标志（平台 `libomp.so` 在 `sysroot/usr/lib/aarch64-linux-ohos/`） |
| 5 | `implicit declaration` / `undefined reference to get_current_dir_name` | glibc 扩展，musl 无 | POSIX `getcwd` 等价替换（补丁 0003）；**禁止**用 `__OHOS__` 之类平台宏做条件编译（R8） |

## 关键机理

- 父工程的 `CMAKE_C_FLAGS` / `CMAKE_CXX_FLAGS` / `CMAKE_ARGS` 会被 `ExternalProject_Add` 的 `CMAKE_ARGS` 继承
  （上游 sdsl-lite 子构建直接取父级同名变量）→ `-fopenmp`、`-I/-L` 依赖路径、策略变量都能一次性透传，**无需改上游子工程文件**；
- 子工程自带的测试目录（sdsl-lite 的 `test/`）构建期会联网下载测试集 → 补丁 0002 将其改为可选（默认 OFF）。

## 关联

- 配方: `archives/s/seqwish/0.7.11/conanfile.py`（`generate()` 中逐条注释了上述取舍）
- 补丁: 0001（cmake 最低版本）、0002（子工程测试可选）、0003（POSIX 目录名）
- 数据源: `archives/s/seqwish/0.7.11/conandata.yml`（`sources.submodules`，13 条固定 commit + sha256）
