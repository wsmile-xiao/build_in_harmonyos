# mkcue 1 适配笔记

## 编译环境
- 构建系统: autotools（随包分发预生成 `configure` + 手写 `GNUmakefile.in`；仅需 GNU make）
- 编译日期: 2026-10-04
- 编译器: clang / clang++ 15.0.4（OHOS SDK；`/data/service/hnp/bin/clang`，target `aarch64-unknown-linux-ohos`）
- 目标: `os=OHOS`、`arch=armv8`、`aarch64-unknown-linux-ohos`、`compiler=clang`、`libcxx=libc++`
- 状态: built（配方已就绪；真机 rule4 预检尚未在本轮执行，待 HMBS 后台验证后回填实测数字）
- 依赖: **0 个第三方依赖**（链接行 `mkcue.o mb.o`，无 `-l`）
- 目录-产物分离：任务目录 `archives/m/mkcue/1` 保持单字符上游标签 `1`（分支 `feat/mkcue-1`），产物 ref 为 `mkcue/1.0`（`set_version()` 映射；Conan 单字符版本导出限制，先例 `cutmp3/4->4.0`、`cvechecker/4->4.0`）
- 与 `archives/m/mkcue/1.0` 的关系：`1.0` 为 2026-09-29 已发布归档（前 HMBS 门禁 epoch）；本目录 `1` 为同一上游按当前房式（单字符目录 + `set_version`）与当前 HMBS rule4 机器证据要求重述的配方，补丁与源码锚定完全一致，测试证据改为 rule4 可解析的 `RESULT`/`HMBS_*` 标记

## 源码信息
- 上游：Eric Gillespie（`epg@pretzelnet.org`），分发点 `https://diplodocus.org/`
- 上游只有 **Subversion** 仓库（`svn+ssh://diplodocus.org/svn/projects/release/mkcue-1/`），**无公开 git 仓库、无 commit SHA**；2005 年后未再发布新版本
- 源码：Debian 官方主归档 `https://ftp.debian.org/debian/pool/main/m/mkcue/mkcue_1.orig.tar.gz`
  - sha256 `2aaf57da4d0f2e24329d5e952e90ec182d4aa82e4b2e025283e42370f9494867`
  - size 80650 bytes，Last-Modified 2005-08-11，与 Debian 源包 `1-9.dsc` 的 Checksums-Sha256 一致
- 许可证：LGPL-2.1-or-later（上游 `COPYING` 为 LGPL-2.1；`README` 文字写作 "GNU GPL"，以 `COPYING` 为准）

## 上游测试审计（上游无测试）
- tarball 文件清单无 `tests/`、`t/`、无 `*.test`；`GNUmakefile.in` 构建目标仅 `all / mkcue / clean / maintainer-clean / install / dist`，无 `check`/`test` 目标
- `configure.ac` 中 `test`/`check` 字样仅为 `AC_CHECK_SIZEOF` 与注释，非测试目标
- Debian `debian/rules` 只做 `dh` 标准流程，无 `dh_auto_test`/`TEST_TARGET`
- 结论：上游确无自动化测试 → `test_package/MANIFEST.yml` 置 `upstream_tests_exist: false` 并附 `upstream_test_audit`，`upstream_test_total: 0`（口径 `autotools_tests`）；`test_package` 对打包二进制做 9 条消费端校验，不冒充上游覆盖

## 编译步骤

