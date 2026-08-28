# unixodbc 2.3.12 适配笔记

## 2026-08-28 Conan recipe 前置适配

- 分支: `feat/unixodbc-2.3.12`
- issue: `TBD`。已在本轮委托上下文、`archives/u/unixodbc/2.3.12` 和下游 `asterisk-odbc/22.10.1` 记录中查找，未发现明确 unixodbc issue 编号。
- W0 依赖检查: unixODBC 2.3.12 当前 recipe 无 Conan runtime requirements；readline/editline/drivers/driver-config/stats/iconv 等可选功能在首轮配方中关闭，避免把缺失可选依赖混入本 PR。`conan download unixodbc/2.3.12 -r=ohpcd --only-recipe` 在本机返回 `system acceleration policy not enabled`，下游仍需要本 recipe 合入/发布后再消费。
- 源码: 改用上游 GitHub release tarball，`conandata.yml` 优先尝试 `gh-proxy` 镜像并以 GitHub 原地址兜底，SHA256 `f210501445ce21bf607ba51ef8c125e10e22dffdffec377646462df5f01915ec`。该 release 包已包含 `configure`，不再依赖 GitHub API tarball + `autoreconf -fi`。
- 构建系统: Autotools；配方使用 `AutotoolsToolchain`/`Autotools`，`make -j1`，并执行 `make check`。上游 2.3.12 只有 Automake 递归 check 目标，未发现 `TESTS`/`check_PROGRAMS`，所以配方额外执行 build-tree `odbc_config --version`、`odbc_config --ulen`、`isql --version`、`odbcinst --version`。
- OHOS 适配: 新增 `patches/0007-ohos-umask-tmpdir.patch`，用 unified diff 将 `config.guess`、`configure`、`libltdl/configure` 的 `umask 077` 临时目录创建改为 `umask 022`；recipe 同时设置 `TMPDIR`/`TMPPREFIX` 指向 build 目录下的隔离临时目录。
- 打包: `make install` 后移除 `.la` 和 `bin/*`，首轮 package 只交付 `libodbc`、`libodbcinst`、`libodbccr` 与 headers；OHOS 上对包内真实 ELF `.so*` 执行 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`，跳过 symlink。CLI 仅在 build-tree 阶段作为 smoke 验证，不作为包内命令发布，避免在版本目录外新增 `commands.json`。
- test_package: 新增 `test_unixodbc.c`，真实调用 `SQLAllocHandle`、`SQLSetEnvAttr`、`SQLGetDiagRec`、`SQLFreeHandle`、`SQLGetConfigMode`、`SQLSetConfigMode`、`SQLValidDSN`、`SQLInstallerError`，覆盖下游 `asterisk-odbc` 所需的库/头文件消费路径。
- 旧补丁 `0001`-`0006` 保留为 2026-05-29 GitHub API tarball/autoreconf 手工路径的历史记录；当前 Conan recipe 只通过 `conandata.yml` 应用 `0007-ohos-umask-tmpdir.patch`。
- 新增 `.gitattributes` 固定本目录文档、recipe、测试源码、hint 脚本和补丁为 LF，避免 Windows checkout 后真机执行脚本或 patch 时遇到 CRLF 问题。

本机前置验证命令:

```powershell
python -m py_compile archives\u\unixodbc\2.3.12\conanfile.py archives\u\unixodbc\2.3.12\test_package\conanfile.py
git -C D:\harmonyos\tmp\unixodbc-2.3.12-src\unixODBC-2.3.12 apply --check D:\harmonyos\worktrees\unixodbc\archives\u\unixodbc\2.3.12\patches\0007-ohos-umask-tmpdir.patch
conan inspect archives\u\unixodbc\2.3.12
conan export archives\u\unixodbc\2.3.12
conan graph info archives\u\unixodbc\2.3.12 -s:h os=OHOS -s:h os.version=6.0 -s:h arch=armv8 -s:h compiler=clang -s:h compiler.version=15 -s:h compiler.libcxx=libc++ -s:h compiler.cppstd=17 -s:h build_type=Release
```

本轮本机结果:

- `python -m py_compile` 通过。
- `git apply --check` 对 release tarball 解包目录通过。
- `conan source` 可重新下载 release tarball 并通过 SHA256 校验；该命令会按 recipe layout 临时生成 `archives/u/unixodbc/2.3.12/src/`，本轮复核后已清理。
- `conan inspect` 通过，正确读到 source SHA、patch、options 和空 requirements。
- `conan export archives/u/unixodbc/2.3.12` 通过，plain ref recipe revision 为 `unixodbc/2.3.12#4e386d003c5eb254003a86f3edceb50d`。
- `conan export archives/u/unixodbc/2.3.12 --user=ohpcd --channel=stable` 通过，`@ohpcd/stable` recipe revision 更新为 `a18cba0c3b5b65cb222b4f2b5fe9783d`。
- 显式 OHOS graph (`os=OHOS`, `os.version=6.0`, `arch=armv8`, `clang 15`) 通过，`info_invalid: None`，dependencies 为空。
- 下游 `asterisk-odbc/22.10.1` graph 探针已能从本机 cache 解析 `unixodbc/2.3.12#4e386d003c5eb254003a86f3edceb50d`；剩余状态是 unixODBC 二进制 `Missing`，需本库先跑真机/CI 发布。
- 真机构建首轮发现 Conan patch 解析器会把 `strip: 1` 的 git-style patch 路径剥过头，导致 `0007` 无法应用；已移除 `strip`，与仓库内同类 `--- a/...` patch 写法保持一致。
- 真机 profile 中的 `CONFIG_SHELL=/data/service/hnp/bin/bash` 实际不可用；`conanbuild.sh` 会先 source recipe 的 `conanautotoolstoolchain.sh`，再 source profile 的 `conanbuildenv-*.sh`，后者会覆盖 shell 变量。recipe 已在 OHOS configure/make/install 命令层面内联 `CONFIG_SHELL`/`SHELL`/`TMPDIR`/`TMPPREFIX`，强制选择 `$HOME/usr/local/bin/bash` 或系统 `sh`。
- 真机 profile 中的 `/data/service/hnp/bin/clang`/`clang++` 同样不存在；recipe 已将 profile 提供的 compiler executable 解析为实际可执行路径，优先使用 `$HOME/usr/local/bin/clang`/`clang++`。
- `test_package` 也不能直接使用 profile compiler path；测试编译器同样带 `$HOME/usr/local/bin` 兜底，避免消费侧 smoke test 回落到不可用 `/data/service/hnp/bin/clang`。
- 上游 release tarball 的 `config.guess`/`config.sub` 为 2015 年版，不认识 `uname -s = HarmonyOS`，且不接受 `linux-ohos`；recipe 在 OHOS armv8 下显式传 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`，避免 configure 依赖 config.guess。
- `python -X utf8 scripts/pre_pr_audit.py check --repo-dir .` 提示缺 W3 `.ci-result.json`，符合本轮未占用真机的预期。
- WSL 默认发行版是 `podman-machine-default`，启动命令受 `/run/user/1000/containers` 权限问题阻塞，未形成可用 Linux Conan 验证环境。

真机/shadow CI 结果:

- 2026-08-28 14:12:10 CST 通过 SSH 在无后缀分支 `feat/unixodbc-2.3.12` 启动单包构建。
- run 目录: `/storage/Users/currentUser/ohos-test-runs/codex-unixodbc-unixodbc-2.3.12-20260828-r2-conan-20260828-141210-7300`。
- runner: 2026-08-28 14:12:11 CST 获得锁，2026-08-28 14:19:36 CST 结束，`exit-code.txt = 0`。
- package ref: `unixodbc/2.3.12#6878d8258773e5a57d6526e9b29cc5b1:01d92cf349a0dd98ff915f4bd99a04430171517f#0b26fa613ed1fdb0654f70b0075406a8`。
- test_package: 编译 `test_unixodbc.c` 并完成签名后执行成功，日志出现 `PASS: unixODBC API smoke test completed`。

