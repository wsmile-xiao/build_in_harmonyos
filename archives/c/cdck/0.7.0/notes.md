# cdck 0.7.0 适配笔记

## 编译环境

- 构建系统: autotools（预生成 configure + Makefile.in，不做 autoreconf）
- 编译日期: 2026-09-09
- 编译器: clang/clang++（OHOS 真机 /data/service/hnp/bin）
- 状态: built（待真机预检，未提交）

## 编译步骤

```bash
# 标准 Autotools 流程（conan create 内执行，VPATH 构建）
./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu
make -j1
# 上游无 make check 目标（automake 默认空目标，零用例），如实声明 no_tests
# package() 不跑 make install，直接复制 build 树中找到的 cdck ELF 到 bin/
```

- `linux/cdrom.h` 由 OHOS 工具链提供，`lib_cdinfo.cpp` 无条件包含它，无需补丁（cd-discid 先例：同头文件在 OHOS 可用）。
- configure 的 perl 版本探测缺 perl 时降级为跳过（补丁 0002），gcc 版本探测同步跳过。
- `SUPCXX` 按 `$CC -print-file-name=libsupc++.a` 解析，仅保留真实存在的绝对路径；clang 下自动清空，改走 libc++。
- C++ 链接器由 `$(CC)` 改为 `$(CXX)`（补丁 0003），否则 clang 驱动链接 C++ 产物缺运行时。
- `make all` 会进 man/ 子目录构建 `cdck.1`（需 pod2man）；真机无 pod2man 时预建最小 `cdck.1` 使该规则成为 no-op，二进制不受影响。
- libtool 1.5 链接的 `src/cdck` 是包装脚本，真 ELF 在 `src/.libs/cdck`；`package()` 按 ELF 魔数查找，优先 `.libs` 路径。
- 二进制行为（源码 `src/cdck_main.cpp` 实测语义）：
  - `cdck -V` → `Simple CD/DVD check program, ver 0.7.0. ...`，exit 0（不碰硬件）
  - `cdck -h` → Usage 说明，exit 0（不碰硬件）
  - `cdck -d /dev/不存在的设备` → `Unable to read TOC because ...`，exit 1（open 失败即返，无等待）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.sub` 报 `invalid configuration 'aarch64-...'` | 自带 config.sub 时间戳 2001-09-07，无 aarch64 CPU、无 linux-ohos 系统 | 补丁 0001 同步加 CPUs 的 `aarch64` 与两处 OS 模式的 `linux-ohos*`（aalib/1.4p5 同年代包先例） |
| 2 | 无 perl 时 configure 直接 `exit 1`；有 perl + clang 时仍跑 2001 版 gcc 版本探测（`exec 15>`）在 OHOS `/bin/sh` 下 `configure[9073]: 15: inaccessible or not found` exit 127 | `configure.ac` 要求 perl 5+ 做 gcc 版本探测；真机仅保证 cmake/make/ninja/python3；2001 探测的 fd 15 写法与 OHOS shell 不兼容且对 clang 无意义 | 补丁 0002：缺 perl 时打印提示继续，gcc 版本探测同步跳过；且 `case "${CC:-}" in *clang*)` 时强制跳过版本探测（已装 perl 也跳过），只保留 gcc/Linux 原路径 |
| 3 | `SUPCXX=\`gcc ...\`` 在 clang 环境错误 | 硬编码 gcc；clang 无 libsupc++.a | 补丁 0002：改按 `$CC` 解析，非绝对路径或文件不存在即清空 |
| 4 | 链接 C++ 程序用 `$(CC)` | `src/Makefile.am` 的 CXXLINK 继承上游写法；clang C 驱动不带 libc++ | 补丁 0003：CXXLINK 改用 `$(CXX)`（`.am` 与 `.in` 同改，不跑 automake） |
| 5 | `make all` 卡在 `pod2man` | man/Makefile 的 `all-am: Makefile $(MANS)`；真机无 pod2man | 有 pod2man 则正常构建；否则预建最小 `cdck.1` 使规则跳过，且 `package()` 不安装 man 页 |
| 6 | 发布包自带 `src/config.h` | maintainer 机器生成的旧头文件会遮蔽 configure 产物（quoted include 优先命中源码树） | `source()` 中删除（cdecl/18.7.2 先例），以 configure 生成为准 |
| 7 | 上游下载只有 HTTP 且单源易截断（真机 `Signal 9` + `gzip: stdin: unexpected end of file`） | `swaj.net` 不提供 HTTPS（实测 https 握手超时）；Debian/Gentoo 同用该 http 源；单 http 慢源下载截断即解包失败 | 保留官方 http 单源为回退 + sha256 锁定（240285 字节，与 Gentoo DIST 一致），首选 Gentoo distfiles HTTPS 同文件镜像（`https://distfiles.gentoo.org/distfiles/cdck-0.7.0.tar.gz`，Gentoo Manifest 同尺寸 240285，校验值不变，conan 按序重试），如实记录为例外 |
| 8 | 真机 `"/data/service/hnp/bin/clang" inaccessible or not found`（`--version` 探针 Error 127） | 仓库 `ci/conan/profiles/ohos-aarch64` 把 `tools.build:compiler_executables` 写死为该路径，真机镜像已移除；配方此前无条件信任该值 | 配方内动态解析：conf 路径仅在文件存在时采用，否则用 `shutil.which("clang")`/`clang++`（HMBS 已把活动工具链前置到 PATH，juise/xz/fastconstmap 先例）；同时剥离 toolchain 回传的 stale `CC=/CXX=`，configure/make 均显式 `CC="real" CXX="real"` 覆盖；不碰共享 profile |
| 9 | 0002 补丁的 clang 条件跳过未生效：新预检仍在未后移的 `configure[9073]` 报 `15: inaccessible or not found`（exit 127） | 补丁同步/命中位置依赖预检代码树状态；且 2001 探测的 perl gcc 版本解析本就认不出 clang 版本串，即使修好 fd 语法也可能判旧编译器 | 改用不同策略：配方 `build()` 在补丁之后用 Python 无条件摘除整个版本探测块（`checking version of`→`rm -f ./.gcc.test` 一次性正则替换，嵌套 if/fi 不可能失衡；未命中时回退只修两处 fd-15 写法）；不依赖 CC 取值与补丁同步时序 |
| 10 | 真机 `config.status` 报 `can't create .../tmp/csXXX/out: Permission denied` 后 `make: No targets specified and no makefile found`，`HMBS_PLATFORM_CAPABILITIES` 为 `hardlink:0,chmod:0,local_mktemp:1` 并伴随 `[readonly_tmp]/[unsafe_local_mktemp]` 诊断 | HMDFS 上 `mktemp -d` 建 0700 目录因 UID 映射不可写（E011/E206）；且配方曾把 `HMBS_AUTOCONF_MKTEMP_FALLBACK=1` 标志误当路径使用 | 配方内最小适配：`_resolve_hmbs_tmp` 只接受绝对路径（`0/1//tmp` 不再当路径）；`HMBS_AUTOCONF_MKTEMP_FALLBACK=1` 时仅 configure 阶段用 PATH 前置 shim 使 `mktemp -d` 失败走 autoconf `mkdir` fallback（其余 mktemp 透传）；`configure` 与生成的 `config.status` 内 `umask 077` 放宽为 `umask 000`；Makefiles 缺失时重跑一次 `./config.status`；不跳过任何测试 |
| 11 | 上轮修复后 configure/编译通过，但 `make all` 在 `man/` 子目录失败：`pod2man ... cdck_man.in > cdck.1` 报 `Can't open cdck_man.in`（`Makefile:291: cdck.1 Error 2` → `all-recursive Error 1`） | VPATH 构建：`pod2man` 真机存在故旧逻辑直接放行，但 recipe 用裸文件名 `cdck_man.in` 在 build 目录执行，而该文件只在源码树，旧逻辑仅覆盖 pod2man 缺失场景 | 与上轮不同策略：pod2man 存在时把源码树 `cdck_man.in` 复制到 build `man/` 目录使真实手册页可构建；源码 `.in` 仍缺失时回退预建最小 `cdck.1`；`package()` 始终不装 man 页，二进制交付不受影响 |
| 12 | VPATH 修复后 `make all` 仍在 `man/` 失败：`cdck_man.in around line 1: =cut found outside a pod block` + `POD document had syntax errors`，`pod2man` exit 255 → `Makefile:291: cdck.1 Error 255` → `all-recursive Error 1` | 上游 `man/cdck_man.in` 首行为无前导 `=pod` 的孤立 `=cut`；2001 年老 pod2man 仅警告放行，真机新版 Perl/pod2man 直接判错；非 VPATH 问题，文件已找到但内容被拒 | 双层修复：补丁 0004 删除首行孤立 `=cut` 使 POD 合法（真实手册页可构建）；`build()` 同步把 build 树 `man/Makefile` 的 pod2man recipe 改写为 `... \|\| (echo 最小 TH > cdck.1)`，未来 pod2man 再变严格也只回退占位页、不再卡死构建；`package()` 仍不装 man 页，不跳过任何测试 |

