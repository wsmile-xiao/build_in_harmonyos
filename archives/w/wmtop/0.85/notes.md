# wmtop 0.85 适配笔记

## 编译环境
- 构建系统: autotools（上游发布仅 configure.ac/Makefile.am，无生成好的 configure，须自举）
- 编译日期: 2026-09-27
- 编译器: clang（profile: ci/conan/profiles/ohos-aarch64，os=OHOS arch=armv8 clang 15 libc++ cppstd=17）
- 状态: published
- 隔离验证环境: 独立 git worktree（feat/wmtop-0.85）+ 独立 CONAN_HOME（零缓存，全部二进制自远端 ohpcd 实拉）

## 编译步骤

1. `conan create archives/w/wmtop/0.85 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
2. 自举（配方 `build()` 内完成，因上游不带 configure）：
   - `perl .aclocal-real --automake-acdir=<pkg>/share/aclocal-1.18 --system-acdir=<pkg>/share/aclocal --force`（内联 `ACLOCAL_PATH` 指向 hnp pkg.m4）
   - `autoconf -o configure configure.ac`
   - `perl .automake-real --libdir=<pkg>/share/automake-1.18 --add-missing --copy --foreign`
3. `sh ./configure --prefix=/ --build=aarch64-linux-ohos --host=aarch64-linux-ohos ...`（内联 `LD_LIBRARY_PATH`=依赖 lib 目录、`SHELL/CONFIG_SHELL=/bin/sh`、PATH 前置 /system/bin）
4. `make -j1` → `make check -j1` → `make install DESTDIR=<pkg>`

## 上游测试清点（R51 三步法）

| 清点项 | 结果 |
|--------|------|
| Makefile.am 中 TESTS / check_PROGRAMS | 无 |
| tests/ 等测试目录 | 无 |
| configure.ac 测试宏（AC_CONFIG_TESTDIR 等） | 无 |
| 结论 | **上游无自动化测试用例，测试入口为 automake 标准 `make check`（空目标）** |

`make check` 实际执行记录（真实构建内）：

```text
$ make -j1 check
make: Nothing to be done for 'check'.
```

统计：用例总数 0，通过 0，失败 0，跳过 0（上游无测试入口，`test_package` 不替代此统计）。
消费者验证（鸿蒙测试用例）：test_package/test.sh 以 conan 消费者身份实际执行 `wmtop -v`/`-Z`/错误参数路径/DT_NEEDED 链等 **18 项断言 + 1 条鸿蒙消费者执行用例，19 通过 / 0 失败**。鸿蒙用例为执行型（非断言）：uname 仅作运行前置 gate，用例本体端到端启动已安装的 wmtop（无参数），验证运行时共享库链完整解析、执行到 libdockapp X11 初始化并以程序自身干净的 "can't open display"（exit 1）退出；动态链接器失败（exit 127）或崩溃（exit ≥128）均判 FAIL。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `autoreconf` 报 `Can't exec ".../bin/aclocal": Permission denied`（exit 13） | OHOS 对 conan 构建树内 HMDFS 上的**脚本**拒绝 execve（最小配方探针矩阵实证：direct execve ✗、sh wrapper ✗（内层 exec 同样被拒）、`perl .aclocal-real` ✓）；解释器二进制不受限 | 弃用 autoreconf 链，`perl` 直调 `.aclocal-real`/`.automake-real` 并复刻 wrapper 的 acdir 参数 |
| 2 | `configure: error: cannot run C compiled programs`（exit 77） | `--build == --host` 使 configure 判定本地编译并运行 conftest；conftest 链接全部共享依赖，运行时找不到 `libdockapp.so.3` 等 | configure 命令内联 `LD_LIBRARY_PATH` 指向各依赖包 lib 目录 |
| 3 | 链接规则 `make: *** [Makefile:414: wmtop] Error 126`，`safe-bin/rm: /bin/bash: bad interpreter` | conanbuildenv 导出 `SHELL=/data/service/hnp/bin/bash` 并被 configure 固化进 Makefile；该 bash 经 BASH_ENV source 的 safe-bin/rm shim shebang（#!/bin/bash）不存在 | 运行 configure/make/install 时统一覆盖 `SHELL=/bin/sh CONFIG_SHELL=/bin/sh`，并把 `/system/bin`（toybox）前置到 PATH，使 `rm` 等解析到真实工具 |
| 4 | `umask 077` 导致 config.status 私有临时目录不可写（E011/E114/E129 家族） | HMDFS 强制 setgid 位并映射 owner uid，0700 目录连 owner 都不可写 | 生成好的 configure 在运行前被改写 `umask 077 → umask 022`（沿用 libdockapp 配方先例） |
| 5 | `config.guess` 无法识别 `uname -s` = HarmonyOS | 平台特性 | 显式传 `--build=aarch64-linux-ohos --host=aarch64-linux-ohos`；automake 1.18 的 config.sub 已接受 ohos 三元组，无需补丁 |
| 6 | 并行 make 挂起/失败（E074/E525 家族） | 沙箱禁止创建 jobserver FIFO | `make -j1` |

