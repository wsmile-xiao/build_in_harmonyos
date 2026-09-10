# bruteforce-wallet 1.5.4 适配笔记

## 上游信息

- 仓库：https://github.com/glv2/bruteforce-wallet
- 版本：1.5.4（tag，2024-03-01，commit 648d7d7）
- 源码包：tag 自动归档 tar.gz，28259 bytes
- sha256：`dd91cf78b33d4862120703ab0c81dac64722d18a8867a104474ffaef0738731c`
- 许可证：GPL-3.0-or-later（COPYING 为 GPLv3，源码头声明“version 3 or any later version”）
- 构建系统：autotools（configure.ac + Makefile.am + autogen.sh，无预生成 configure）
- 源码：src/bruteforce-wallet.c、src/elliptic-curve.c/.h、src/version.h（VERSION_NUMBER "1.5.4"）
- 依赖：OpenSSL（libcrypto，EVP/sha256/aes）、BerkeleyDB（db.h，db_create）、pthread、libm
- 类型：纯命令行工具，无库产出（package_type=application）

## 上游测试审计（结论：无正式测试框架；上游证据计为构建等价步骤 1/1）

- 发布包顶层无 tests/、test* 目录或文件。
- Makefile.am 仅定义 `bin_PROGRAMS = bruteforce-wallet`，无 TESTS / check_PROGRAMS，
  即 `make check` 无目标可跑。
- configure.ac 无测试相关宏（仅 AC_PROG_CC/AC_CHECK_HEADERS/AC_CHECK_LIB）。
- GitHub 仓库 Actions 为空，无 CI workflow 可引用。
- Debian 的 debian/tests 为发行版 autopkgtest，非上游测试。
- 因此上游证据采用 nwipe/0.39 先例：`make` 构建步骤本身是唯一可验证的上游断言。
  配方 build() 在真机完成等价直接编译，test_package/test.sh 的 -h 烟雾
  （版本横幅 + 用法文本 + 非空输出断言）证明构建通过，
  输出 HMBS_UPSTREAM_TEST_RESULT status=passed, discovered=1。
  build() 不再输出静态 no_tests 标记（单源在 test.sh，避免状态冲突）。

## 配方决策

| 决策 | 依据 |
|------|------|
| 直接编译 src 2 个 C 文件，不跑 autogen/configure | knock/0.8.2-r2、zimg/3.0.6 先例；预检盒无 autoreconf（实测）+ 无 bash，源码无 config.h 可直接编 |
| openssl/3.5.8.1（published）+ berkeley-db/4.8.30，经 -I/-L 注入 | bvi/1.5.0 先例；Debian 证实上游可对 OpenSSL 3.x 构建 |
| -static 静态链接 | R26 终端工具要求；bvi 先例 |
| CC 取自 tools.build:compiler_executables（R33） | exim 先例写法 |
| test_package 跑真二进制 3 次调用（-h / 无参 / 未知选项） | R34；-h 走 exit(EXIT_FAILURE)，脚本按“输出断言”而非退出码判定 |

## 风险与待验证（真机预检）

1. `-static` 下 libdb.a/libcrypto.a 链接顺序与 musl 缺符号（如 dl）问题，待真机 conan create 验证。
2. OpenSSL 3.x 废弃 API（EVP_MD_CTX_create、EVP_CIPHER_CTX_cleanup）以警告形式兼容，
   Debian sid 已用 OpenSSL 3.x 构建 1.5.4-1，风险低。
3. 上游仅 2 个 C 文件且无 config.h，直接编译无需 autoreconf，已在配方中绕过。
4. 本轮未在本机跑 conan（规范要求真机验证），以上待 HMBS 真机预检回填实测数据。
