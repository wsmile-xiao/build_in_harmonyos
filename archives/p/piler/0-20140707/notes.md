# piler 0-20140707 适配笔记（OHOS / HarmonyOS PC aarch64）

## 0. 目标与来源

| 项 | 值 |
|---|---|
| 目标库 | piler（PILER 1.0，基因组重复序列分析） |
| 任务声明版本 | `0-20140707`（= Debian 源包版本 `0~20140707`，上游 2014-07-07 快照） |
| 官方源码 | <https://www.drive5.com/piler/piler_source.tar.gz> |
| sha256 | `3b1be91c497bdb22eac8032a60c9f815bdcd03edc5b25d925314a02f54bec44f` |
| 归档形态 | flat tarball（**无顶层目录包裹**），48 个文件（40 × .cpp/.h 主体 + Makefile） |
| 语言 | C++（40/40 源文件，`lang-preflight` 判定 detected=cpp，匹配 task=cpp） |
| 构建系统 | 手写 Makefile（无 configure / 无 CMake / 无 install 目标） |
| 许可 | public domain（上游明确声明） |
| 产物 | 单个静态自包含可执行文件 `bin/piler2`（2.6 MB） |

**版本来源交叉核验**：`https://deb.debian.org/debian/pool/main/p/piler/` 的
`piler_0~20140707.orig.tar.gz` 与官方 `piler_source.tar.gz` **逐字节相同**
（`cmp` rc=0，sha256 一致）。Debian 侧 `debian/install` 亦为 `piler2 usr/bin`，
证明本包就是 drive5.com 的 PILER，而非同名邮件归档软件。

## 1. W0b 历史经验核验

- 本仓库 `archives/p/piler/` 无任何历史归档（`git log --all --diff-filter=A -- archives/p/piler/*` 空）。
- 无历史 notes.md 可参考 → 无可迁移性风险；本次为首适配，直接按 `ci/config` 能力矩阵作业。
- CI 能力矩阵对照：仅需 `gcc/clang/make`（✅ CI 具备），**无需 Rust/OCaml/Java 等缺失工具链**。

## 2. W0 依赖检查结论

- 源码 `#include` 全集（17 个头文件）全部落在 libc / libstdc++（C++ 标准库）/
  POSIX 头（`sys/time.h`、`sys/resource.h`、`unistd.h`、`fcntl.h`）。
  `windows.h`/`psapi.h`/`crtdbg.h` 均在 `#ifdef WIN32` / `_MSC_VER` 内，不参与 OHOS 编译。
- 链接声明仅 `-lm`（上游 Makefile `LDLIBS`）。
- `conanfile.py` **不含任何 `requires` / `tool_requires`** → 零第三方依赖。
- 工具链 sysroot 已提供 `libc.a` / `libm.a`（`.../ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/lib/aarch64-linux-ohos/`）。
- 最终产物 `DT_NEEDED = 0`（自包含）——运行期无需消费任何包。
- 结论：**无 R36 阻塞**；`--build=missing` 全程未使用。

## 3. OHOS 平台适配（首个真实错误 → 根因 → 最小修改 → 复验）

### 错误 1（首个错误，阻断构建）

```
$ make -j1
g++ -c -O3 -DNDEBUG=1  annot.cpp -o annot.o
make: g++: No such file or directory
make: *** [Makefile:22: annot.o] Error 127
rc=2
```
日志：`reports/logs/build-01-upstream-make-error.log`

**根因**：上游 Makefile `GPP = g++`（硬编码赋值，会覆盖环境 CXX）。OHOS aarch64
工具链只提供 `clang++`（`/data/service/hnp/bin/clang++`，target
`aarch64-unknown-linux-ohos`），不存在 `g++`。

**最小修改**：`GPP = g++` → `GPP = $(CXX)`，由 Conan 的
`tools.build:compiler_executables` 注入（R33：禁止依赖 shell 环境变量 `${CC}`/`${CXX}`）。

