# ticker 1.16 适配笔记

## 编译环境
- 构建系统：autotools 风格（2002 年手写 `configure` + 手写 `Makefile`，无 automake，无 config.guess）
- 目标：OpenHarmony aarch64（profile `ci/conan/profiles/ohos-aarch64`，clang 15）
- 状态：首轮工作树完成，待 HMBS 真机预检（`conan create` 尚未执行，实测数待回填）

## 上游概况
- 软件：ticker，可配置的文本滚动器，把消息在屏幕顶行/底行滚动显示（stock ticker 效果），支持 SysV 共享内存与外部程序通信换消息。
- 作者：Joey Hess（1998-2002），作者页 https://joeyh.name/code/ticker/，2014 年 orphaned，之后由 Debian QA Group 维护。
- 版本关系：作者 git（`git://git.joeyh.name/ticker`）最新 tag 为 1.10；1.11–1.16 为 Debian QA 上传（1.16：`ticket.c` 补 `Clean_Exit` 声明，修 GCC 15 FTBFS，Closes: #1097995）。包格式 3.0 (native)，因此 **Debian archive 即本版本的官方源**。
- 源码包：`ticker_1.16.tar.xz`（47356 字节），顶层 17 个条目：CHANGES、INSTALL、LICENSE.md、Makefile、README.md、autoconf/、configure、configure.ac、debian/、sysinfo-ticker、ticker.1、ticker.c、ticker.spec。
- 源码校验：sha256 `af88c0a7…09b23c69` 已用本机下载的归档逐字节核对，与 `ticker_1.16.dsc` 内 `Checksums-Sha256` 一致。
- 许可证：GPL-2+（`debian/copyright`）→ 配方 `license = "GPL-2.0-or-later"`。
- 依赖：唯一第三方依赖为 S-Lang（`configure.ac` 中 `AC_CHECK_LIB(slang, SLsig_block_signals)` 找不到即 hard error；Debian `Build-Depends: libslang2-dev`）。由仓内已适配的 `slang/2.3.3`（jedsoft S-Lang，非着色器 slang）提供，`requirements()` 精确引用。

## 配方设计（`conanfile.py`）

- `package_type = "application"`，`settings` 四元组，`validate()` 限定 Linux/OHOS（R32）。
- `generate()`：AutotoolsToolchain + AutotoolsDeps。OHOS 时追加 `--target=aarch64-unknown-linux-ohos`（照抄 `slang/2.3.3` 的 E001 做法）；全平台追加 `-Werror=implicit-function-declaration`（`tal/1.9` 先例：musl 在严格 ANSI 下隐藏 POSIX 声明，隐式声明会把 64 位指针截断，编译期直接拦下）。
- `build()`：**源码内构建**——上游 `Makefile` 没有 VPATH，out-of-source 找不到 `ticker.c`。`sh configure --prefix=<package>`（显式 `sh`，不依赖 configure 的 exec 位：cronic 笔记，HMDFS 的 exec 位不可靠），然后 `make -j1`（HMDFS 无 FIFO jobserver，保持串行，E074/E525）。编译器与 slang 的 `-I/-L/-l` 全部来自 `conanbuild` 环境（R33，无裸 `${CC}`）。
- 上游测试接入（R51）：`build()` 末尾运行 `debian/tests/control` 的唯一命令 `./ticker -h`（`LD_LIBRARY_PATH` 指向 conan slang 产物；跨架构时经 `qemu-aarch64`，与 `tal/1.9` 同一 helper），把输出落盘后断言含 `Usage: ticker`（退出码 0 不算证明：ticker 多条路径打印用法后都 exit 0），据此输出 `HMBS_UPSTREAM_TEST_RESULT`（discovered=1，单一确定来源，无字符串数数修补）。
- `package()`：直接 `copy()`（`tal` 先例）：`bin/ticker`、`share/man/man1/ticker.1`、`licenses/LICENSE.md`。不用 `make install`（避开真机 `install(1)` 是否存在的问题）。`sysinfo-ticker`（perl 演示脚本，死循环 + 依赖 `uptime`）不打包。
- `package_info()`：`bindirs=["bin"]`，`lib/includedirs` 置空（纯应用）。
- 补丁：无（1.16 已含 GCC 15 声明修复；`patches/` 按“无则不创建”省略）。

## 上游测试清点（R51）

