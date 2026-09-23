# cjose 0.6.2.7 — OHOS (HarmonyOS PC aarch64) 适配笔记

## 上游与版本

- 上游: OpenIDC/cjose (cisco/cjose 的延续维护版), release `v0.6.2.7` (2026-06-26)
- 源码: https://github.com/OpenIDC/cjose/releases/download/v0.6.2.7/cjose-0.6.2.7.tar.gz
- SHA-256: `80fae3ef56be6419255092374ffe059018a9a453e861de8e3a8b38d06ce8621d`
- 依赖: jansson >= 2.3, OpenSSL >= 1.0.1h (README; configure.ac 用 AC_CHECK_LIB 探测)
- 测试框架: check >= 0.9.4 (PKG_CHECK_MODULES, 可选条件 — 未装则 have_check=no)

## 设备环境

- python3 3.12.8 (/data/service/hnp/bin), Conan 2.29.1, clang 15.0.4 (aarch64-unknown-linux-ohos), GNU Make 4.4.1
- 依赖 binary: jansson/2.15.1.1、openssl/3.5.8.1 (W0 `conan install --build=never` 通过)

## 构建系统要点

- 纯库项目 (autotools + libtool), 无 CLI 工具 → 无 commands.json
- config.guess (2024-07-27) 不识别 `uname -s = HarmonyOS`/HongMeng 内核 → 显式
  `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`
  (build==host 保持 native 语义, AC_RUN_IFELSE 不被跳过; 先例 abiword 系列 PR #4119)。
  cjose 自带 config.sub 已接受 ohos 后缀, 无需 patch config.guess/sub
- 依赖注入: conan `PkgConfigDeps` + `AutotoolsDeps`, configure 加
  `--with-openssl/--with-jansson` 指向 conan 包目录; PKG_CONFIG_PATH 只指向
  消费方再生成的 .pc 目录, 不用依赖包内 .pc (其 prefix 固化打包机路径)

## 补丁 (2 个)

1. `0001-configure-umask-022.patch` — configure 的 config.status 临时目录用
   `(umask 077 && mktemp -d ./confXXXXXX)` 创建; HMDFS UID 映射 (目录 owner 20001006,
   进程 UID 20020083) 使 0700 目录进程不可写, 且权限位错乱为 `drwx--S---`
   (实测复现)。改 umask 022 (knowledge E011; 先例 a52dec 0002-configure-umask-022.patch)。
   手动 mkdir+写文件不受影响 — 仅 umask 077 创建的目录触发
2. `0002-jwk-init-rsa-buflen-uninit.patch` — `_cjose_jwk_import_RSA` 的
   `d/p/q/dp/dq/qi_buflen` 声明在首个 `goto import_RSA_cleanup` 之后, cleanup
   读未初始化值; clang 15 `-Werror -Wsometimes-uninitialized` 阻断构建 (上游缺陷,
   非平台特有)。修复: 声明提升到函数顶部初始化 (行为不变: `_cjose_cleanse_dealloc`
   对 NULL ptr 直接返回)

## 测试

- check 0.15.2 已在 ohpcd 发布, 但其实测**不可用于设备测试**: conan binary 的
  check_msg.c open_tmp_file 无 TMPDIR 适配, `TMPDIR=<可写目录> make check` 仍报
  "check_msg.c:317: Unable to create temporary file" (构建路径
  `.conan2/p/b/check01f6875eb3aa2/b/` 实测) → 按提审对齐口径从源码自建到任务
  私有 prefix (仅测试用, 不进包依赖链): `./configure --prefix=<task>/check-prefix
  --disable-shared --enable-static`, make install 需 `MAKEINFO=true` (设备无 makeinfo)
- libcheck 两处设备修正 (私有测试依赖, 不进包补丁): config.guess/sub 用 cjose
  tarball 内 2024-07-27 版覆盖 (0.15.2 自带 2022 版不识别 ohos);
  check_msg.c 的 open_tmp_file 把 TMPDIR 探测提到 P_tmpdir 之前 (设备 /tmp 只读,
  P_tmpdir 固化 "/tmp"; 见知识草稿 E547, 发布版 binary 同样受累)
- 测试运行环境: 沙箱 HOME (`$TASK_DIR/test-home`) + 任务可写 TMPDIR + conanrun env
- 结果: `make check` → check 框架 `100%: Checks: 85, Failures: 0, Errors: 0`,
  automake 层 `# PASS: 1` (test 计数单位: check test case, 取数
  `grep -cE ':(P|F):' test/check_cjose.log`)
- VPATH 构建注意: 上游 test/Makefile.am 的 AM_CPPFLAGS 只带
  `-I$(top_builddir)/include`, `#include <cjose/util.h>` 在 VPATH 下找不到
  `top_srcdir/include/cjose/util.h` → `make check CPPFLAGS="-I<src>/include -I<src>/src"`
  命令行变量补齐 (不改上游测试文件; in-tree 构建不受影响, conan basic_layout 用 in-tree)

## test_package

- 真实消费者 C 程序 (CMake, find_package(cjose CONFIG)): cjose_version 校验、
  base64url 往返 (RFC 4648 §5 向量)、header set/get、HS256 JWS
  import→sign→export→import→verify→明文一致 (上游 check_jws.c 的 oct JWK 向量)
- 4 用例全过, 输出 `CJOSE TEST PACKAGE OK (version 0.6.2.7)`
- conanfile package_info 声明 `cpp_info.requires = ["jansson::jansson", "openssl::openssl"]`
  与上游 cjose.pc 的 `Requires:` 对齐 (CMakeDeps 为消费方拉齐传递依赖)

## 已知限制

- 无 (上游测试 85/85, test_package 4/4)
- R8 检查: 两个补丁均无条件编译, 无 `__OHOS__` 平台分支; 0001 是设备级文件系统
  行为修正 (HMDFS UID 映射), 无法用运行时探测表达 — configure 生成物内的
  umask 常量不依赖平台能力探测