### 问题 2（工具链标志被丢弃）

上游 `CFLAGS = -O3 -DNDEBUG=1`（硬赋值）与 `LDLIBS = -lm -static`（硬赋值）
会丢弃工具链/conan 传入的 `CFLAGS`/`LDFLAGS`。
修改：`CFLAGS += -O3 -DNDEBUG=1`、`LDLIBS = $(LDFLAGS) -lm -static-pie`。
复验（`make CXX=<toolchain clang++>`）可见工具链标志生效：

```
/data/service/hnp/bin/clang++ -c -fPIC -O2 -O3 -DNDEBUG=1  annot.cpp -o annot.o
/data/service/hnp/bin/clang++ -fPIC -O2 -O3 -DNDEBUG=1 -o piler2 ... \
    -L/storage/Users/currentUser/usr/local/lib -lm -static-pie
```

### 问题 3（安全硬化：非 PIE）

上游 `-static` 的产物 `readelf -h` → `Type: EXEC`（非 PIE）、无 `.dynamic`：

```
$ readelf -hl piler2 | grep -E "Type:|GNU_RELRO"
  Type:                              EXEC (Executable file)
  GNU_RELRO      0x... (存在)
```

鸿蒙硬化基线（`conan-verify` L4 的 NX/PIE/RELRO 扫描）对非 PIE 可执行文件报
`PIE disabled`；Debian 打包同样移除了上游的 `-static`
（`debian/patches/compiler-flags.patch`）。

**为什么不是直接删 `-static`**：实测本机默认动态链接会引入
`NEEDED libc++_shared.so`，而 OHOS CLI 运行期并不保证共享 libc++ 可用；
上游"自包含单文件二进制"的语义应当保留。实测三种链接方式：

| 方式 | Type | DT_NEEDED | RELRO | BIND_NOW | NX |
|---|---|---|---|---|---|
| `-static`（上游） | EXEC | 0 | partial | ✗ | ✓ |
| 默认（动态） | DYN | 2 (`libc++_shared.so`, `libc.so`) | full | ✗ | ✓ |
| **`-static-pie`（采用）** | **DYN(PIE)** | **0** | **full** | **✓** | **✓** |

**最小修改**：`-static` → `-static-pie`，同时满足"自包含"与"PIE + full RELRO + NX"。

**补丁**：`patches/0001-ohos-makefile-toolchain-hardening.patch`（仅 3 行改动，
无平台宏，`patch -p1 --dry-run` rc=0）。

## 4. source() 的一个坑

上游 tarball 是 flat 归档。Conan 的 `get(..., strip_root=True)` 会直接报
`ConanException: Can't untar a tgz containing files in the root with strip_root enabled`，
必须 `strip_root=False`。

## 5. 上游测试入口核验（结论：上游无任何自动化测试）

| 探测项 | 命令 | 结果 |
|---|---|---|
| tarball 内测试/样例文件 | `tar tzvf piler_source.tar.gz \| grep -iE "test\|check\|spec\|example\|sample\|data"` | 无匹配（rc=1） |
| Makefile 目标 | `grep -nE "^[A-Za-z_.$-]+:" Makefile` | 仅 `all: piler2`（无 check/test/install） |
| tests 目录 / CMake / Meson / setup.py | `ls -d tests test CMakeLists.txt meson.build setup.py` | 全部不存在（rc=1） |
| ctest/pytest 注册 | `grep -rnE "add_test\|ctest\|pytest\|unittest\|meson test" .` | 无匹配（rc=1） |
| 测试源文件 | `ls *test*` | 0 个 |

证据文件：`reports/evidence/upstream-test-entry-probe.txt`

上线策略：**不伪造上游测试**；`MANIFEST.yml` 中 `upstream_tests: []` 并写明理由；
功能覆盖改由 `test_package/` 按上游 User Guide 的**全部**工作流补全。

## 6. 测试覆盖设计（补全用例）