| 项目 | 结论 |
|---|---|
| `test/`、`tests/` 目录 | 无 |
| Makefile `check`/`test` 目标 | 无（仅 all/ticker/demo/distclean/clean/install/configure/config.status/makeinfo） |
| 官方测试声明 | `debian/tests/control`：`Test-Command: ticker -h`（Restrictions: superficial） |
| 上游测试总数 | **1**（口径 auto：单一 autopkgtest 命令） |

## 适配后测试统计

| 用例 | 断言 | 说明 |
|---|---|---|
| `test_ticker.sh`（3） | `-h` 退出 0 且含用法横幅（即上游同命令）；`--help` 同理；无参数输出 `Must specify a message`（负向；上游此路径仍 exit 0，故断言文本） | 全部在 `Parse_Params()` 内退出，不触终端，headless 可跑；输出非空断言 + 缺二进制立即 FAIL，符合“证伪”要求 |
| `test_ticker_ohos.sh`（鸿蒙特有，2） | `readelf -h` 为 AArch64；`readelf -d` NEEDED 含 `libslang` | 纯文件检查，证明交叉编译产物与 Conan 依赖链（非宿主库） |
| 合计 | 5 个断言，`SUMMARY: pass=N fail=M` 为唯一计数源，驱动据此输出 `HMBS_TEST_PACKAGE_RESULT`（discovered=5） | 脚本非 0 即整体 FAIL，不会静默跳过；破坏性反向（L1e，产物移走）下脚本因找不到二进制而 FAIL，满足 R34 |

滚动主循环（`Init_Screen()` 之后）需要真实终端，headless 运行器无法执行，未纳入自动化，已在 PR 正文如实说明。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | Windows 本机 `git checkout upstream/main` 失败：`invalid path 'archives/g/gama/2.29/patches/0002-dataparser-ungated.patch??'` | 该文件名尾带 `\r\r`，Windows 非法 | 稀疏检出（`.git/info/sparse-checkout`，本地生效，不进版本控制）：仅检出 `SKILL.md`、`docs/`、`templates/`、`knowledge/`、`.gitcode/`、`ci/`、`archives/t/`、`archives/_index.yaml`；完整检出在 HMBS Linux 侧不受影响 |
| 2 | 上游仓库不明（任务未给） | ticker 有多个同名项目（Go 股票终端、ticker-cxx 等），版本号 1.16 指向 Debian 系 | 经 Debian changelog/Ubuntu 包页定位到 Joey Hess ticker 的 Debian native 包 1.16；作者 git 只到 1.10，Debian archive 为本版本官方源 |
| 3 | 出站网络到 `deb.debian.org`/salsa 的 https 被拦截 | 沙箱网络限制（git 协议与部分 https 镜像可用） | 经 `ftp.osuosl.org`（Debian 官方镜像）取 `.dsc` 得 SHA256，并下载归档逐字节验签；配方仍写官方 `deb.debian.org` URL（CI 会自动加镜像回退）。若真机下载超时，按守则下一轮把 `conandata.yml` 改为 URL 列表（osuosl 镜像在前，官方在后，校验值不变） |
| 4 | 构建期依赖 slang 是否已发布（R36） | 仓内 `archives/s/slang/2.3.3` 即 S-Lang，但本机禁跑 conan，无法 `conan download` 验证 | 配方精确 `requires("slang/2.3.3")`；发布状态待真机预检 L0i 裁定。若未发布，需先走 slang 发布（届时如实上报 `dependency_missing`，不伪造） |

## 依赖版本

- `slang/2.3.3`（唯一第三方依赖，精确引用）。W0 发布检查待真机 L0i。

## 验证结果

- 首轮：工作树完成，未执行 `conan create`（本机禁跑 conan；真机预检由 HMBS 在本轮结束后自动执行）。
- 待回填：`conan create` 日志中的上游 1/1 与新增 5/5（以真机实际输出为准，不得抄本笔记的期望值）。

## 对话记录

### 对话 #1 — 2026-10-13
- 同步上游 main（`e44a437b7`），建分支 `feat/ticker-1.16`；Windows 非法文件名改用稀疏检出。
- 定位上游：Debian native 包 1.16，`.dsc` 取 SHA256 并对归档验签。
- 确认 `slang/2.3.3` 即所需 S-Lang；`debian/tests/control` 即上游测试（1 个）。
- 完成配方全套（conanfile/conandata/manifest/notes/test_package/软件级 manifest+README+commands.json）与 PR 正文草稿，保持未提交，待真机预检。

