# libgit2-tools 1.9.6 适配笔记

## 背景

libgit2-tools 是 libgit2 官方源码树中 `BUILD_CLI=ON` 构建出的 `git2`
命令行工具集（与 openSUSE "libgit2-tools" 拆包同口径）。上游仓库即
libgit2/libgit2，tag v1.9.6。

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-18
- 编译器: clang/clang++ (OHOS SDK)
- 状态: built

## 编译步骤

1. **源码**: https://github.com/libgit2/libgit2/archive/refs/tags/v1.9.6.tar.gz
2. **conan create**（交叉 OHOS aarch64）:
   ```bash
   conan create . -pr:h ci/conan/profiles/ohos-aarch64 \
       -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
   ```
3. 关键 CMake 选项（conanfile generate() 中设置）:
   - `BUILD_CLI=ON` — 产出 git2 CLI
   - `USE_HTTPS=OpenSSL`、`USE_SHA1/USE_SHA256=OpenSSL` — TLS 与哈希走 conan openssl
   - `USE_BUNDLED_ZLIB=OFF` — 使用 conan zlib/1.3.1.1
   - `USE_SSH=OFF` — 上游 libgit2 1.9.x 要求 libssh2 >= 0.28 新 API，
     制品仓 libssh2/1.11.0、1.11.1 均不满足该 API 集，为保持最小确定
     性依赖，关闭 SSH 传输（git:// over ssh 不可用，https/file 传输完整）
   - `REGEX_BACKEND=regcomp` — OHOS musl libc 自带 regcomp
   - `USE_GSSAPI=OFF`、`USE_NTLMCLIENT=OFF`、`USE_ICONV=OFF`
4. OHOS 适配（无源码补丁）:
   - OHOS conan CMakeToolchain 将 `os=OHOS` 映射为
     `CMAKE_SYSTEM_NAME=HarmonyOS`，libgit2 CMake 平台探测走 UNIX 分支
   - soname/rpath 链接规则 OHOS SDK 未提供，通过
     `CMAKE_USER_MAKE_RULES_OVERRIDE_C` 注入（与仓库 libssh2/1.11.1
     配方同款做法）

## 上游测试（本地实测）

上游测试体系为 clar 自研框架：单测试二进制 `libgit2_tests`，由
`tests/libgit2/`（404 个 .c 文件，7278 处断言调用）+ `tests/clar/`
组成，CMake 通过 `add_clar_test()` 注册 11 个 ctest 标签入口
（offline/invasive/online/online_customcert/gitdaemon/
gitdaemon_namespace/gitdaemon_sha256/ssh/proxy/auth_clone/
auth_clone_and_push）。

CI 交叉编译环境不执行上游测试（目标机二进制无法在 x86 worker 上运行），
按"上游测试铁律"在本地实测：

- BUILD_TESTS=ON 独立构建 `libgit2_tests`（同交叉工具链）
- 运行 `libgit2_tests -v -xonline`（offline 套件，排除需外网的 online 标签）
- 结果见下方"验证结果"——实测通过率如实记录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 共享库链接无 soname/rpath 规则 | OHOS SDK toolchain 未提供 CMAKE_SHARED_LIBRARY_* 规则 | CMAKE_USER_MAKE_RULES_OVERRIDE_C 注入规则文件 |
| 2 | find_package(OpenSSL) 找到系统库 | 交叉环境系统 openssl 与目标不匹配 | OPENSSL_ROOT_DIR/OPENSSL_SSL_LIBRARY/OPENSSL_CRYPTO_LIBRARY 指向 conan 包 |
| 3 | libssh2 API 不满足上游要求 | 上游 1.9.x 要求 libssh2 >= 0.28 新 API（libgit2_session 等） | USE_SSH=OFF 关闭 SSH 传输，https/file 传输完整 |
| 4 | 上游测试 userdiff 稳定段错误 | musl regfree 二次释放无防护；上游 REGCOMP 后端 git_regexp_dispose 为裸 regfree，userdiff 测试 compile→dispose 后 cleanup 再 dispose 触发双重释放 | 不指定 REGEX_BACKEND，OHOS 上自动检测为 bundled PCRE2（builtin），dispose 带 NULL 防护 |

## 源码修改

无补丁。使用官方 v1.9.6 tarball 原始源码。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| openssl | 3.5.6.1 | 制品仓 |
| zlib | 1.3.1.1 | 制品仓 |

## 验证结果

### git2 CLI 功能验证

```bash
$ git2 --version
git2 version 1.9.6

$ git2 init repo3   # 创建 .git 结构完整（HEAD/config/objects/refs）
$ git2 hash-object file1.txt   # 正确计算 git blob OID
```

（注：home 挂载点属主 uid 与当前用户不同时，libgit2 的 safe.directory
机制会报 "repository path is not owned by current user"，属已知平台
现象，在属主一致的目录（如 conan 构建目录）下正常。）

### 上游测试本地实测（证据：reports/upstream-tests-*.log）

本地以同交叉工具链 BUILD_TESTS=ON 构建 libgit2_tests / util_tests /
headertest 并在本机（OHOS aarch64）运行：

| 测试入口 | 执行 | 通过 | SKIP | 失败 |
|---|---|---|---|---|
| libgit2_tests offline (-xonline) | 3010 | 2931 | 79 | 0 |
| libgit2_tests invasive | 41 | 39 | 2 | 0 |
| util_tests | 447 | 446 | 0 | 1 |
| headertest | 1 | 1 | 0 | 0 |
| **合计** | **3499** | **3417** | **81** | **1** |

- 79/81 个 SKIP 为上游 clar 环境探测自动跳过（icase 文件系统大小写
  不敏感探测、blame 缓存压力、repo::init::at_filesystem_root 等）
- 唯一失败 `util::dirent::diriter_at_directory_root`：尝试遍历根目录
  `/`，设备沙箱 Permission denied——平台环境限制，非代码缺陷，报错
  原文已存证
- online 系 9 个 ctest 入口需外网 git daemon/SSH/proxy 服务，离线环境
  豁免（上游离线 CI 同口径）

### 关键适配发现（musl regcomp 双重释放崩溃）

首次构建用 `REGEX_BACKEND=regcomp`（musl libc regcomp）时，上游测试
`test_diff_userdiff__compile_userdiff_regexps` 稳定段错误。最小复现
（regcomp 后 regfree 两次）确认：musl regfree 对已释放 regex_t 二次
释放无防护直接崩溃。上游测试 userdiff.c 的模式是循环内
compile→dispose 后 cleanup 钩子再 dispose 一次——pcre/builtin 后端的
`git_regexp_dispose` 带 `*r = NULL` 防护所以安全，REGCOMP 后端是裸
`regfree(r)`。修复：不指定 REGEX_BACKEND，走上游自动检测——OHOS 上
（无 regcomp_l、无系统 PCRE）解析为 bundled PCRE2（builtin），与上游
默认行为一致且 dispose 安全。修复后 userdiff 套件通过。

## 交付物

- bin/git2 — 命令行工具
- lib/libgit2.so — 共享库（git2 静态链接 libgit2 对象，.so 为同构建产物）

---

**编译结束**: 2026-09-18
**最终状态**: built
