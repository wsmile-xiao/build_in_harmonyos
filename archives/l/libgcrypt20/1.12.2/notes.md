# libgcrypt20 1.12.2 HarmonyOS PC 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4（HarmonyOS PC 真机，Conan 2.29.1）
- 状态: built（待真机预检回填证据后由 HMBS 统一提交）

## 上游信息
- 上游版本：1.12.2
- 上游仓库地址：https://gnupg.org/software/libgcrypt/
- 源码包：https://gnupg.org/ftp/gcrypt/libgcrypt/libgcrypt-1.12.2.tar.bz2
- SHA256：7ce33c2492221a0436f96a8500215e9f3e3dcb5fd26a757cd415e7a843babd5e（与 Homebrew 及 GnuPG 官方一致）
- 包名说明：本配方包名为 libgcrypt20（Debian 运行时包命名，对应 SONAME libgcrypt.so.20），与 archives/l/libgcrypt/1.12.2 同源、同版本、同补丁，仅包名不同以满足下游依赖声明。

## 编译步骤

复用同源 libgcrypt 1.12.2 已验证的 Autotools 流程，未做构建逻辑创新：

1. `AutotoolsToolchain` 生成工具链，OHOS 下追加 `-ffile-prefix-map/-fdebug-prefix-map/-fmacro-prefix-map` 源路径映射，配置参数 `--disable-asm --disable-doc --disable-silent-rules --with-libgpg-error-prefix=<libgpg-error 包路径>`。
2. 通过 `GPG_ERROR_CONFIG` 与 `PKG_CONFIG_PATH` 注入 `libgpg-error/1.55` 头文件与库路径，`ac_cv_path_GPGRT_CONFIG=no` 避免误用宿主 gpgrt-config。
3. OHOS 下用 `CONFIG_SHELL` 显式执行 `configure`，`PWD` 固定为 build 目录；`libtool` 去除 `hardcode_libdir_flag_spec` 的 rpath 硬编码。
4. Homebrew 同款可移植配置：`random` 目录 jitterentropy 对象先以 `CFLAGS=-O0` 预编译，再全量 `make -j1`，保留熵源。
5. 每次构建必跑完整上游 `make check`，OHOS 下三个生成的 shell 测试经 `tests/ohos-test-wrapper.sh` 走可执行 shell，其余 ELF 测试保持 Automake 直接执行；`make` 与 `make install` 阶段统一 `SHELL=/system/bin/sh`。
6. 打包去除 `.la`，OHOS 下对所有 ELF 去 RPATH、去 `.codesign` 后用 `binary-sign-tool -selfSign 1` 重签名。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 要求 libgpg-error 1.56，制品仓仅有 1.55 | 上游 tarball 预生成 `configure` 写死 1.56 | `configure.ac` 补丁对齐到 1.55，并在配方内对预生成 `configure` 做精确替换，保持 `configure.ac` 为准 |
| 2 | `config.guess` 报 unable to guess system type | 不认识 HarmonyOS | 0003/0004 补丁让 `config.guess`/`config.sub` 识别 `HarmonyOS` 并映射到 `aarch64-unknown-linux-ohos` |
| 3 | HMDFS 下 `configure` 临时目录不可写 | `umask 077` 在 HMDFS 权限异常（E129） | 配方内精确替换两处 `umask 077` 为 `022`，不宽泛改生成文件 |
| 4 | 生成的 shell 测试在 HMDFS 无执行权限 | HMDFS 对脚本执行位限制（E087） | 新增 `tests/ohos-test-wrapper.sh`，经 `TESTS_ENVIRONMENT` 用 `/system/bin/sh` 显式解释执行 |
| 5 | 打包 ELF 含 RPATH 与旧签名 | Conan 缓存路径泄漏，OHOS 要求重签名 | `patchelf --remove-rpath`、`llvm-objcopy` 去 `.codesign`、`binary-sign-tool` 重签名 |

## 源码修改

- `patches/0001-configure.ac.patch`：`NEED_GPG_ERROR_VERSION` 由 1.56 对齐到已发布的 1.55。
- `patches/0002-tests-ohos-test-wrapper.sh.patch`：新增 HMDFS shell 包装器。
- `patches/0003-build-aux-config.guess.patch`：识别 HarmonyOS 主机。
- `patches/0004-build-aux-config.sub.patch`：接受 HarmonyOS target triplet。
- 补丁均复用 `archives/l/libgcrypt/1.12.2/patches/` 已验证内容，未引入 `__OHOS__` 平台宏。

## 依赖版本

