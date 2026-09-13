# desproxy 0.1.0 适配笔记

## 编译环境
- 构建系统: autotools（configure + make）
- 编译日期: 2026-09-10
- 编译器: clang（CI OHOS profile）/ gcc 11.4（本地 Linux 验证）
- 状态: built（本地验证通过，待远程 CI）

## 上游信息
- 上游项目: desproxy - a TCP tunnel for HTTP proxies（SourceForge）
- 上游仓库: https://sourceforge.net/projects/desproxy/
- 版本说明: 上游无正式 0.1.0 release，最新源码包为 0.1.0-pre3（0.1.0 系列），本适配以该源码对应版本 0.1.0
- 源码 URL: https://downloads.sourceforge.net/project/desproxy/desproxy/desproxy-0.1.0-pre3/desproxy-0.1.0-pre3.tar.gz
- SHA256: d0c8a299fc3eacd12aef79c422a09f0e15e48ac69163ff8eef0b62b20d162ffd
- 许可证: GPL-2.0
- 语言: C（C 95.9%）

## 编译步骤

```bash
./configure --prefix=$DEFAULT_PREFIX
make -j1          # CFLAGS 经配方注入 -fcommon
make install DESTDIR=$TEST_PREFIX
```

产物（5 个命令行工具，安装到 bin/）:
- desproxy — 主程序：TCP 隧道（HTTP CONNECT 代理）
- desproxy-inetd — inetd 模式隧道
- desproxy-socksserver — SOCKS5 服务器
- desproxy-dns — DNS 转发器
- socket2socket — 双 socket 连接工具

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接报大量 `multiple definition of 'fd'/'status'/...`（desproxy.h:73-101） | 1990s 老 C 代码在 desproxy.h 中直接定义全局变量（非 extern 声明），GCC≥10 / Clang 默认 `-fno-common` 将 common 符号改为强符号导致重复定义 | 配方 `generate()` 中经 `AutotoolsToolchain.extra_cflags` 注入 `-fcommon`（构建参数层修复，R1 参数优先，不改源码） |
| 2 | `socket2socket.c` write() 返回值未检查警告 | glibc `warn_unused_result` | 仅警告不阻塞，保持上游代码原样 |
| 3 | 远程 HarmonyOS CI 在 `conan-build-test` 失败：`config.status: .../subs.sed: Permission denied` → `make: *** No targets specified and no makefile found` | 1990s autoconf 生成的 `config.status` 用 `$TMPDIR/csXXXXXX`（`mktemp -d`）创建临时目录；OHOS 的 toybox `mktemp -d` 创建的临时目录权限异常（无论 `$TMPDIR` 指向 `.cache/tmp` 还是 conan 构建目录均复现），config.status 写入临时文件被拒 → Makefile 未生成 | ① 配方 `generate()` 经 `conan.tools.env.Environment` 把 `TMPDIR` 指向 conan 构建目录（确定可写）；② `patches/0001-tmpdir-fallback.patch`：`config.status` 临时目录改用 `mkdir`（umask 077），`$TMPDIR` 不可用/不可写时回退当前目录（configure 所在目录，确定可写）。本地已验证：`TMPDIR=/proc/readonly ./configure` 仍成功生成 Makefile |
| 4 | 远程 HarmonyOS CI（tmp 修复后）在编译阶段失败：`desproxy.c: error: incompatible integer to pointer conversion passing 'int' to parameter of type 'const char *'`（gettext 未声明） | configure 检测到 OHOS sysroot 存在 `libintl.h` → config.h 定义 `HAVE_LIBINTL_H` → 源码 include libintl.h；但 **OHOS 的 libintl.h 不声明 gettext**，clang 将隐式函数声明（返回 int）默认视为 error（`-Wimplicit-function-declaration` → `-Wint-conversion`） | 配方 `generate()` 经 Environment 预置 autoconf 缓存变量 `ac_cv_header_libintl_h=no`，使 configure 跳过 libintl.h 检测（日志显示 `(cached) no`），config.h 不定义 `HAVE_LIBINTL_H`，源码走 `#define gettext(A) A` 无 NLS 宏分支（构建参数层修复，R1 参数优先，不改源码）。本地以 `-Werror=implicit-function-declaration -Werror=int-conversion` 严格模式验证编译通过 |

## 源码修改

1 个源码 patch（构建生成文件，最小必要）:
- `patches/0001-tmpdir-fallback.patch` — 修改 autoconf 生成的 `configure` 中 config.status 模板的临时目录创建逻辑：
  - 原：`mktemp -d -q "$TMPDIR/csXXXXXX"`（OHOS toybox mktemp 创建的目录权限异常 → Permission denied）
  - 改：`mkdir`（umask 077）+ `$TMPDIR` 不可用/不可写时回退当前目录
  - 生效面：configure 生成的 `config.status` 同样适用（配置阶段临时文件落盘路径修复）

## 依赖版本

无外部依赖（仅 libc + POSIX 头文件）。

## 上游测试清点

- Makefile.in / src/Makefile.in 仅有 `all`/`clean`/`install` 目标，**无 check/test 目标**，源码包无 tests 目录
- 上游测试用例数: **0**
- 适配后补全: test_package 冒烟测试 5 项（逐一执行 5 个二进制验证可运行 + 版本 banner），断言数 5

## 验证结果

```bash
# 本地 Linux 探索编译（gcc 11.4, -fcommon）
make -j2 CFLAGS="-fcommon -O2"     # 5 个二进制全部构建成功
./desproxy                        # 打印 "desproxy 0.1.0-pre3" banner + Usage, exit 0
./desproxy-inetd                  # 同上
./socket2socket                   # 同上

# conan-verify（本地 Linux profile 验证配方逻辑；远程 CI 用 ohos-aarch64 交叉编译）
conan create . -pr:h=<linux> -pr:b=<linux>   # 构建 + test_package 冒烟测试通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools + -fcommon 注入） |
| conandata.yml | 源码 URL + SHA256 |
| test_package/ | 5 项二进制冒烟测试 |
| commands.json（软件级） | 5 个命令行工具声明（R38） |

## 注意事项

- 远程 HarmonyOS CI 使用 `ci/conan/profiles/ohos-aarch64`（clang 15 + aarch64-linux-ohos triplet），为本包最终门禁
- `-fcommon` 在 clang 15 仍受支持（deprecated 但可用），如未来工具链移除需改为源码 patch（desproxy.h 全局变量改 extern + 单点定义）
---

**编译结束**: 2026-09-10 02:21
**最终状态**: built