## 源码修改

无（`patches_applied: []`）。上游 `configure.ac` 的 `AS_CASE([$host_os],[linux*])` 直接匹配 `aarch64-linux-ohos`，LINUX 后端原样可用（含 `-m` 内存视图与 `/proc` 读取器）。全部 OHOS 适配在 conanfile.py 内完成。

## 依赖版本

宿主依赖（二进制均自 ohpcd 远端实拉消费）：
- libdockapp/0.7.3（其 pkg_config_name=dockapp）
- libx11/6.4.0 → libxcb/1.16 → xorgproto/2025.1 + xtrans/1.6.0 + libxau/1.0.11 + libxdmcp/1.1.5
- libxext/6.4.0
- libxpm/3.5.17

构建期工具依赖（tool_requires）：
- automake/1.18（autoconf 家族由系统 hnp 提供；wmtop 无 LT_INIT，不需要 libtool）

## 验证结果

```text
$ conan create archives/w/wmtop/0.85 -pr:h=... -pr:b=...   # EXIT=0
  make -j1        → 1 warning（_BSD_SOURCE 重定义，上游源码固有）后编译链接成功
  make -j1 check  → Nothing to be done for 'check'.（上游 0 用例）
  make install DESTDIR → bin/wmtop + share/man/man1/wmtop.1 + licenses/COPYING
  test_package    → 19 passed, 0 failed
  bin/wmtop: ELF64 / AArch64 / DYN，无 RPATH/RUNPATH
```

test_package 消费者用例（18 项断言 + 1 条鸿蒙执行用例）摘要：PATH 定位与可执行性、AArch64/ELF64 架构、`wmtop -v` 输出 `wmtop v0.85`、`-Z` usage 横幅（含 LINUX-only `-m` 行，OHOS 按 linux* 匹配）、`-a 99`/`-x`/`-disdisplay` 错误参数均 exit 1、DT_NEEDED 含 libdockapp.so/libX11.so/libXext.so/libXpm.so、无 RPATH/RUNPATH、man page 安装；鸿蒙执行用例（gated，非断言）端到端启动 wmtop 验证消费者可行性。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 配方（含 OHOS execve 限制的 perl/sh 直调自举链） |
| conandata.yml | 官方源 URL + sha256 |
| test_package/{conanfile.py, test.sh, MANIFEST.yml} | 消费者测试（19 断言，含鸿蒙用例） |
| manifest.yaml / notes.md | 元数据与知识沉淀 |
| ../commands.json | R38 CLI 工具声明（软件级） |

## 注意事项

- **原始构建日志不入库**（避免混入依赖库日志，PR 原子性）：全部日志在仓库外
  `/storage/Users/currentUser/ohc-work/wmtop-0.85/logs/`（04–21 号日志覆盖了 8 次 conan create 迭代与探针矩阵）。
- 配方的 perl/sh 直调自举链是**跨平台安全**写法（解释器调用在任何平台都合法），CI 上同样成立；不要回退到 `Autotools.autoreconf()`。
- `make check` 为空目标是上游事实，不要为凑数把 test_package 统计当成上游测试。

## 发现与知识积累

✅ OHOS 上 conan 构建树内 execve HMDFS 脚本被拒（EACCES/exit 13），解释器二进制不受限 → autoreconf 链不可用，须 perl 直调 `.aclocal-real`/`.automake-real`（显式 acdir）+ `sh <configure>`（已沉淀于本配方 `conanfile.py` 的 `_bootstrap_configure`）。
✅ `--build == --host` 时 configure 运行 conftest，须内联 `LD_LIBRARY_PATH` 指向依赖 lib 目录（buildenv_info 不落盘，内联才生效）。
✅ conanbuildenv 的 `SHELL=沙箱 bash` 会被 configure 固化进 Makefile → 统一覆盖 `SHELL/CONFIG_SHELL=/bin/sh` 并前置 `/system/bin` PATH。
✅ pkg.m4 位于 hnp pkg-config 目录，aclocal 时内联 `ACLOCAL_PATH` 注入。
✅ finish/W3 的 zsh 执行环境：cmd-pkgs release 提供 `zsh-5.9-ohos-aarch64.tar.gz`（python 解包写入 → execve 稳定），需设 `TMPPREFIX` 使 heredoc 落在可写缓存。

---

### 对话 #1（2026-09-27）

- 任务：加载编译 SKILL，目标库 wmtop 0.85，前置条件 R36 依赖消费性验证（通过：零缓存隔离 CONAN_HOME 实拉 9 包）。
- 过程：8 次 conan create 迭代定位 OHOS execve 限制并落地 perl/sh 直调自举；上游测试清点 0 用例（如实记录）；test_package 19/19（含鸿蒙执行用例）；conan-verify G0–G4 PASS；finish W2/W3 通过。
- 结果：status=published，可提交（commit `eb2920c5a8` + 归档补全后的二次修正）。
---

**编译结束**: 2026-09-27 17:13
**最终状态**: published
