# notes — libcaes 0-20251121 OHOS aarch64 适配

本文记录适配过程的关键决策与证据，供后续审计与复用。

## 1. 上游核验（官方事实）

| 项 | 值 |
|---|---|
| 官方主页 | https://github.com/libyal/libcaes |
| 上游版本 | 20251121（configure.ac 内 AC_INIT 硬编码） |
| 配方版本 | 0-20251121（任务指定版本串；对应上游发布即 20251121） |
| 锚定提交 | 4dbdd25466bf25bd73bdf77976e4c9eab744d697（2025-11-21T13:18:06Z，Applied updates） |
| tarball URL | https://mirrors.tuna.tsinghua.edu.cn/ubuntu/pool/universe/libc/libcaes/libcaes_0~20251121.orig.tar.gz（主）/ https://mirror.jmu.edu/pub/ubuntu/pool/universe/libc/libcaes/libcaes_0~20251121.orig.tar.gz（备，两源同文件同哈希） |
| SHA256 | 4e597ebc143f2c1063785ccc1e491f1fc51c27413802f0d32644d260bf3c835c（双镜像实测一致） |
| License | LGPL-3.0-or-later |
| 构建系统 | GNU Autotools（dist 包自带 configure + Makefile.in + ltmain.sh + libcerror 子树，开箱即用） |
| 公开 API | `#include <libcaes.h>`，`libcaes_get_version` / `context_initialize/free/set_key` / `crypt_ecb/cbc/ccm` / `tweaked_context_*` / `crypt_xts`，链接 `-lcaes` |

版本选择说明：Ubuntu `libcaes_0~20251121.orig.tar.gz` 为上游 20251121 的
pristine `make dist` 输出（不含 debian/ 修改），其 `libcaes/*.c` 与 GitHub
提交 4dbdd25 快照逐字节一致（实测 `libcaes_context.c` sha256
8fd53bec… 相等），`configure.ac` 同为 `AC_INIT([libcaes],[20251121])`。
与 libbde（release tarball 自带 configure）同策略：dist 包免去
synclibs.sh（git clone libcerror）与 autoreconf 自举（见 §3/§4）。

## 2. 上游测试调查

| 搜索位置 | 结果 |
|---|---|
| tests/ 目录 | 存在：7 个 caes_test_*.c + test_library.sh/test_runner.sh + pycaes_*.py |
| tests/Makefile.am check_PROGRAMS | 7 个：caes_test_context / crypt_cbc / crypt_ccm / crypt_xts / error / support / tweaked_context |
| tests/Makefile.am TESTS | 默认 1 个：test_library.sh；test_python_module.sh 仅 HAVE_PYTHON_TESTS 条件分支 |
| test_library.sh | LIBRARY_TESTS=context error support tweaked_context，仅跑其中 4 个二进制 |
| tests/data | dist 包不含 tests/data（快照内 4 个 crypt_*.1 仅 17 字节硬编码向量副本，测试 .c 均用内置向量，不读外部固件） |
| pycaes 测试 | 需 Python 绑定构建；配方 --disable-python，不计入发现数 |

结论：上游测试总数 7（口径 autotools_tests），由配方 build() 经
`make check TESTS=` 构建后逐个直接执行 7 个 caes_test_* 二进制覆盖
（含驱动未列出的 3 个 crypt 模式），零 SKIP 设计。

## 3. 依赖分析（W0）

| 依赖 | 状态 | 处理 |
|---|---|---|
| libcerror | dist 包已内含完整子目录（含 Makefile.in 与全部 .c/.h） | configure 经 AC_CONFIG_FILES 直接配置编译为 noinst 静态库，不打包、不传递给消费者，无需 synclibs.sh |
| autotools 自举链（autoconf/automake/libtool/gettext） | 真机/CI 均不需要 | 不声明：dist 包自带全部生成物，build() 直跑 configure（bwm/0.6.3 先例；m4/1.4.19 的 OHOS 跨编译在 HMBS 真机必败见 §4） |
| pkg-config 二进制 | 真机缺失（2026-09-23 预检：checking for pkg-config... no → configure: error: pkg-config not found） | tool_requires pkgconf/3.0.5（meson 构建、无 m4 链，已发布预编译包）+ PKG_CONFIG 导出与 hmbs-shims/pkg-config 垫片（pms/0.42 先例；pkgconf 只带 bin/pkgconf 无别名） |
| python 绑定 | 不需要 | --disable-python 关闭 |

无 conan requires；tool_requires 仅 pkgconf/3.0.5（构建期）。

## 4. 构建期关键机制（与 libbde 同源，dist 包特化）

1. 零自举：dist 包开箱即有 configure，build() 先断言
   `configure` 与 `libcerror/` 存在，假设破裂即 fail-fast，不再跑
   synclibs/autoreconf。
