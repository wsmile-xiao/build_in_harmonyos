# trousers 0.3.15 适配笔记

## 编译环境
- 构建系统: autotools（release tarball 只带 `configure.ac`/`Makefile.am`，需要 autoreconf）
- 编译日期: 2026-10-03
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`），原生构建 aarch64 / HarmonyOS 6.0
- 状态: built

## 版本说明
- 上游: https://trousers.sourceforge.net/ （SourceForge 项目 `trousers`），版本 `0.3.15`
- 源码: 上游 SourceForge 镜像在当前网络下超时（`twds.dl.sourceforge.net` read timeout），改用
  Debian 官方归档的同一 release：`https://deb.debian.org/debian/pool/main/t/trousers/trousers_0.3.15.orig.tar.gz`，
  sha256 `1e5be93e518372acf1d92d2f567d01a46fdb0b730487e544e6fb896c59cac77f`（与上游 tar 包内容一致，仅含额外
  `.git`/`.gitignore`）
- 版本号沿用赛事清单 `0.3.15`（首次适配，无适配修复后缀，遵循 R37）

## 编译步骤
```bash
# 运行依赖：openssl/3.5.6.1（libcrypto 提供 trspi 的哈希/加解密原语）
# 构建期工具：automake/1.18、libtool/2.5.4、pkg-config/0.29.2（autoconf 用工作机自带的 2.72，见问题 2）
conan create archives/t/trousers/0.3.15 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码包没有 `configure`，`bootstrap.sh` 跑不起来 | release tarball 只带 `configure.ac`，且 bootstrap.sh 的 aclocal→libtoolize 顺序在干净树上不成立 | `build()` 里用 `autoreconf -fi` 生成构建脚本（顺序正确、自动 `--add-missing`） |
| 2 | `autoreconf` 报 `Cwd.so: Perl_my_cxt_init: symbol not found` | 工作机的 `autoreconf` 用系统 perl 5.42.0，却通过 PERL5LIB 载入了 conan `perl/5.42.2` 的 XS 模块；改用 registry 的 autoconf 后，其脚本又写死了 registry perl 的 shebang | 不使用 registry 的 autoconf，直接用工作机自带的 autoconf 2.72（系统 perl 下工作正常）；`PERL5LIB` 收敛为 automake 自己的模块目录 |
| 3 | `configure` 报 `working directory cannot be determined` | HMDFS 下 Conan 构建目录里 `getcwd()` 失败，autoconf 的 `pwd` 判定直接退出 | 生成 configure 后打运行时补丁：`pwd` 失败回退 `$PWD`；config.status 临时目录 `umask 077 → 022`（HMDFS 新目录强制 setgid，077 目录属主都不可写） |
| 4 | 无法执行链接出的 conftest（E064） | 鸿蒙只运行已签名二进制 | 显式传 `--build/--host=aarch64-unknown-linux-gnu`（项目用 `AC_CANONICAL_TARGET`），configure 走交叉编译分支，不做运行探针 |
| 5 | `tcsd/platform.c` 报 `incompatible integer to pointer conversion` | 鸿蒙的 `<utmp.h>` 声明了 `setutent/getutent/endutent` 却没有 `getutid` 原型，且该符号在 SDK sysroot 的 libc 里也不存在 | 补丁 0001：改用 `getutent()` 遍历并按 `ut_type == RUN_LVL` 过滤，语义与原来的 `getutid()` 等价 |
| 6 | `tcsd/tcsd_conf.c` 链接报 `undefined symbol: rindex` | `rindex()` 是 BSD 旧拼写，musl 只提供 `strrchr()` | 补丁 0001：9 处 `rindex(` 改为 `strrchr(`（POSIX） |
| 7 | 消费者链接 libtspi 报 `undefined symbol: getpwent_r` | `getpwent_r()` 非 POSIX，musl/HarmonyOS 未导出；函数里本来就有 BSD 分支用 `getpwent()` | 补丁 0002：Linux 分支同样改用 `setpwent/getpwent/endpwent` 迭代器 |
| 8 | SourceForge 下载超时 | `downloads.sourceforge.net` 跳转的镜像不可达 | 换用 Debian 官方归档的同一 release（见版本说明），并在 conandata.yml 中注明原因 |
| 9 | 上游没有测试套件 | `Makefile.am`/`src/*/Makefile.am` 均未注册 `check_PROGRAMS`/`TESTS`；`*_selftest.c` 是编译进库的自检代码，需真实 TPM 才能运行 | `build()` 内置 `grep`/`find` 审计把「无上游测试」写入 conan create 日志（R51 口径 N=0），并用消费者用例覆盖可用性 |
| 10 | 产物里带 libtool `.la` 包装脚本 | libtool 默认安装 `.la`，其中记录构建机路径 | `package()` 清理 `lib/*.la` |

## 源码修改
- `patches/0001-tcsd-posix-portability.patch` — tcsd：`strrchr()` 替代 `rindex()`；`getutent()` 扫描替代
  `getutid()`（运行级别查询）
- `patches/0002-tspi-ps-portable-getpwent.patch` — tspi：以可移植的 `setpwent/getpwent/endpwent` 迭代器
  解析用户主目录，替代非 POSIX 的 `getpwent_r()`

## 依赖版本
- `openssl/3.5.6.1`（libcrypto：`src/trspi/crypto/openssl` 的哈希、RSA、对称加密与随机数）
- 构建期工具：`automake/1.18`、`libtool/2.5.4`、`pkg-config/0.29.2`，以及工作机自带的 autoconf 2.72 / m4 / make

## 验证结果
```bash
conan create archives/t/trousers/0.3.15 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# CREATE_RC=0
# 交付：lib/libtspi.a、lib/libtddl.a、bin/tcsd、include/tss/*.h(23)、include/trousers/*.h(2)、
#       share/man、etc/tcsd.conf、licenses/LICENSE（共 114 个文件）

# 消费者用例（test_package，静态链接 libtspi）
ok 1..6 - Tspi_Context_Create / GetDefaultPolicy / CreateObject / Policy_SetSecret / CloseObject / Context_Close
6 checks, 0 failures
```

上游测试：该版本**不含测试套件**（`Makefile.am` 与各子目录都没有 `check` 目标/`check_PROGRAMS`/`TESTS`；
`*_selftest.c` 是编译进 libtspi/libtcs 的自检入口，只能在有真实 TPM 与 tcsd 运行的环境里调用），因此按
TEST_QUALITY_SPEC 的要求在 `build()` 内置审计命令留证，并补充消费者用例。详见
`test_package/MANIFEST.yml` 与 `reports/test-report.md`。

## 注意事项
- 交付静态库 `libtspi.a` 与 `libtddl.a`；`tcsd` 守护进程需要真实 TPM 设备与 `/etc/tcsd.conf`，本包只做编译与
  链接验证，不在 CI 中启动守护进程。
- 头文件沿用上游布局：`include/tss/*.h`（TSS 1.2 API）与 `include/trousers/*.h`；消费者用
  `#include <tss/tspi.h>` 引入。

---

### 对话 #1 — 编译协作者 (implementer)

**请求**: 在鸿蒙 PC 上完成 trousers 0.3.15 的适配并按赛事流程提交 PR。

**执行摘要**:
1. 依赖预检（W0/R36）：只需 `openssl`（制品仓已发布），其余为 autotools 构建工具。
2. 构建链路：`autoreconf -fi` 生成构建脚本 → 运行时修补生成的 `configure`（HMDFS pwd/umask）→
   `conan create` rc=0，交付 libtspi.a / libtddl.a / tcsd / 25 个头文件。
3. 上游测试清点（R51）：无 `check` 目标、无 `TESTS`，自检代码需真实 TPM，判定 N=0 并在 `build()` 内置
   `grep`/`find` 审计留证；补充 6 条断言的消费者用例（100% 通过）。
4. 关键问题与证据：PERL5LIB/registry-perl 冲突（逐次尝试记录：系统 autoreconf + conan perl 模块 → XS 符号
   不匹配；registry autoconf 的 shebang → 改用系统 autoconf）；`getutid`/`rindex`/`getpwent_r` 三个
   musl 缺失符号分别以 `getutent()` 扫描 / `strrchr()` / `getpwent()` 迭代器替代，并用
   `nm -u` + sysroot libc 符号表核对。
5. 质量门禁：conan-verify、W3 本地 CI 模拟、W4 独立审计（见 `reports/`）。

**产出文件**: `conanfile.py`、`conandata.yml`、`patches/`（2 个）、`test_package/`
（`conanfile.py` + `CMakeLists.txt` + `test_trousers.c` + `MANIFEST.yml`）、`notes.md`、`manifest.yaml`、
`reports/test-report.md`。
---

**编译结束**: 2026-10-03 21:19
**最终状态**: built