### 2026-10-13 preflight compile fix (round 1)
- 真机失败：configure[157] /data/service/hnp/bin/bash inaccessible（profile buildenv 硬编码 CONFIG_SHELL/SHELL，当前 runner 缺失该路径；configure 第152行 exec CONFIG_SHELL 失败）。
- 修复：generate() 新增 Environment hmbs_shell 强制 SHELL/CONFIG_SHELL=/bin/sh（c-client/2007f 先例）；build() 同步 os.environ 并在 sh configure 命令前显式 CONFIG_SHELL="/bin/sh" SHELL="/bin/sh"；test_package 新增 _shell() 按 CONFIG_SHELL/SHELL//bin/sh/sh 顺序解析可用 Bourne shell，不再硬编码 bash。

### 2026-10-13 preflight compile fix (round 2)
- 真机失败：`checking for gcc... /data/service/hnp/bin/clang` 后 `C compiler cannot create executables`（Error 77）。
- 修复：`conanfile.py` 新增 `_resolve_compilers()`（profile 钉死路径先做存在+可执行+`--version` 探测，通过则零改动直接用；不通过则按同目录兄弟+PATH 回退 `clang`/`clang++`，全空则报明示环境故障；仅覆盖 CC/CXX，不碰 CFLAGS/LDFLAGS）+ `_dump_configure_failure()`（失败时转储 `config.log` 尾部与编译器 `--version` 上下文）；`build()` 改为 `CC=<resolved> CXX=<resolved> CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh configure` 与 `make -j1 CC=<resolved>` 显式传入，避免 conanbuild 内坏 CC 透传。

### 2026-10-13 preflight compile fix (round 3)
- 真机失败：`checking whether we are cross compiling... configure: error: cannot run C compiled programs. If you meant to cross compile, use --host`（Error 1；上一轮编译器回退已让构建从 Error 77 推进到可链接，自检运行阶段才失败，非原样重复）。
- 根因：2002 年手写 configure 无 config.guess/CANONICAL_HOST，默认 `cross_compiling=no`；OHOS clang 产出的目标二进制在构建宿主上无法直接执行，run 自检必然失败。
- 修复：OHOS 时 `build()` 以 `--host=aarch64-unknown-linux-ohos`（不传 `--build`，使 cross=maybe，运行失败自动转为 cross=yes 而非硬错误）调用 configure；保留上一轮编译器探测回退与 config.log 转储。

### 2026-10-13 preflight compile fix (round 4)
- 真机失败：config.status[695] can't create ./confVfXi7L/subs1.awk: Permission denied -> could not setup config files machinery（compile 阶段，HMBS 平台诊断 unsafe_local_mktemp，local_mktemp=1/chmod=0）。
- 根因：configure 内 stock autoconf AS_TMPDIR 先走 `(umask 077 && mktemp -d ./confXXXXXX)`，HMDFS 上 mktemp 建出的目录后续不可写；mkdir 回退同样带 umask 077（setgid+077 对属主不可写），故 subs1.awk 写入失败。已用 .hmbs/ticker-1.16/configure 实物核对：umask 077 x2、mktemp -d x1，与 tta/2.2 补丁 0003 上下文一致。
- 修复：conanfile 新增 _patch_autoconf_tmpdir()（OHOS 时 build() 调用）：把 mktemp -d 中性化为 false 恒走 mkdir 回退，并把 umask 077 全改为 022（tta/2.2 patch 0003 先例；不用 PATH mktemp shim，因本机 HMBS_CAP_CHMOD=0 无法 chmod+x）；configure 命令加 umask 022 前缀。Linux 分支保持原样。

### 2026-10-13 preflight compile fix (round 5, config.h.in)
- 真机失败（与上轮不同阶段）：上轮 mktemp 补丁生效后，config.status 依次创建 makeinfo/slang.h，随后死于 `error: cannot find input file: config.h.in`（build() line 246）。
- 根因：1.16 Debian native 包内 configure.ac 与作者仓库完全一致（含 AC_CONFIG_HEADER(config.h)），但 tarball 顶层与 autoconf/ 均缺 config.h.in（仅有 makeinfo.in/slang.h.in），属上游打包遗漏；config.status 按 :H 规则默认找 config.h.in 必然失败。已用 .hmbs/ticker-1.16（缺）与 .hmbs/upstream-ticker/config.h.in（有，46 行）实物核对。
- 修复（新策略，非重复上轮）：conanfile 内嵌作者仓库 config.h.in 全文为 _CONFIG_H_IN，build() 在 configure 前调用 _ensure_config_h_in(src)，缺失时写回源码树（存在则不动）；覆盖全部 AC_CHECK_HEADERS/FUNCS 宏，与 1.16 configure.ac 的检查集合一致。