上游 User Guide（<https://www.drive5.com/piler/piler_userguide.html>）记载的
工作流与 `main.cpp` 分派的子命令**一一对应**，全部覆盖（16 项功能用例）：

`-version` / `-help` / `-crisp` / `-trs` / `-trs2fasta` / `-tr` / `-tan` /
`-tanmotif2fasta` / `-cons` / `-annot` / `-annotedge` + 2 项负向
（缺输出选项、畸形 GFF）+ 3 项上游可选行为修饰 flag
（`-multihit` / `-quiet` / `-exact`）。

上游 `options.cpp` 的 `FLAG_OPT` 表中另有 `-edge` / `-pilesonly` 两项，
但全工程对其无任何引用（死选项），无可测行为，故不设用例。

夹具（`test_package/data/`，11 个，全部按上游 GFF/FASTA 格式手工构造）：
- `crisp_hits.gff`：合成 CRISPR 阵列（29 bp 直向重复 × 8，间隔 32 bp）
- `disp_hits.gff` / `disp_genome.fasta`：900 bp 元件 × 4 拷贝的自比对命中
- `trs_in.gff`：TRS 格式输入（供 `-annot`/`-annotedge`/`-trs2fasta` 独立使用）
- `ltr_hits.gff`：4 个元件 5'/3' LTR 候选 + 元件间连接命中（≥50 kb 相隔）
- `tan_hits.gff` / `tan_genome.fasta`：串联重复嵌套命中金字塔
- `aln.fasta`：3 序列等长比对（`-cons`）
- `reps.gff`：RepeatMasker 风格第三方注释（`-annot`/`-annotedge`）
- `bad.gff`：畸形 GFF（负向）

另有 **2 项鸿蒙特有用例**（`test_package/conanfile.py` 内纯 stdlib 解析 ELF，
不依赖 `readelf`）：`ohos_elf_hardening`、`ohos_selfcontained_no_libcxx`。

## 7. 已知平台限制 / 未做改动

- `utils_linux.cpp` 的 `GetRAMSize()` 查找 `/proc/meminfo` 中的 `"Mem: "`，
  该串在 Linux/OHOS 上都不存在 → 恒返回 `DEFAULT_RAM=1e9`。这是**上游既有行为**，
  与平台无关（Linux 上同样如此），不影响功能，未改动（R1 最小改动原则）。
- `Makefile` 第 14 行 `CC = gcc -c $(CFLAGS)` 未被使用（工程内无 `.c` 文件，
  `CPPSRC` 只匹配 `*.cpp`），未改动以免引入与上游语义无关的差异。
- `register` 关键字在 C++17 下产生 14 条 `-Wdeprecated-register` 警告
  （上游代码风格，非错误），未改动。

## 8. 环境阻塞记录（非本包问题）

- **conan cache 索引损坏**：`~/.conan2/p/cache.sqlite3` 为 0 字节（mtime 12:40，
  早于本任务启动），缺 `recipes`/`packages` 表，导致所有 conan 写操作报
  `sqlite3.OperationalError: no such table: recipes`。
  修复：用 conan 自身 DDL（`RecipesDBTable/PackagesDBTable.create_table`，
  `CREATE TABLE IF NOT EXISTS`）补建缺失表；0 字节原件已备份为
  `cache.sqlite3.zero-byte-bak-*`。未删除、未覆盖任何数据。
- **inode 耗尽**：全机 `ffree≈4999 / 48455677`，导致 `Errno 28 No space left on device`
  （块空间仍有 ~200 GB）。清理 `$HOME/tmp`（环境声明为可随时清理的临时区）中
  已结束任务遗留的验证副本（`ohc-verify-*`、`cleanHEAD`、`mk2clean`、
  `audit-r3-cleanout`、`cc-audit-*`、`build_in_harmonyos-clean` 等），
  回收 inode 至 ~3.15 M 后重跑成功。
---

**编译结束**: 2026-10-01 14:52
**最终状态**: built