```sh
# 1. 源码（canonical 版本 1）
curl -LO https://ftp.debian.org/debian/pool/main/m/mkcue/mkcue_1.orig.tar.gz
sha256sum mkcue_1.orig.tar.gz
# 2aaf57da4d0f2e24329d5e952e90ec182d4aa82e4b2e025283e42370f9494867

# 2. 补丁（5 枚，见 patches/，与 1.0 逐字一致）
# 3. 交叉编译（Conan 驱动）
conan create . --name=mkcue --version=1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 产物 ref 为 mkcue/1.0（set_version 映射）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./build/config.guess` → `unable to guess system type` | 2002 版 config.guess 无 HarmonyOS 分支；`uname -s` = `HarmonyOS` 不匹配任何已知系统 | `0002-build-config.guess.patch`：插入 `*:HarmonyOS:*:*` 分支，输出 `aarch64-unknown-linux-ohos`（E007） |
| 2 | `./build/config.sub aarch64-linux-ohos` → `machine not recognized` | 2002 版 config.sub 既不认 `aarch64`/`arm64`，也不认 `linux-ohos` | `0003-build-config.sub.patch`：CPU 列表加 `aarch64`/`arm64`；`maybe_os` 加 `linux-ohos*`（E007/E072） |
| 3 | `config.status: can't create ./confstat*/subs.sed: Permission denied` | HMDFS 目录属主 UID 映射，`umask 077` 的 0700 目录不可写 | `0004-configure.patch`：`umask 077` → `umask 022`（E011/E110/E052） |
| 4 | VPATH 构建下 `fatal error: 'diskid.h' / 'mb.h' file not found` | 手写 `GNUmakefile.in` 非 VPATH-clean：`AC_LINK_FILES` 生成物在 build 目录，头文件在 source 目录，双向互含 | 不改上游 Makefile，`generate()` 追加 `-I<source_folder> -I<build_folder>`（R33） |
| 5 | `diskid.h:64: error: reference to 'byte' is ambiguous`（C++17） | `using namespace std;` + 全局 `typedef unsigned char byte;` 与 `std::byte` 冲突 | `0005-diskid.h.patch`：重命名为 `byte_t` |
| 6 | `make install` → `No such file or directory` | install 规则依赖目标目录已存在，但从未使用 `INSTALL_DIR` 变量 | `0001-GNUmakefile.in.patch`：补 `${INSTALL_DIR} ${DESTDIR}${bindir}` |
| 7 | Windows 本地无法完整检出上游树（`archives/g/gama/...patch\r\r` 文件名含回车） | 上游某补丁文件名以 `\r\r` 结尾，Windows `CreateFile` 报 `EINVAL` | 本地用 sparse-checkout 排除 `archives/g/gama/` 后 `checkout-index` 恢复工作树（`core.protectNTFS=false` 使 `read-tree` 可入索引，`skip-worktree` 跳过坏文件）；真机为 Linux 不受影响（先例 `cvechecker/4` notes #11 同款） |
| 8 | Conan 预检 `configure: error: cannot run .../build/config.sub`（第 1 轮） | 初步怀疑 Conan 四段式 triplet 被 2002 版 config.sub 拒识 | `generate()` OHOS 时钔三段式 `--build/--host=aarch64-linux-ohos`，`build()` 增加探针；真机证明探针 `sh config.sub aarch64-unknown-linux-ohos rc=0` 但 configure 仍失败，证伪三段式假设，已回滚钔定 |
| 9 | 同错误持续：探针 rc=0 但 `cannot run /data/service/hnp/bin/bash .../build/config.sub` 仍然（第 2 轮） | 问题在 SHELL 二进制本身而非 triplet 校验：profile `[buildenv]` 注入 `SHELL/CONFIG_SHELL=/data/service/hnp/bin/bash`，configure 内部 `$SHELL config.sub` 调用失败，而 `sh config.sub` 成功 | 取消三段式钔定（回到 Conan 默认四段式，探针已证明可接受）；`generate()` 用 `Environment.save_script("mkcue_shell")` 将 `SHELL/CONFIG_SHELL` 覆写为 HMBS 注入的 `/bin/sh`（recipe 脚本后于 profile buildenv 生效）；探针改为单行汇总同时测 profile-bash 与 sh 邓断下轮 |
| 10 | 同错误第三次：`save_script` 无 scope 不生效，configure 仍用 profile-bash 失败 | 上一轮 `env.vars(self).save_script` 缺省 scope 落入 runenv（conanrun.sh），configure 读取的 conanbuild.sh 未被覆盖；探针 iron 证据：`/data/service/hnp/bin/bash+*` 全为 `FileNotFoundError(2)`，`/bin/sh+*`/`sh+*` 全 rc=0 | 改 `scope="build"`（zydis 先例 `save_sh` 同口径）并在 `build()` 以 `os.environ` 双保险导出 `SHELL/CONFIG_SHELL=/bin/sh`（4ti2 先例经 `os.environ` 设 `CONFIG_SHELL`） |

## 依赖版本

| 依赖 | 版本 | 类型 | 实测 |
|------|------|------|------|
| （无第三方依赖） | — | — | 链接行无 `-l`，仅 libc / libstdc++ / 内核头 |
| GNU make | 4.4.1（基环境自带） | 构建工具链基础件 | 配方不声明，由真机环境提供 |
| clang / clang++ | 15.0.4（OHOS SDK） | 编译器基础件 | profile `ohos-aarch64` 指定 |

