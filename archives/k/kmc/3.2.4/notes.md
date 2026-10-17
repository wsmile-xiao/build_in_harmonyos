# kmc 3.2.4 适配笔记

## 编译环境
- 构建系统: makefile（上游顶层裸 Makefile，无 configure/autotools；`build.system: makefile`）
- 编译日期: 2026-09-23
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos，HNP 工具链）
- 状态: built

## 编译步骤

1. 源码：GitHub tag archive（`refresh-bio/KMC` tag `v3.2.4` → `d6c24dc88010…`，sha256 `dde49d9a…5504c`）+ 锁定 commit 的 zlib 子模块（`.gitmodules` → `refresh-bio/dependencies-zlib` @ `3cccc9613d79…318a`，经 `git ls-tree HEAD 3rd_party/cloudflare` 实核；sha256 `14e5fc5d…461462`），双源在 `conandata.yml` 分键锚定。
2. 捆绑 zlib：`CC=<profile clang> bash ./configure && make libz.a -j1`（在 `3rd_party/cloudflare/`）——先于顶层 make 预构建，使上游 `$(LIB_ZLIB)` 规则（无依赖、目标已存在）自动跳过。
3. 顶层构建：`make CC=<clang++> kmc kmc_tools kmc_dump -j1`（目标列表与上游 `.github/workflows/main.yml` 完全一致；`CC=` 命令行覆盖 Makefile 硬赋值 `CC = g++`——设备/CI 无 g++）。aarch64 分支由上游 Makefile 自动选 `raduls_neon.o`（`-march=armv8-a`），不编 SSE/AVX 变体。
4. 上游测试：`build()` 末尾逐字复刻上游 workflow linux-remote job 4 步（bash，含 `cmp … 70` 与 `cmp … pattern.dump` 两个硬断言）。
5. 产物布局对齐上游官方 `KMC3.2.4.linux.arm64.tar.gz`（实核清单）：`bin/{kmc,kmc_tools,kmc_dump}` + `libkmc_core.a`（放 Conan 标准 `lib/`）+ `include/kmc_runner.h`；**不含** py_kmc_api（上游发行物与上游 CI 均不构建/不发布）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `fatal error: 'ext/algorithm' file not found` | OHOS NDK 用 libc++，无 libstdc++ 专属 `<ext/algorithm>`；`__gnu_cxx::copy_n` 是 GNU 命名空间（copy_n 本身是 C++ 标准算法） | 补丁 `0001-libcxx-portability-ext-algorithm-to-std-algorithm.patch`（2 文件 3 行改动：`<ext/algorithm>`→`<algorithm>` ×2、`__gnu_cxx::copy_n`→`std::copy_n` ×1，patch 内 `-`/`+` 各 3 行；`copy_n` 全仓无调用点，纯死引用收敛） |
| 2 | 捆绑 zlib `./configure` 报 `Compiler error reporting is too harsh`（探测 gcc） | 设备/CI 无 gcc，zlib configure 默认 `CC=gcc` | 配方 `CC=<clang>` 预构建 `libz.a`（上游规则被 make 跳过，不改上游 Makefile） |
| 3 | Makefile 硬赋值 `CC = g++`（设备无 g++） | 上游面向桌面 Linux 假定 gcc | `make CC=<clang++绝对路径>` 命令行覆盖（make 命令行变量优先于 makefile 赋值） |
| 4 | 首次 `conan create` 报 `Package type is 'library', but no 'shared' option declared` | 上游仅发行静态 `libkmc_core.a`，无 shared 产物 | `package_type = "static-library"`（不加空开关 shared 选项） |
| 5 | `conan create` 报 `[conf] 'tools.build:compiler_executables:c' does not exist` | 本机 conan 2.29 中该 conf 是整个 JSON dict，不支持 `:c`/`:cpp` 深取（模板写法与现场实现不符） | 先 `self.conf.get("tools.build:compiler_executables")` 取 dict 再按键 `c`/`cpp` |
| 6 | `make py_kmc_api` 9 errors：`member access into incomplete type 'PyFrameObject'` | 上游捆绑 pybind11 2.3.dev（2015 年代）与 Python ≥3.11 不兼容（PyFrameObject 3.11+ 不透明化）；设备 python 3.12.9/3.13.15 无旧版 | 判 NOT_RUN（上游官方发行物亦不含 py_kmc_api、上游 CI 不构建它）；替代验证：test_package T5 以底层 `kmc_runner.h` API 覆盖等价功能路径 |
| 7 | 链接出现 `-static-libgcc` unused 警告 | clang 在编译阶段不消费该 flag | 仅 warning 不阻塞；实测产物 NEEDED 仅 `libc.so`（libc++ 静态链入，无 libstdc++ 残留），符合 OHOS 形态 |

## 源码修改

- `patches/0001-libcxx-portability-ext-algorithm-to-std-algorithm.patch`（portability）：
  - `kmc_core/defs.h`：`#include <ext/algorithm>` → `#include <algorithm>`；`using __gnu_cxx::copy_n;` → `using std::copy_n;`
  - `kmc_api/kmer_defs.h`：`#include <ext/algorithm>` → `#include <algorithm>`
  - 无其他源码/构建系统改动；上游 Makefile、测试脚本、workflow 全部保持原样。

## 依赖版本

- 外部 conan 依赖：**无**（`requirements()` 为空）
- 捆绑 zlib：`3rd_party/cloudflare` 子模块 @ `3cccc9613d79781a8486f9bae1ff38103963318a`（zlib 1.2.8 系 cloudflare fork，源内 `configure` 构建 `libz.a`，静态链入工具）
- 工具链：clang/clang++ 15.0.4（HNP）、GNU Make 4.4.1、`/data/service/hnp/bin/bash`（CONFIG_SHELL）

## 平台可移植性（W0）

- 上游 tag `v3.2.4` 实核：`git ls-remote --tags` → `d6c24dc88010508336d824bbffbf1ef3f49fddf8`；codeload 与 `marekkokot/kmc`（重定向同仓）sha256 一致。
- 无强制 x86 路径：`raduls.h`/`raduls_impl.h`/`intr_copy.h`/`cpu_info.cpp` 均有 `#if defined(__aarch64__)` NEON 分支；无 `altivec.h`/`3dnow`/`register_printf_*` glibc 钩子命中（grep 清点 0）。

## 验证结果

```bash
# 上游 CI 4 步（逐字复刻，设备实跑）——详见 PR 正文测试统计表与 reports/
bash upstream_ci_checks.sh   # rc=0，[upstream-ci] ALL 4 upstream workflow test steps PASS
# 采信轮（清缓存干净轮）
sh tools/conan_verify_round.sh kmc 3.2.4 --repo "$TARGET_REPO" --task-dir "$TASK_DIR"
```

（具体 PASS/NOT_RUN 计数以 PR 正文测试统计表为准，全部由最终设备日志复算。）

## 注意事项

- 顶层 Makefile 每次 make 打印 `fatal: not a git repository`（`$(shell git submodule update …)` 在非 git 解压树失败）——**噪声非错误**，submodule 内容已由配方 source() 按锁定 commit 落位。
- 上游无 `make check`/`test` 目标（顶层 Makefile 已清点）；测试入口三家族见 `test_package/MANIFEST.yml`。
- 许可证：上游 README §License 声明 GNU GPL 3，tarball 未随包分发独立 LICENSE 文本文件（如实披露，未伪造）。