后续真机/shadow CI 单包命令:

```sh
CI_PACKAGES="archives/u/unixodbc/2.3.12" zsh ci/conan/build_and_test.sh
/path/to/run-ohos-shadow-ci.sh archives/u/unixodbc/2.3.12
```

验收关注点:

- 日志只发现 `archives/u/unixodbc/2.3.12` 一个包。
- `Build Summary` 为 `Total: 1`，L0/L1 通过。
- `make check` 和 test_package 的 `PASS: unixODBC API smoke test completed` 均出现。
- L5 产物包含 `lib/libodbc.so*`、`lib/libodbcinst.so*`、`lib/libodbccr.so*`；`bin/` CLI 不随首轮库包发布。
- 合入/发布后回到 `asterisk-odbc/22.10.1` 执行 `conan graph info`，确认 `unixodbc/2.3.12` 可从制品仓解析。

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: built

## 编译步骤

### Phase 1: init-build
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build unixodbc 2.3.12 \
  --url="https://api.github.com/repos/lurcher/unixODBC/tarball/2.3.12"
```

### Phase 2: pre-build (hints 固化)
```bash
# 执行 hints/pre-build.sh
# 内容: autoreconf -fi + umask 077 → 022 修复（E011 workaround）
cd /storage/Users/currentUser/builds/unixodbc-2.3.12.work
sh archives/u/unixodbc/2.3.12/hints/pre-build.sh
```

### Phase 3: configure + make
```bash
./configure --prefix=/storage/Users/currentUser/usr/local
make -j1
```

### Phase 4: install + verify
```bash
make install DESTDIR=/storage/Users/currentUser/test-install-unixodbc-2.3.12
make install
/storage/Users/currentUser/usr/local/bin/isql --version  # → unixODBC 2.3.12
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | E011: HMDFS umask 077 权限问题 | HMDFS UID 映射导致 mktemp 创建的临时目录不可写 | hints/pre-build.sh 固化 autoreconf + sed umask 077→022 |
| 2 | GitHub tarball 无 configure 脚本 | 源码仓库不包含生成文件 | autoreconf -fi 生成 configure |
| 3 | libltdl/configure HMDFS 权限问题 | 同 E011，子模块独立 configure | pre-build.sh 同步修复 libltdl/configure |
| 4 | lt__argz 函数未定义 | 系统无 argz.h，libltdl 需编译 lt__argz.c | 正确设置 LTDL + LT_CONFIG_H 宏编译 |