2. m4 连根去除（第 3 次同指纹修复，前两次均为加 tool_requires）：
   autoreconf 链的传递依赖 m4/1.4.19 会以 `-pr:b=ohos-aarch64`
   被跨编译，其 configure[139] 重执行 `$CONFIG_SHELL`；仓库 profile
   固定 `CONFIG_SHELL=/data/service/hnp/bin/bash`，在 HMBS 预检宿主
   不可执行（"inaccessible or not found"，Error 127），而配方层 env
   覆盖影响不到依赖包的构建。根治 = 不再需要 autoreconf。
3. E007：dist 包的 config.guess/config.sub 打 HarmonyOS 补丁
   （aarch64-unknown-linux-ohos）。
4. E011 + HMBS shell 双保险：`_force_posix_shell` 在 configure 文件
   内硬赋值 `CONFIG_SHELL/SHELL=/bin/sh`（脚本运行时内部遮蔽外部坏值，
   不依赖环境层叠顺序，libbde 先例）+ generate() 存
   `hmbs_shell` build-scope env 脚本覆盖 profile [buildenv] +
   build() 内 os.environ 同值覆盖；confstat 走 TMPDIR。
5. 安装期 HMDFS 兼容：cp/mkdir install shim + INSTALL 重定向 +
   chmod 容错（ctpl/cryptopant/libbde 定式）。
6. 工具链：AutotoolsToolchain + OHOS 下追加
   --target=aarch64-unknown-linux-ohos；CC/CXX 走 PATH 优先发现，
   LD_LIBRARY_PATH 在 configure 期间弹出（cstream 教训）。
8. OpenSSL 强制本地实现（2026-09-23 真机 compile 阶段 libcaes/libcaes_context.c:31 fatal error: openssl/err.h file not found）：generate（）追加 --with-openssl=no（上游所有 openssl 引用均受 HAVE_LIBCRYPTO/HAVE_OPENSSL_*_H 保护，切到 FIPS-197 自带实现，无新增依赖；libbde 20240502 issue #6 同源、FreeBSD 端口同标）+ build（）删除 dist 包自带的陈旧 common/config.h（生成物，模板为 config.h.in），防止 quoted #include "config.h" 屏蔽新鲜配置（libbde issue #7 同源）；_dump_make_diagnostics 增打两树 config.h 的 HAVE_LIBCRYPTO/HAVE_OPENSSL 宏作证据。

## 5. test_package 设计（1 个完整消费者端到端用例，含 9 项检查）：`make check TESTS=` 仅构建不跑驱动，
   随后逐个执行 7 个 caes_test_* 二进制；任一失败即抛异常，
   空集亦判失败，杜绝空跑冒绿。

## 5. test_package 设计（1 个完整消费者端到端用例，含 9 项检查）

全部调用真实公共 API，加密后解密比对，不依赖外部 KAT 向量
（lib1305 向量勘误教训：自洽往返优先）：

1. get_version 非空；2. context_initialize；
3. context_set_key AES-128 ENCRYPT；4. ECB 加密；
5. ECB 解密往返一致；6. CBC 加解密往返一致；
7. tweaked_context 初始化与双密钥设置；8. XTS 加解密往返一致；
9. 文件级 AES-128-CBC 端到端流程（写 64 字节明文文件→加密落盘→
解密还原→字节比对，另断言密文与明文不同，多块验证 CBC 链，
TMPDIR 优先、CWD 回退，覆盖后清理临时文件）。

任一检查失败测试二进制即非零退出，ctest 判负；
HMBS_TEST_PACKAGE_RESULT 按实际 9/9 填写。

## 6. 产物与验证（待真机预检回填实测数字）

- 产物：`include/libcaes*.h` + `lib/libcaes.a`（默认）或
  `lib/libcaes.so*`（shared=True）；bin/ 工具不打包。
- build() 内运行上游 7 个 caes_test_* 二进制，期望全部退出 0。
- test_package 消费者测试 9 项检查（含文件级端到端），以 ctest 为准。
- 真机 conan create 日志即 PR 正文「上游测试用例通过率」的唯一依据；
  本轮仅完成工作树，具体数字待预检 evidence 轮摘录。

## 7. 风险与后续

- 镜像一致性：双 Ubuntu 镜像（tuna/jmu）实测同文件同哈希
  （929703 字节）；Ubuntu 归档镜像按官方同步，内容稳定。若预检出现
  下载抖动，conan 的 url 列表会自动按序回退。
- 若 dist 包的 config.guess/config.sub 与预期模板漂移（marker 不存在），
  E007 补丁会静默跳过；届时以预检 configure 的 triplet 报错为准再补分支。
- Windows 工作树注记：本机工作树缺
  archives/g/gama/2.29/patches/0002-dataparser-ungated.patch\r\r
  （文件名尾带 CR，Windows 非法）与 libXext/libxext 大小写合并差异，
  均为本机文件系统 artifact，未纳入本次改动；以后端 Linux 视角为准。
