# seqwish 0.7.11 适配笔记（HarmonyOS PC / OHOS aarch64）

## 一、软件概况

- 上游：https://github.com/ekg/seqwish （tag `v0.7.11`）
- 源码 tarball：`https://github.com/ekg/seqwish/archive/refs/tags/v0.7.11.tar.gz`
  sha256 `9d9359faa4ca6c0d565d664100658b5872693d507d457dedc947ff10f425b255`
- 语言/构建：C++14，CMake（本包用 Unix Makefiles 生成器）
- 交付：单一命令行程序 `bin/seqwish`（把 PAF 比对诱导成 GFA 变异图，pangenome 图构建）
- 运行时依赖：`zlib/1.3.2`；OpenMP 用平台 `libomp.so`（sysroot `usr/lib/aarch64-linux-ohos/`）

## 二、源码获取：tarball 里 dep 目录全空，需取 13 个 git 仓库

GitHub 的源码归档不含 submodule 内容，`deps/` 下 11 个目录在 tarball 中**全为空**，且其中两个还各有自己的嵌套 submodule：

| 层级 | 数量 | 说明 |
|------|------|------|
| 顶层 `deps/*` | 11 | BBHash、args、atomic_queue、atomicbitvector、flat_hash_map、gzip_reader、iitii、ips4o、paryfor、mmmulti、sdsl-lite |
| `deps/mmmulti/deps/*` | 6（摸底台账） | 其中仅 `deps/mmmulti/deps/mio` 被构建引用并纳入 conandata（GitHub API 对 `deps` ref 返回 404，须按 `.gitmodules` 取名 + 固定 sha 取）；其余 5 项未被任何构建目标引用，已剪除 |
| `deps/sdsl-lite/external/*` | 1 | `libdivsufsort`（必需，已纳入）；同层 `googletest` 未被任何构建目标引用，已剪除 |

`conanfile.py` 的 `source()` 从 `conandata.yml` 的 `sources.submodules` 逐个 `get()` 到相对路径（每个都带固定 commit + sha256）——`sources.submodules` 共 **13 条**（11 个顶层 + `mmmulti` 的 `mio` + `sdsl-lite` 的 `libdivsufsort`），即本包实际取源集合；本机摸底台账另记 20 条（含未被构建引用的嵌套项）。缺任何一个都会在 configure 阶段以空目录 / 找不到头文件失败——例如缺 `deps/mmmulti/deps/mio` 时，`mmmulti` 的 include 链断在 `deps/mio/include`。

## 三、五枚补丁（全部为可移植性改动，无平台条件编译宏）

| 补丁 | 行数/块数 | 解决的问题 |
|------|-----------|-----------|
| `0001-bump-cmake-minimum-version.patch` | 10 行/1 块 | `cmake_minimum_required(VERSION 3.1)`：本机 CMake 4 已移除 3.5 以下兼容层，直接 configure 失败 → 抬到 3.10 |
| `0002-sdsl-lite-make-tests-optional.patch` | 34 行/4 块 | 关闭 sdsl-lite 自带 `test` 子目录：其测试在构建期联网下载测试集，且依赖未取到的 `external/googletest` |
| `0003-portable-current-dir-name.patch` | 58 行/4 块 | `get_current_dir_name()` 是 glibc 扩展，OHOS musl 不提供 → 用 POSIX `getcwd` 实现等价的 `current_dir_name()`（`src/tempfile.hpp`、`src/tempfile.cpp`、`src/main.cpp`） |
| `0004-optional-libatomic.patch` | 19 行/1 块 | 上游无条件 `-latomic`，但原子内建函数由编译器运行时提供的工具链并不附 `libatomic`（本机 sysroot 无该库）→ 改为 `find_library` 能力探测 |
| `0005-jemalloc-optional.patch` | 23 行/1 块 | 上游无条件链接 `jemalloc` → 改为 `SEQWISH_USE_JEMALLOC` 开关（**默认 ON，保持上游行为**），配方在本平台关闭（原因见第四节） |

补丁链顺序：0001 → 0004 → 0005 依次改同一文件 `CMakeLists.txt` 的不同区块，五枚补丁在本机 scratch 树上按序 dry-run 全部 rc=0（0004/0005 的基线已按「前序补丁已应用」重算，避免同一区块重复 hunk）。

## 四、关键决策：本平台不链接 jemalloc（静态库启动即崩）

现象：首次 `conan create` 成功（rc=0），但产物 `bin/seqwish --version` 与不带参数运行都立即 `SIGSEGV`（退出码 139）。

