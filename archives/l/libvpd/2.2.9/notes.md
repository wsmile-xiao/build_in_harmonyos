# libvpd 2.2.9 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4 / clang++（DevBox，`/data/service/hnp/bin/`）
- 依赖: sqlite3/3.53.4（制品仓，且由源码构建）
- 状态: built（库产物已生成并验证架构）

## 适配步骤

1. 解包上游 tarball（GitHub 官方 tag v2.2.9；与 Debian orig 逐文件等价，已核实）
2. 应用 `patches/0001-ohos-makefile-portability.patch`：
   对 Makefile.am 做 3 处源码层可移植性修改（`-lstdc++`→`-lc++`、
   `-I./src`→`-I$(srcdir)/src`、`install --mode=644`→`-m 644 $(srcdir)/`）
3. `build()` 阶段用 tool_requires 拉入的 automake/libtool **在 CI 内自举**：
   `apply_conandata_patches` → `aclocal -I m4` → `autoconf` → `autoheader`
   → `automake --add-missing --copy`（全程 `self.run(env="conanbuild")`，
   使 `$ACLOCAL`/`$AUTOMAKE` 等由 VirtualBuildEnv 注入的变量生效）
4. **不随配方提交任何 autotools 生成物**（configure / Makefile.in / aclocal.m4 /
   config.* / ltmain.sh / m4/*）：遵守 R6「只改源文件不改生成文件」，生成物
   由 CI 从源码复现。automake/1.18 自带的 config.sub 已识别
   `aarch64-linux-ohos`（实测 `sh config.sub aarch64-linux-ohos` →
   `aarch64-unknown-linux-ohos`），故无需随附 config.guess/config.sub
5. `build()` 对新生成的 configure 就地修 shebang（`/bin/bash` →
   `/data/service/hnp/bin/bash`）与 HMDFS 临时目录 workaround，然后 configure + make

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ld.lld: unable to find library -lstdc++` | OHOS 只有 libc++ | patch：`-lstdc++` → `-lc++` |
| 2 | `checking for sqlite3.h... no` | sqlite3 不在 sysroot | `AutotoolsDeps` 注入依赖的 -I/-L |
| 3 | `config.status: error: could not create Makefile` | HMDFS 拒写 umask 077 的 700 临时目录 | 配方加 workaround（改 umask 022 mkdir） |
| 4 | `'libvpd-2/vpddbenv.hpp' file not found with <angled> include` | 上游 `AM_CPPFLAGS = -I./src/` 假定 in-tree 构建；conan 是 out-of-tree | Makefile.am 改 `-I$(srcdir)/src/`，并由 conanfile 额外注入 `-I<srcdir>/src` 双保险 |
| 5 | `install: Unknown option 'mode=644'` / `bad '90-vpdupdate.rules'` | 上游 install-exec-hook 用 GNU coreutils 语法，OHOS 是 busybox install；且 out-of-tree 下源文件需 `$(srcdir)/` | Makefile.am：`--mode=644` → `-m 644`，并加 `$(srcdir)/` 前缀 |
| 6 | `aclocal.m4` 比 `Makefile.in` 新 → make 触发 automake 重建 → `automake-1.16: command not found` | 早期方案把 autoreconf 产物（preconf/）随配方提交，逐个 `os.utime(fp, None)` 取当前时刻导致时间戳倒挂 | **已弃用该方案**：改为 build() 内用 tool_requires 的 automake/libtool 当场自举，不存在提交生成物与时间戳问题（同时修复 R6 违规） |
| 7 | 测试 `SIGTRAP` / `SIGSEGV` | ① `free_dataitem()` 内部已释放字段，测试又手动 free → 双重释放；② `new_vpddbenv()` 会尝试打开 sqlite 库、失败返回 NULL，而测试用 `assert` 判空，但构建带 `-DNDEBUG` 使断言被移除 → NULL 解引用 | 去掉手动 free；改用显式 `CHECK` 宏（不用 assert）并判空 |
| 8 | 早期误判「CI worker 无 libtoolize/aclocal/automake」而把 51276 行 autoreconf 生成物随配方提交 | 未先查制品仓：automake/1.18 与 libtool/2.5.4 实际**均已发布**，CI 内可自举；生成物占 PR 98% 行数并违反 R6 | 改用 `tool_requires("automake/1.18")` + `tool_requires("libtool/2.5.4")` + `VirtualBuildEnv`（仓库 240 处先例同款），PR 从 51979 行降至 ~700 行 |

## 源码修改

`patches/0001-ohos-makefile-portability.patch`
```
-libvpd_cxx_la_LDFLAGS = -module -lstdc++ -version-info \
+libvpd_cxx_la_LDFLAGS = -module -lc++ -version-info \
 
（补丁 0001 共 3 处修改，另两处见问题表第 4、5 条）
```

## 验证结果（conan create 全流程，已实测通过）

```
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
...
1/3 Test #1: test_libvpd_c ......................   Passed    0.05 sec
2/3 Test #2: test_libvpd_cxx ....................   Passed    0.06 sec
3/3 Test #3: test_libvpd_ohos ...................   Passed    0.05 sec

100% tests passed, 0 tests failed out of 3
退出码: 0
```

**测试用例通过率：3/3 = 100%（共 92 项显式断言）**（本仓库上游零测试，测试为本适配补齐的消费者用例）

### 测试覆盖（上游公开 API 全量 + 鸿蒙专有）

| 用例 | 覆盖对象 | 断言数 |
|------|----------|--------|
| `test_libvpd_c` | C API：6 个头文件的 **24 个函数全部覆盖**（common.h 的 list 三函数、dataitem 构造/追加/打包长度/unpack 往返、component 构造/追加/unpack 契约、system、vpddbenv 的 fetch 空库契约、vpdretriever 的 get 空指针守卫） | **45** |
| `test_libvpd_cxx` | C++ API：`libvpd_cxx.a` 的 lsvpd::DataItem / Source / Component / System 四类（默认构造、访问器、pack↔unpack 往返、析构释放） | **36** |
| `test_libvpd_ohos` | **鸿蒙专有**：①编译期 `__OHOS__` 已定义；②运行期 `uname(2)` = HarmonyOS/aarch64；③标准库为 libc++（`_LIBCPP_VERSION` 存在且无 `__GLIBCXX__`）——即 `-lstdc++`→`-lc++` 补丁的判据；④静态链接产物可用（无 .so，直接调用 C/C++ API） | **11** |
| **合计** | | **92** |

> - C++ 用例为本次补齐：配方 `package_info` 声明 `libs = ["vpd", "vpd_cxx"]`，
>   但此前 C 用例只触及 C API，**`libvpd_cxx.a` 随包发布却从未被链接验证过**。
> - 鸿蒙专有用例为本次补齐：把适配赖以成立的平台前提写成可执行判据，
>   平台假设一旦不成立立即显形（不依赖真机 VPD 数据，故 CI 稳定）。
> - 本配方 `shared=False`（R26），**无 .so 产物**，故鸿蒙用例按静态链接直接
>   调用 API，而不是先例 2.2.11 那种 `dlopen` 方式。

### 分阶段实测记录

| 阶段 | 结果 |
|------|------|
| source / generate | ✅ |
| build（tool_requires 自举 autoreconf + configure + make） | ✅ 退出码 0 |
| package（含 install-exec-hook） | ✅ 退出码 0 |
| test_package 编译链接（C + C++ + 鸿蒙专有） | ✅ |
| test_package 运行 | ✅ 3/3 Passed，0 失败 |

### 产物

配方默认 `shared=False`（R26），产出静态库 `libvpd.a` / `libvpd_cxx.a`；
经 `llvm-readelf -h` 确认为 **ELF64 / AArch64**。

## 注意事项
- 上游 `install-exec-hook` 会 `mkdir -p $(DESTDIR)/${sysconfdir}/udev/rules.d/`，
  OHOS 无 udev；配方已把 sysconfdir/localstatedir 收敛到 prefix 内，仅靠 DESTDIR 保证不写系统路径
- 本库源自 IBM PowerPC 生态（VPD 为 Power 硬件清单），在 aarch64/OHOS 上
  依赖真实 VPD 数据的接口（如 `get_system` 读取 `/sys/bus`）无法产生有效数据，
  故测试刻意只覆盖不依赖硬件的接口，避免假失败

## 参考知识库条目

下表为本次适配各问题所对应的知识库条目（位于 `knowledge/graph/`）：

| 条目 | 对应问题 | 要点 |
|------|----------|------|
| E165 | 适配步骤 5 | OHOS 无 `/bin/bash`：新生成的 `configure` shebang 需改写为 `/data/service/hnp/bin/bash` |
| E060 | 问题 3 | HMDFS 下 `config.status` 用 `mktemp -d "./confXXXXXX"` 在当前目录建临时目录会失败，需改 `umask 022` + `mkdir` |
| E188 | 问题 5（前半） | OHOS 的 `install` 是简化版 coreutils，GNU 长选项 `--mode=` 不可用，需改为 `-m` |
| E519 | 问题 5（后半） | out-of-source 构建下安装数据文件必须加 `$(srcdir)/` 前缀，否则 `cannot stat: No such file` |
| E259 | 问题 7 | Conan Release 注入 `-DNDEBUG` 使 `assert()` 整体不求值，**不能**用 `assert()` 判空 |
| E007 / E072 | 适配步骤 3（历史） | 曾用 config.guess/config.sub 覆盖识 `aarch64-linux-ohos`；现改用 automake/1.18 自带 config.sub（已原生识别 ohos），该覆盖已移除 |
---

**编译结束**: 2026-09-28 19:24
**最终状态**: built
