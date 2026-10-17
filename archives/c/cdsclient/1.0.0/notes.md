# cdsclient 1.0.0 适配笔记

## 编译环境
- 构建系统: autotools (configure + make，预生成 configure 随包发布，无需 autoreconf)
- 编译日期: 2026-08-24
- 编译器: clang 15 (AutotoolsToolchain 注入)
- 状态: built

## 编译步骤

1. 源码获取: `get()` 下载 CDS 官方 tarball
   `https://cdsarc.cds.unistra.fr/ftp/pub/sw/cdsclient-4.07.tar.gz`
   (sha256 4a0a02cb1dc48bc9a0873ebb3ef9b031f9288baf13a3573f885a8504f9c317c5，
   本机与真机实测校验一致)
2. 配置: `autotools.configure()`（AutotoolsToolchain 注入 clang 工具链与 OHOS 环境）
3. 编译: `make -j1`（hmbs 注入 tools.build:jobs=1，配方显式 -j1）
4. 安装: `autotools.install()`（DESTDIR 模式）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `working directory cannot be determined` | HMFS/HMDFS 不支持 getcwd，`pwd` 失败，configure 的 `ac_pwd=`pwd`` 直接报错 | build() 顶 `os.chdir(build_folder)` + `os.environ["PWD"]=build_folder`；补丁 0001 改写 configure 的 ac_pwd 为 `pwd 2>/dev/null || ac_pwd="$PWD"` 兜底（同 aribb24/1.0.4、xsel/1.2.1） |
| 2 | config.status 报 `Permission denied` on temp dir | E114: configure 用 umask 077 建临时目录，HMDFS 下的 acl/mac 机制导致不可写 | 补丁 0001 将 umask 077 → 022 |
| 3 | 链接 `undefined symbol: getpass` | HarmonyOS libc.so 不导出 getpass()（仅 libc.a 中有），动态链接失败 | 补丁 0002: getpasswd() 改用 POSIX termios (tcgetattr/tcsetattr/termios.h) 实现，避免 getpass 依赖 |
| 4 | gcc 构建的 aclient 执行报 `Operation not permitted` | 设备上 gcc 产物与 HarmonyOS 安全策略不兼容；clang 构建的 aclient 正常执行 | 配方使用 AutotoolsToolchain 注入 CC=clang，确保 clang 编译 |
| 5 | CI conan-build-test 配置 `C compiler cannot create executables`（buildset 32881；本地 `~/preflight` 复现不同） | CI worker 的 TMPDIR 指向 `/data/storage/el2/base/cache`，该目录属另一 UID(20020102) 不可写，clang 编译 conftest 报 `unable to make temporary file: No such file or directory` | build() 中探测可写 TMPDIR（`_writable_tmpdir()`：先试 `$TMPDIR` 写探针，失败回落 `~/tmp`），并注入 `TMPDIR`/`TEMP`/`TMP` 供 clang/conftest 使用（try/finally 恢复）；staging 一律放 `~/tmp/cdsclient-1.0.0-staging`，与 clang 临时目录分离 |

## 补丁说明

| 补丁 | 目标 | 说明 |
|------|------|------|
| 0001 | configure | HMFS pwf 兜底 + umask 022（E114） |
| 0002 | aclient.c | getpasswd() 改用 POSIX termios（HarmonyOS libc.so 无 getpass） |

## 依赖版本

无外部依赖（仅 libc + socket API，均为 OHOS 系统库）。

## 上游测试

cdsclient 4.07 上游**无任何自动化测试**（已审计）：
- 源码树无 tests/ test/ 目录，无测试文件
- Makefile.in 仅有 all/install/clean/tar 等目标，无 check/test 目标
- configure 仅做编译器/头文件/函数探测，无测试宏
- catClient.py 含 --test 选项但需要连接活 CDS 服务器（非自动化测试套件）

因此 test_package/MANIFEST.yml 声明 `upstream_tests_exist: false` + `upstream_test_audit`，
test_package 输出 `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",...}`。

## 验证结果

test_package 冒烟测试（6 个真实断言）：
1. bin/aclient 文件存在
2. `aclient -version` → 输出 `aclient (CDS) Version 2.7`，rc=0
3. `aclient -h` → 输出 `Usage: aclient [-b bsiz] ...`，rc=0
4. file(1) 报告 ELF 64-bit LSB arm64
5. 关键 shell 脚本 (vizquery/find_gen/catcat/lscat/Detex) 存在
6. find_gen 无参执行退出码非 0（离线参数守卫）

## 注意事项

- cdsclient 是 CDS 天文数据库客户端：aclient 是 C 核心二进制，其余 ~90 个文件是 shell 脚本
  (findxxx, vizquery, catcat, lscat 等)，运行时需要网络连接 CDS 服务器
- 非交互模式（-version/-h）纯本地，无需网络
- 产物为可执行文件 + shell 脚本，无库可链接，已创建软件级 commands.json（R38，tool 类型）
- CDS 官方下载服务器 cdsarc.cds.unistra.fr 有 Anubis 反爬保护 + SSL 证书校验问题；
  真机下载使用 `-k` 可正常拉取（sha256 一致）
- 上游版本为 4.07，conan 包版本为 1.0.0（社区约定版本号）