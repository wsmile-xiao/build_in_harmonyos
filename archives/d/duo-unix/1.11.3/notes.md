# duo-unix 1.11.3 适配笔记

## 源码

- 上游：https://github.com/duosecurity/duo_unix
- 版本：duo_unix-1.11.3 tag
- 源码 URL：GitHub archive（Savannah 1.11.3 已 404，GitHub tag 为官方源）
- SHA256：beabba9fc286fea651941548aa830920f465ca6b754adb6fbc050ad420d3ae75

## 依赖分析

configure.ac 检查的依赖：
- **OpenSSL**（必需）：`AX_CHECK_OPENSSL([], AC_MSG_FAILURE([OpenSSL not found]))`
- **PAM**（可选）：`--with-pam` 默认 no，OHOS 无 libpam，禁用
- **nsl/socket**：系统库，AC_SEARCH_LIBS 自动检测
- **curl**：无（duo-unix 自带 http_parser + OpenSSL HTTPS 客户端，代码注释提及 libcurl 仅是灵感来源）

## 构建系统

- autotools（configure.ac + Makefile.am + libtool）
- **GitHub archive 不含 configure 脚本**（git tree 快照，configure 是 autoreconf 产物不进版本库）
- 解决方案：`build_requirements()` 中 `tool_requires("automake/1.18")` + `tool_requires("libtool/2.5.4")`，build() 中 `autotools.autoreconf()` 自举

## OHOS 适配

1. **config.sub/guess**：autoreconf 生成的 config.sub 可能不识别 `aarch64-unknown-linux-ohos`，build() 中 `_patch_config_for_ohos()` 添加 ohos triplet 支持
2. **交叉编译**：`--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`
3. **OpenSSL**：`--with-openssl={openssl_package_folder}` 指向 Conan 依赖
4. **PAM**：`--without-pam`（OHOS 无 libpam）
5. **login_duo 安装位置**：上游安装到 `sbin/`，CI L2 烟雾测试扫描 `bin/`，package() 中移动到 `bin/`
6. **ELF 签名**：package() 中对 .so 和 bin/ 下 ELF 文件执行 HarmonyOS 代码签名

## 测试

- 上游测试：cram.py（Python 集成测试，需 pexpect + mock 服务）+ unity_tests（C 单元测试）
- CI 环境：上游 cram 测试不适合 CI（需 Python 运行时 + mock Duo 服务），改由 test_package 消费者测试验证 libduo API
- test_package/test_duo.c：调用 `duo_open()`/`duo_geterr()`/`duo_close()`，NULL cafile 使用内置 CA 证书，无需网络

## login_duo -v 行为

`login_duo -v` 调用 `die("login_duo " PACKAGE_VERSION)`，die() 调用 `exit(EXIT_FAILURE)`。
L2 烟雾测试会标记为 "failed (non-blocking)"，这是预期行为，不阻塞 CI。

## 产物

- `lib/libduo.a`（静态库）
- `bin/login_duo`（命令行工具，从 sbin 移动到 bin）
- `include/duo.h`、`duo_private.h`、`util.h`、`shell.h`
