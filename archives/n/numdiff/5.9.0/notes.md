# numdiff 5.9.0 适配笔记（HarmonyOS PC / OHOS aarch64）

## 编译环境
- 构建系统: autotools (configure + make, 非 automake)
- 编译日期: 2026-09-10
- 编译器: clang 15.0.4 (+ clang++)
- 目标: os=OHOS, arch=armv8 (aarch64), compiler.libcxx=libc++
- 状态: built（本地 conan create 通过，未 upload）

## 源码
- 官方源（GNU Savannah nongnu 发布目录）:
  https://download.savannah.gnu.org/releases/numdiff/numdiff-5.9.0.tar.gz
- sha256: 87284a117944723eebbf077f857a0a114d818f8b5b54d289d59e73581194f5ef
  校验方式：以同一官方 URL 独立二次下载并 `sha256sum` 复算，两次结果一致。
  （Savannah 仅提供 `.sig` GPG 签名，无 .sha256 文件；GPG 公钥不在环境内，
  故采用"官方源独立复算一致"作为核验口径。）
- 依赖: 无外部库依赖（仅 libc）。GMP 为可选（`--enable-gmp` 默认开），
  本平台无 gmp 头/库 → configure 的 `AC_CHECK_LIB(gmp, __gmpz_init)` 失败回退
  到内置多精度实现（与上游测试套件要求一致，见下）。

## 编译步骤
```bash
source .build-context-numdiff-5.9.0
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX --disable-nls   # 参数最少化 + 断 NLS
make -j1
make install DESTDIR=$TEST_PREFIX
```
- `--disable-nls` 是唯一额外参数：OHOS 无 libintl 开发库（E027 / PSCAN-MUSL-005），
  numdiff 默认 `--enable-nls`（configure.ac 默认 yes，并 `AC_CHECK_LIB(intl,...)`，
  定义 `-DENABLE_NLS` → 源码 `#include <libintl.h>` 会失败）。
- 未加 `--build/--host` 等交叉参数（R1）；configure.ac 无 `AC_CANONICAL_*`，
  因此**不使用 config.guess/config.sub**，规避了 E007/E072。
- 文档目标（html/info/pdf/txt）在 tarball 中已预生成且时间戳与 .txi 相同，
  make 视为最新，不触发 makeinfo/texi2pdf（平台无这些工具）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: creating ./config.status` 后报 `./config.status[609]: can't create ./confjKllBp/subs1.awk: Permission denied` | E011：autoconf 生成的 configure/config.status 用 `umask 077` + `mktemp -d ./confXXXXXX` 建临时目录；HMDFS 上该 0700 目录的 owner UID 被映射（目录显示 drwx--S---），当前进程不可写 | 0001-configure.patch：`umask 077` → `umask 022`（configure 中 2 处）。改后 configure/config.status 正常，`drwxr-s--x` 可写 |
| 2 | 无法解析 `-D` 分隔符 | OHOS 无 libintl | configure `--disable-nls`（配方 generate()） |
| 3 | 上游测试套件 test32 中 `numdiff -D '... ' ` 段错误（exit 139 / SIGSEGV） | numdiff linesplit.c 的 `ssplit()`：分隔符串以分隔符结尾时子串计数 n 多计 1，填充循环只写 i<n 个槽位，`sv[i..n-1]` 未初始化；glibc 常常返回清零内存故被掩盖，musl 返回非零内存 → `is_char_in_vector`/`remove_duplicates_from_string_vector` 对垃圾指针做 strchr/strcmp → 崩溃 | 0002-linesplit.c.patch：`malloc` → `calloc`，所有槽位初始化为 NULL |

## 源码修改（补丁）
- `patches/0001-configure.patch`：configure 中 `umask 077`(2 处) → `umask 022`。
  平台隔离写法：无平台宏，纯 POSIX 语义调整（与 xz/tar/wget/diffutils 一致）。
- `patches/0002-linesplit.c.patch`：linesplit.c `ssplit()` 的 `malloc` → `calloc`。
  平台无关的未初始化内存修复（对正确平台透明，仅消除 UB）；未引入 `__OHOS__` 宏。

## 依赖版本
- 构建期: clang 15.0.4 / GNU Make 4.4.1 / autoconf 2.72（tarball 已含 configure，
  未重新 autoconf）
- 运行期: 仅系统 libc（依赖链为空）

## 验证结果（上游测试 R51）
- numdiff 5.9.0 源码包**无 in-tree 测试**（无 tests/，Makefile.in 无 check/test 目标）。
- 上游官方测试套件为**独立发布**的 `numdiff_tests-1.7.0.tar.gz`（与 5.9.0 同日发布）。
- 清点：34 个测试脚本（test1..test34）；`runalltests.sh` 注册 34 个。
- 运行：34/34 脚本全部执行（脚本以 `#!/bin/bash` 为 shebang，本平台 /bin/bash
  不存在，故以 `bash <script>` 显式调用；pager 传 `cat` 避免交互）。
- 结果：合计 689 个检查项 → **687 PASS / 2 差异**。
  - 2 项差异 = test10 的 `ZfG2` / `zfG2`：**平台大小写不敏感文件系统**导致
    同名文件折叠（预期文件 ZfG2 与 zfG2 折叠、输出 ./output/ZfG2 与
    ./output/zfG2 折叠后写覆盖先写）。验证：`-Z ... -f` 的输出 sha256
    = 5629ef14…，与预期 `ZfG2` 完全一致 → numdiff 行为正确，属测试框架/
    文件系统伪失败（与 libxext/libXext 折叠同源）。
  - 修复补丁生效前 test32 有 3 项 SIGSEGV，修复后 0 崩溃。
- `make check`：numdiff 无该目标（已确认，非跳过）。

## 交付物
- conanfile.py（package_type=application, bindirs=["bin"]）
- conandata.yml（官方 URL + sha256 + 2 补丁）
- patches/0001-configure.patch, patches/0002-linesplit.c.patch
- test_package/{conanfile.py, test.sh, MANIFEST.yml}
- ../commands.json（软件级，R38：numdiff 提供 numdiff/ndselect 两个命令行工具）

## 注意事项
- 本包为命令行工具，commands.json 必需（R38）。
- 运行期仅依赖系统 libc；非系统同名库，不涉及 R26 静态约束。
---

**编译结束**: 2026-09-10 13:02
**最终状态**: built