## 源码修改

| 补丁 | 内容 |
|------|------|
| `patches/0001-config.sub-ohos.patch` | config.sub 加 `aarch64` CPU 与 `linux-ohos*` 系统模式 |
| `patches/0002-configure-ohos-perl-supcxx.patch` | configure 缺 perl 可继续、gcc 版本探测可跳过、SUPCXX 按 $CC 条件解析 |
| `patches/0003-src-makefile-cxxlink.patch` | `src/Makefile.am` 与 `src/Makefile.in` 的 CXXLINK 改用 `$(CXX)` |
| `patches/0004-man-pod-cut.patch` | `man/cdck_man.in` 删除首行孤立 `=cut`（新版 pod2man 判 exit 255），其余 POD 不动 |

无平台宏污染：补丁均为 POSIX 兼容写法，未引入 `__OHOS__`（R8/PF5 合规）。

## 依赖版本

无外部依赖（仅 libc + 内核 `linux/cdrom.h` + 工具链 libc++）。`requirements()` 为空。

## 上游测试审计

- 源码包 43 个文件：无 `tests/`、`test/` 目录，无 `*test*` 源文件。
- `Makefile.am`（顶层/src/man）仅定义 `SUBDIRS`、`lib_LTLIBRARIES`、`noinst_LIBRARIES`、`bin_PROGRAMS`、`man_MANS`；无 `TESTS`、`check_PROGRAMS`、`check` 目标。
- `configure.ac` 仅做编译器/头文件探测与 perl 版 gcc 版本检查；无测试框架注册。
- Debian/Gentoo 下游打包均不运行任何测试。
- 结论：上游 0.7.0 无自动化测试。`build()` 输出 `HMBS_UPSTREAM_TEST_RESULT`（`status: no_tests`，discovered/executed 均为 0 及本审计原因）；`test_package` 每轮重发该标记（缓存命中可验证）。

## 验证结果

```bash
# test_package 4 个真实用例（test.sh，经 conanrun 运行安装后的 bin/cdck）：
# 1. 二进制存在且可执行
# 2. cdck -V → 含 0.7.0，exit 0
# 3. cdck -h → 含 Usage:，exit 0
# 4. cdck -d /dev/nonexistent-cdck-test-device → 含 Unable to read TOC，exit 非零
# 通过率以真机预检日志的 HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT 为准，
# 本轮未提交，待 HMBS 后台完整验证后回填。
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/cdck` | 命令行可执行文件（ELF，aarch64） |
| `licenses/COPYING` | 上游 GPL-2.0-or-later 许可证文本 |

## 注意事项

- 本机为 Windows + 光驱无关环境，未在本地运行 conan 构建；一切编译与测试结论以 HarmonyOS 真机预检为准。
- 光盘实际读写/计时功能需真实光驱硬件，沙箱与 CI 均无法覆盖；测试仅覆盖版本、帮助与设备错误三条确定性路径，不伪造硬件测试结果。
- `conandata.yml` 使用 http 源是上游限制（无 HTTPS），非选型疏漏；校验值 sha256 与 Gentoo 归档尺寸双重锁定。