## 验证结果（待真机预检回填）
- 本轮为首轮工作树搭建，未执行 `conan create` 真机预检（按任务守则由 HMBS 后台统一验证）
- `test_package` 设计为 9 例（6 例上游行为 + 3 例鸿蒙平台），脚本输出确定性 `RESULT: P passed, F failed` 行，`conanfile.py` 由此解析出 `HMBS_TEST_PACKAGE_RESULT`（`discovered`/`passedCount` 唯一来源即该行，不做字符串数数或算术修补）
- 上游测试：`HMBS_UPSTREAM_TEST_RESULT` 为 `status:"no_tests"`、`discovered:0`、`executed:0`（审计见 `test_package/MANIFEST.yml`）
- 证伪安排（真机轮执行）：确认测试输出非空；负向对照（未知选项 `-x` 必 exit 2 且打印 usage）证明 harness 能抓真失败；`passed+failed==executed`、`executed<=discovered` 自检在 `conanfile.py` 内完成，不满足则抛异常而不凑数字
- 真机通过后回填 `conan create` / `test_package` 实测数字到 PR 正文

## 注意事项
- 源码 `.cc/.cpp` 业务逻辑零改动；`<linux/cdrom.h>` 由 OHOS SDK sysroot 提供
- TOC 读取 happy path 需真实光驱，不可测，已如实记录，未伪装通过
- 本配方未改动 `knowledge/`、`ci/`、`templates/` 等框架路径；单 PR 只含 `archives/m/mkcue/1/` 一个版本目录

**编译结束**: 2026-10-04（工作树；真机验证待 HMBS 后台执行）
**最终状态**: built

| 11 | configure 首错变为 \`C++ compiler cannot create executables\`（Error 77），config.sub/SHELL 已通过 | 前三轮 SHELL 假设已证伪方向：本轮日志 build/host 均为 aarch64-unknown-linux-ohos 且无 cannot run config.sub，说明 configure_args SHELL=/bin/sh 生效，失败点后移到编译器自检 | build() 改走编译器临时文件路线：TMPDIR 真实写入探测（HOME/tmp 与 build_folder/.tmp 回退，coinor-vol 先例）+ chmod 容错 + configure 失败时转储 config.log 尾部与 CXX --version 探针，下轮按 config.log 首错定点 |
| 12 | configure仍Error 77但探针Nightly证明CXX=/data/service/hnp/bin/clang++不存在（FileNotFoundError），TMPDIR已为注入可写路径 | 上轮TMPDIR假设证伪：日志TMPDIR probe已using注入路径，失败仍在且compiler probe直接报驱动缺失，根因是profile写死的CI路径在preflight worker不存在 | generate()新增真实驱动发现（which+env+SDK llvm/bin glob+profile兜底）并以CC/CXX configure实参覆盖（沿用SHELL实参免疫路线），build()复用发现做版本探针与PATH记录 |
| 13 | make成功后`make install`在首条安装规则`GNUmakefile:76: <pkg>/bin/mkcue] Error 64`（EX_USAGE）中断，已打印命令为`.../bin/install -c -m 755 -d <pkg>//bin` | 与编译器/SHELL/TMPDIR均无关，属安装工具能力层：AC_PROG_INSTALL把HMBS/OHOS `install` shim（仅接受单文件双参，`[ $# -eq 2 ] \|\| exit 64`）烘焙进INSTALL/INSTALL_PROGRAM/INSTALL_DIR，`install -c -m 755 [-d]`分离参数形式必挂（zurl #35、cvechecker/4 #9、postgresql-18.3 `cp: bad '755'`同族）；0001补的INSTALL_DIR mkdir行首当其冲 | 配方侧规避（不改上游安装语义）：package()新增`_redirect_install_to_bundled_install_sh()`，把生成树GNUmakefile/Makefile的INSTALL/INSTALL_PROGRAM/INSTALL_DATA/INSTALL_SCRIPT/INSTALL_DIR/MKDIR_P重定向到tarball自带`build/install-sh`（AC_PROG_INSTALL标准兜底，正确处理`-c/-m/-d`），再`autotools.install(args=["SHELL=/bin/sh"])`；打包二进制chmod加容错（HMBS_CAP_CHMOD=0） |