- 唯一 Conan 依赖：`libgpg-error/1.55`（`transitive_headers` + `transitive_libs`，因 `gcrypt.h` 公开包含 `gpg-error.h`）。
- 工具链：clang 15.0.4，`libc++`，`os=OHOS 6.0`，`arch=armv8`。

## 上游测试审计

- 上游测试框架：Automake `make check`，测试定义见 `tests/Makefile.am`。
- 上游测试总数：41（与同源 libgcrypt 1.12.2 一致，含 2 个大文件哈希跳过项：6 GiB 与 256 GiB）。
- 本配方 `build()` 必跑 `make check`，以上游 serial-tests 锚定 verdict 行（`PASS:/FAIL:/SKIP:`，每 TESTS 一行）为唯一确定性计数源输出 `HMBS_UPSTREAM_TEST_RESULT` 标记（`hmbs-make-check.log` 捕获 stdout 仅作审计回显，不做子串计数；`All N passed/(M not run)` footer 仅交叉核对）。2 个 SKIP 为上游大文件哈希项 `hashtest-6g`（6 GiB）与 `hashtest-256g`（256 GiB，上游按资源默认 SKIP），包装器仅经可执行 shell 路由，不跳过不断言。HMBS 硬门禁要求 `status=passed` 时 `skipped==0` 且 `executed==discovered`（cxxtest/python3-cairo precedent），故这 2 项按 `excluded_cases/total_upstream_cases=41` 如实声明（`discovered=39/executed=39/passed=39/failed=0/skipped=0/excluded_count=2`，`reason` 具名资源缺口），不计入通过；非预期 SKIP 一律判 `failed` 不隐藏。构建期 JSON 持久化到 `upstream_test_result.json` 并经 `package()` 拷入包内 `res/`，`test_package` 在消费者 15 项通过后校验（`skipped==0`、`executed==discovered`）再双通道复发同一标记，缺失则硬失败（librcc 经验2模式，防 `Already installed!` 缓存命中轮次丢失上游证据）。
- 防证伪：标记数字来自测试框架输出；真机预检将核对测试输出与参照文件非空，避免空文件比对误报通过。

## 验证结果

- 本轮为未提交工作树，真机预检由 HMBS 在本轮结束后统一执行，证据回填前不宣称通过率。
- 同源参考（libgcrypt 1.12.2 在同平台真机实测）：上游 41 项中 39 执行通过、2 大文件项（`hashtest-6g`/`hashtest-256g`）因稀疏文件资源未配给而 SKIP；本包按硬门禁报 `discovered=39/executed=39/passed=39/skipped=0/excluded_count=2/total_upstream_cases=41`；消费者 15 项全部通过；shared/static 双模式 `conan create` 返回 0。
- 本包 `test_package`：15 个独立已安装库 API 命令（version、SHA-256、SHA-512、SHA3-256、HMAC-SHA256、CMAC-AES、AES-128 ECB 加解密、AES-256 CBC、ChaCha20、PBKDF2-SHA256、MPI 加/模、S 表达式、随机数），Clang `-Wall -Wextra -Werror` 编译，逐用例 `self.run` 执行并输出 `HMBS_TEST_PACKAGE_RESULT`（`discovered=15`）。
- 待 HMBS 真机返回 stdout 后，如实摘录执行数/通过数回填 PR 正文。

## 交付物

| 文件 | 说明 |
|------|------|
| `libgcrypt.so.20`（shared）/ `libgcrypt.a`（static） | 主库，SONAME 20，无 RPATH，含 `.codesign` |
| `bin/hmac256`、`bin/dumpsexp`、`bin/mpicalc`、`bin/libgcrypt-config` | 诊断工具（随包安装） |
| `include/gcrypt.h` 等 | 公开头文件 |
| `lib/pkgconfig/libgcrypt.pc` | pkg-config 元数据 |

## 注意事项

- 本包与 `libgcrypt/1.12.2` 同源，勿在同一 Conan 图中同时依赖两者以免库冲突。
- 制品仓不支持同版本多 revision，首次适配用上游版本 `1.12.2`，后续修复按 `1.12.2.N` 递增。
- 真机预检前绝不 `commit/push/建 PR`；代码再变则旧验证失效，需重新完整验证。

## 使用知识库

- E007：Autotools `config.guess`/`config.sub` HarmonyOS 识别。
- E087：HMDFS shell 脚本需显式解释器执行。
- E129：Autoconf `umask 077` 临时目录在 HMDFS 不可写。
- 全局：`openharmony-pc-autotools-patchng-hmdfs`、`openharmony-pc-conan-library-shared-options`、`openharmony-pc-conan-test-virtual-run-env`。
- 未新增知识条目； observed 失败模式均已被上述条目覆盖。
