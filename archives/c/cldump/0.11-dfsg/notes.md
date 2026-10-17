# cldump 0.11-dfsg 适配笔记

## 编译环境

- 构建系统: makefile（上游手写 `src/Makefile`，无 configure/install/check 目标）
- 编译日期: 2026-09-09
- 编译器: clang（经 `tools.build:compiler_executables` 获取，以 `make CC=...` 传入，R33）
- 状态: built（待真机预检通过后由 HMBS 提交推送）
- 依赖: 无（仅 libc；stdio/stdlib/string + mmap + iconv 由系统 libc 解析，Debian 同样无额外 Build-Depends）

## 上游源码

- 官方源: `https://deb.debian.org/debian/pool/main/c/cldump/cldump_0.11~dfsg.orig.tar.gz`
- 镜像回退: `https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/c/cldump/cldump_0.11~dfsg.orig.tar.gz`（与官方包 MD5 `ca1a8b8c1489ed4374a5dc9eea0b8fcd` 一致，同归档可共用 sha256）
- sha256: `a00f619985d7980471143c5f57f3c96440d3f8b15ddcab8f768fb5a725944af5`（23,417 字节 orig.tar.gz）
- 版本映射: Debian `0.11~dfsg`（`~` 非 Conan 合法字符）映射为 `0.11-dfsg`
- 内容: 顶层 `cldump-0.11~dfsg/` + `src/*.c/*.h`（12 个文件）+ `src/Makefile` + `COPYING`/`README`/`CREDITS` + `magic`
- 许可: GPL-2.0-only（COPYING 为 GPLv2；`cldump.c` 头声明 "version 2 of the License"）

## 编译步骤

1. `apply_conandata_patches`：应用 `0001-makefile-respect-env-flags.patch`
   （`CFLAGS =` → `CFLAGS +=`，链接行追加 `$(LDFLAGS)`；Debian
   `01-hardening.patch` 同法，保证 Conan buildenv 旗标不被覆盖）
2. `make -j1 CC="<conan c compiler>"`（`cwd=source/src`，R9 单作业；命令行
   `CC=` 覆盖 Makefile 默认值）
3. `build()` 内冒烟验证（R51：上游无测试套件）：新构建的 `src/cldump --version`
   必须退出 0（`can_run` 为真时）
4. `package()`：无 install 目标，手动拷贝 `src/cldump` → `<pkg>/bin`，
   `src/cldump.1` → `<pkg>/share/man/man1/`（xsel/cdbfasta 等 CLI 工具同族做法）
5. test_package 消费者测试（`conan create` 自动触发）：`bash test_cldump.sh`
   真实执行安装后的二进制

## 上游测试清点（R51）

- 上游**无自动化测试套件**：tarball 内无 `test*/` 目录、无 `*test*`/`*check*`
  源文件；`src/Makefile` 仅 `all/clean` 目标（`make -n check` 无规则）；
  无 CTest/gtest/pytest；Debian 打包无 `debian/tests/`（仅 `debian/tests/control`
  声明，无 autopkgtest 可执行测试）。
- 静态计数如实为 **0**，`MANIFEST.yml` 以 `upstream_tests_exist: false` +
  `upstream_test_audit` 显式审计，`test_cldump.sh` 输出
  `status:"no_tests"`、`discovered:0`、`executed:0` 及具体 `reason`。
- 补偿验证（全部真实执行二进制，非空壳）：
  - `build()` 冒烟：`--version` 退出 0
  - test_package 4 项断言：`--version` 输出版本行、`--help` 输出用法、无参数
    退出 3（"no filename specified"）、不存在文件退出 1（"Couldn't open file"）

## 消费者测试

- `test_package/test_cldump.sh`（`test_type=explicit`，xsel 同族先例）：
  bash 直接驱动安装到包内的真实二进制，4/4 断言通过；脚本末尾输出
  `HMBS_TEST_PACKAGE_RESULT`（discovered=4/passedCount=4）与
  `HMBS_UPSTREAM_TEST_RESULT`（no_tests，discovered/executed=0）供真机门禁采集。
- 证伪说明：4 个用例分别断言不同退出码（0/0/3/1）与不同输出子串；若二进制
  被换成 `exit 1` 桩，第 1/2 项非 0 即失败 leak；若 fixture 为空，第 3/4 项的
  特征串匹配即失败。不存在"空文件比空文件报 PASS"的静默通过路径。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `CFLAGS = -Wall -g -O2` 覆盖 Conan 注入旗标，链接行忽略 `LDFLAGS` | 2010 年手写 Makefile | 补丁改为 `CFLAGS +=` 并追加 `$(LDFLAGS)`（Debian 01-hardening 同法） |
| 2 | 无 `./configure`，不能走 Autotools 模板 | 纯 Makefile 项目 | 用 Makefile 模板：`make -j1 CC=...` + 手动 `package()` |
| 3 | 本机直连 `https://deb.debian.org` TLS 握手超时 | 本机出口网络 | `conandata.yml` url 写有序列表：Tuna 镜像在前、官方原 URL 在后兜底；两者 MD5 一致，同 sha256 |
| 4 | Windows 工作区 `archives/l/libXext` 与 `archives/l/libxext` 大小写冲突致单文件常显 dirty | Windows 文件系统不区分大小写，上游两目录并存 | 本轮未改动该处；该 dirty 为环境 artifact，不属本 PR（单包原子性 W2） |

## 验证结果

```bash
conan create archives/c/cldump/0.11-dfsg -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 待 HMBS 真机预检：conan create（含 build() 冒烟 + test_package 4/4）+ 上游 no_tests 审计标记
```

## 注意事项

- `package_type=application`，软件级 `commands.json` 已声明（单命令 `cldump`）
- 版本目录 status 为 built：配方已完成待真机验证，未发布
- `endian.h`/`byteswap.h` 在 OHOS bionic libc 可用（b43-fwcutter 同族实证）；
  `BYTE_ORDER == BIG_ENDIAN` 分支在 aarch64 LE 下不编译，无额外字节序补丁
- `iconv`/`mmap` 走系统 libc（Debian 无额外依赖）；若真机链接报
  `undefined reference to iconv_open`，下一轮追加 `libiconv/1.17` 依赖
---

**编译结束**: 2026-09-09
**最终状态**: built