隔离复现（同一台 OHOS 设备，最小程序仅做 `std::string` / `std::unordered_map` 静态初始化）：

| 程序 | 链接选项 | 退出码 |
|------|---------|--------|
| 最小 C++ 程序 | 无 | **0** |
| 最小 C++ 程序 | `-fopenmp` | **0** |
| 最小 C++ 程序 | `-ljemalloc`（制品仓 `jemalloc/5.3.0`） | **139 (SIGSEGV)** |
| 最小 C++ 程序 | `-ljemalloc -lpthread` | **139** |
| 最小 C++ 程序 | `libjemalloc_pic.a` | **139** |

排除项：

- **不是 libc 归属错配**：`llvm-nm` 扫描 `libjemalloc.a` 的 `__libc_*` / `_IO_*` 符号命中数为 0，即该库本身是按 OHOS/musl 目标构建的。
- **不是 seqwish 代码问题**：最小 C++ 程序只要链上这个静态库同样崩；去掉即正常。
- **无共享版可退**：SDK sysroot、`/system/lib`、`/usr/lib` 均无 `libjemalloc.so`（制品仓该包也只提供 `.a`）。

处理：配方不引入 jemalloc（`requirements()` 只留 `zlib/1.3.2`），并由 `0005` 补丁把上游硬编码的 `jemalloc` 链接改成可关开关（默认 ON，其它平台行为不变），配方传入 `-DSEQWISH_USE_JEMALLOC=OFF`。代价是 seqwish 改用平台自带分配器（功能不受影响，上游引入 jemalloc 的动机是 musl 分配器在多线程下的性能）；节点级证据与复现命令见 PR 说明。

## 五、其它平台事实与坑

- **OHOS 的 CMake 分支不命中**：上游只对 `Darwin`/`Linux` 配置 OpenMP，OHOS 的 `CMAKE_SYSTEM_NAME=HarmonyOS` 两个分支都不命中 → 交叉编译须由配方显式提供 `-fopenmp` 编译与链接标志。
- **Ninja 不可用于本工程**：上游把 sdsl-lite 的库文件以「全路径」写进 `target_link_libraries`，而该文件由 `ExternalProject_Add` 在构建期生成；Ninja 生成器会判 `no-known-rule` 直接失败 → 换 Unix Makefiles（上游 CI 也是 Make）。
- **子构建变量继承**：父工程的 `CMAKE_C_FLAGS` / `CMAKE_CXX_FLAGS` / `CMAKE_ARGS` 会被 `ExternalProject_Add` 的 `CMAKE_ARGS` 继承（上游 sdsl-lite 子构建直接取父级同名变量），因此 `-fopenmp`、`-I/-L` 依赖路径、`CMAKE_POLICY_VERSION_MINIMUM` 一次透传即可，无需改子工程文件。
- **版本头文件由脚本生成**：上游构建期跑 `scripts/generate_git_version.sh`（`git describe`）生成 `include/seqwish_git_version.hpp`，源码树非 git 仓库时值为空串，上游有 `#ifndef` 兜底（`"not-from-git"`），不影响运行。
- **本机 `/tmp` 只读**：测试/构建脚本的临时文件必须落 `$TMPDIR` 或工作目录（消费者用例内部用 `mktemp -d "${TMPDIR:-.}/…"`）。

## 六、测试

- **上游测试**（bash-tap，`test/t/01_seqwish.t`，30 条断言）：
  `cd test && prove -v t` → **Ok 30 / Fail 0**，`Result: PASS`（2026-10-01 真机实跑，源码树 + 本包产物作为 `../bin/seqwish`）。29 条用例用 HLA 数据集端到端构图，产物 md5 与上游记录逐条比对。
- **消费者用例**（`test_package/test_seqwish.sh`）：**PASS 25 / FAIL 0**（2026-10-01 真机、CI 同口径 `sh` 调用，脚本内置 `PASS/FAIL` 汇总）。覆盖交付物隔离性、真实构图（合成 16M 自比对 → 3 行 GFA）、确定性、空 PAF 不崩、gzip 输入等价、负向对照，以及鸿蒙平台属性（musl 宿主、AArch64 PIE、不引用 glibc、链接 OHOS libc++/libomp）。

## 七、复现命令

```bash
# 制品仓依赖已就位后，本机复现编译 + 消费者用例
conan create archives/s/seqwish/0.7.11 \
    -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

# 上游测试（源码树内，需先把本包产物放到 bin/）
cd test && prove -v t
```
---

**编译结束**: 2026-10-01 07:18
**最终状态**: built