## 源码修改

补丁文件（autoreconf 生成的 m4 文件更新）：
- 0001-m4-ltargz.m4.patch
- 0002-m4-ltdl.m4.patch
- 0003-m4-ltoptions.m4.patch
- 0004-m4-ltsugar.m4.patch
- 0005-m4-ltversion.m4.patch
- 0006-m4-lt~obsolete.m4.patch

修改的生成文件（通过 hints 固化）：
- configure: umask 077 → 022（通过 sed）
- libltdl/configure: umask 077 → 022（通过 sed）

## 依赖版本

- autoconf: 2.72
- automake: 1.16.5
- libtool: 2.4.7（内嵌）
- clang: 15.0.4
- make: 4.4.1

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/isql --version
unixODBC 2.3.12

$ /storage/Users/currentUser/usr/local/bin/odbcinst --version
unixODBC 2.3.12

$ ls /storage/Users/currentUser/usr/local/lib/*.so*
libodbc.so -> libodbc.so.2.0.0
libodbc.so.2 -> libodbc.so.2.0.0
libodbc.so.2.0.0 (1743296 bytes)
libodbcinst.so -> libodbcinst.so.2.0.0
libodbcinst.so.2 -> libodbcinst.so.2.0.0
libodbcinst.so.2.0.0 (444864 bytes)
libodbccr.so -> libodbccr.so.2.0.0
libodbccr.so.2 -> libodbccr.so.2.0.0
libodbccr.so.2.0.0 (465344 bytes)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libodbc.so.2.0.0 | 1.7MB | ODBC Driver Manager 主库 |
| libodbcinst.so.2.0.0 | 444KB | ODBC Installer 库 |
| libodbccr.so.2.0.0 | 465KB | Cursor Library |
| isql | 76KB | 交互式 SQL 工具 |
| iusql | 60KB | Unicode 版 SQL 工具 |
| odbcinst | 43KB | 驱动安装工具 |
| odbc_config | 27KB | 配置查询工具 |
| dltest | 117KB | 动态加载测试工具 |

## 注意事项

1. **E011 平台真理**: HMDFS 上 autotools 项目必须修复 umask 077
2. **GitHub tarball**: 需要预先运行 autoreconf -fi
3. **hints/pre-build.sh**: 必须在 configure 前执行
4. **libltdl**: 子模块同样需要 umask 修复

## 对话记录

### 2026-05-29 初始化编译

**AI**: 开始编译 unixodbc 2.3.12
**用户**: 请按照 SKILL.md 执行编译流程

### 问题诊断与解决

**问题1**: HMDFS umask 077 权限问题 (E011)
- 匹配知识图谱: E011
- 解决方案: hints/pre-build.sh 固化 autoreconf + sed umask 修复

**问题2**: GitHub tarball 没有 configure 脚本
- 解决方案: autoreconf -fi 生成 configure

**问题3**: libltdl 子模块 HMDFS 权限问题
- 解决方案: 同 E011，对 libltdl/configure 也应用 umask 修复

**问题4**: G0 干净构建验证失败
- 原因: G0 流程不支持 hints/pre-build.sh
- 解决方案: 创建 hints/g0-verify.sh 并手动验证 G0

### 编译结果

**状态**: built (G0 手动验证通过)
**产物**: libodbc.so, libodbcinst.so, libodbccr.so, isql, odbcinst 等
**验证**: isql --version → unixODBC 2.3.12 ✅
