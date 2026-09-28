# kore 4.2.3 适配笔记

## 基本信息

- 上游：https://github.com/jorisvink/kore（官方发布站 https://kore.io/releases/kore-4.2.3.tar.gz）
- 版本：4.2.3（RELEASE 2022-08-22，最新稳定版）
- 构建系统：纯 Makefile（无 configure / CMake / meson）
- 类型：tool（application，产出 `kore` + `kodev` 双二进制 + C 头文件 + share 构建元数据）
- 依赖：openssl（默认 `TLS_BACKEND=openssl`，链接 `-lssl -lcrypto`）；默认 flavor 下无其他外部依赖
- 适配路径：路径 A（基础适配）
- 申请人：momimgya，队伍名称：干

## 编译方案

1. `source()` 从 conandata.yml 官方 URL 下载 tarball 并解压（sha256 已用 kore.io 官方 `.sha256` 文件交叉核对，另与 FreeBSD ports 记录的 `f9a9727a...5ec7f5d82` 一致）。
2. `requirements()` 声明 `openssl/3.5.8.1`（制品仓已发布，同 kamailio-tls 6.0.6 口径）。
3. `build()` 执行 `make -j1 CC="<conf>" OPENSSL_PATH="<openssl包>" PREFIX=/`：
   - R33：编译器取自 `tools.build:compiler_executables.c`，OpenSSL 头/库经 `OPENSSL_PATH`（上游 Makefile 原生支持的变量）注入，不裸用 shell 环境变量；
   - 默认 flavor（不启用 PYTHON/LUA/CURL/PGSQL/ACME/TASKS/JSONRPC），依赖闭包仅 openssl；
   - OHOS 下对产出的 `kore` / `kodev/kodev` 执行 binary-sign-tool 自签名（参照 klustakwik 口径），否则内核拒绝 exec。
4. `package()` 执行 `make install DESTDIR="<pkg>" PREFIX=/`，安装 `bin/kore`、`bin/kodev`、`include/kore/*.h`、`share/kore/*`（features/linker/ffdhe4096.pem/源码快照），并复制 LICENSE 到 `licenses/`。

## OHOS 风险点（待真机验证）

| # | 风险 | 说明 | 对策 |
|---|------|------|------|
| 1 | `uname -s` 分支 | Makefile 按 `uname -s` 选择 `src/linux.c + src/seccomp.c`（Linux）或 `src/bsd.c`；真机 HongMeng Kernel 的 uname 输出决定走哪条分支，seccomp 沙箱头在 OHOS 是否可用未知 | 首轮保持上游默认，真机日志若报 seccomp 相关错误再处理（不预设补丁） |
| 2 | `-rdynamic` | 上游 LDFLAGS 硬编码 `-rdynamic`，OHOS lld 是否接受未知 | 真机失败再决定是否补丁剥离 |
| 3 | `-Werror` | 上游 CFLAGS 含 `-Werror`，clang 15 新警告可能转错误（Gentoo 曾为此去 `-Werror`） | 真机失败再补丁处理，不提前改源码 |
| 4 | `install` 命令 | `make install` 依赖 `install -m`，toybox 是否完整支持未知 | 真机失败则改用 cp/chmod 兜底 |
| 5 | `kore -v` 输出 | 版本字符串来自 RELEASE 文件（tarball 内为 `4.2.3`），测试据此断言；若构建树含 `.git` 则变为分支哈希，conan source 无 `.git`，故断言稳定 | 无 |

## 上游测试审计结论

上游无任何自动化测试（详见 test_package/MANIFEST.yml）：顶层 Makefile 无 check/test 目标，无 tests/ 目录，examples/ 仅为手动演示应用。因此 `upstream_tests_exist: false`、`upstream_test_total: 0`、`upstream_test_count_method: none`，build() 不调用上游测试，test_package 做 5 项消费者验证。

## 验证记录

- 本轮：完成未提交工作树（严禁 commit/push/建 PR），等待 HMBS 后台真机预检（conan create + rule4）。
- 真机 evidence（通过率数字）待 HMBS 预检返回后填写进 PR 正文；本轮不猜测数字。

## 源码修改

无 conandata 补丁文件（`patches: {}`）。OpenSSL>=3 兼容由配方内确定性 Makefile 编辑处理：`conanfile.py::_downgrade_deprecated_werror()` 在现有 `CFLAGS+=-DPREFIX=... -fstack-protector-all` 行后追加两行 `CFLAGS+=-Wno-error=deprecated-declarations`（`src/tls_openssl.c` 的 RSA_meth_*/EVP_PKEY_get1_RSA 废弃告警）与 `CFLAGS+=-Wno-error=incompatible-pointer-types-discards-qualifiers`（`src/keymgr_openssl.c:695/719` 处 `EVP_PKEY_get0_RSA/EC_KEY` 在 OpenSSL 3 返回 `const *` 赋给非 const 局部；底层 EVP_PKEY 可变，仅 getter 契约加 const，降级运行安全）。上一轮曾用 patch 文件路线，因 hunk 上下文在真机预检中打不上而改用本路线；其余 `-Werror` 保留。另 `conanfile.py::_fix_kodev_openssl_path()` 给 `kodev/Makefile` 补上顶层同款 `OPENSSL_PATH` 支持（`CFLAGS+=-I$(OPENSSL_PATH)/include`、`LDFLAGS+=-L$(OPENSSL_PATH)/lib`）：kodev 子 make 原生忽略该变量，在 Conan 隔离布局下 `src/cli.c:26 openssl/err.h` 找不到、`-lcrypto` 链接不到 conan 包；并给 kodev 自有 `-Werror` CFLAGS 补同样的两行定向降级（顶层文件内追加的降级不会透传到子 make，`src/cli.c` 的 SHA256_*/RSA_* 废弃 API 在 OpenSSL 3 下同样转错误）。
