# postsrsd 2.0.11 适配笔记

## 软件概述
postsrsd 是 Postfix 邮件服务器的 SRS（Sender Rewriting Scheme）守护进程，用于邮件转发时改写
发件人地址以保持 SPF 校验通过。产物为可执行文件 `postsrsd`（安装到 sbin/bin）。

## 编译环境
- 构建系统: cmake（3.14+；上游 CMakeLists 用 FetchContent 内置构建依赖）
- 编译日期: 2026-09-26
- 编译器: clang/clang++（OHOS arm64）
- 状态: built

## 依赖分析（W0 结论）
| 依赖 | 版本 | 类型 | 制品仓状态 | 处理 |
|---|---|---|---|---|
| libConfuse | 3.3 | 强制（CMake FetchContent 无条件下载并 ExternalProject 静态编译） | **未发布**（conan install --requires=confuse/3.3 → Unable to find in remotes） | conanfile source() 下载 confuse-3.3.tar.gz 到 third_party/confuse，FETCHCONTENT_SOURCE_DIR_CONFUSE 指向本地；build() 内 replace 修复 config.sub 与 configure 后经 ExternalProject 静态编入 |
| Check | 0.15.2 | 测试框架（BUILD_TESTING=ON 时 FetchContent） | 本地缓存有 recipe | 同法本地化 third_party/check，FETCHCONTENT_SOURCE_DIR_CHECK 指向本地 |
| Hiredis / LibMilter / sqlite3 | - | 可选（WITH_REDIS/WITH_MILTER/WITH_SQLITE，默认 OFF） | 不适用 | 保持 OFF，不启用 |

无 conan requires 外部依赖；W0 无阻塞。

## 编译步骤
```bash
# 本地开发验证（conan create 由配方驱动，等价步骤）：
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
make -j4
ctest --output-on-failure    # 上游测试 7/7 通过
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cannot guess build type`（confuse configure） | confuse 3.3 自带的 config.sub(2018) 不识别 aarch64-unknown-linux-ohos，config.guess 无法识别 HarmonyOS | patches/0001：cmake/utils.cmake 的 add_autotools_dependency 定义 OHOS_TRIPLET 并传 `--build/--host=aarch64-unknown-linux-ohos`，跳过 config.guess；conanfile build() 里对 confuse 源码 config.sub 注入 linux-ohos* 识别（同 bmon E072/E122 范式） |
| 2 | `can't create ./confXXXXXX/subs1.awk: Permission denied`（confuse config.status） | HMDFS 上 `umask 077 && mktemp -d` 创建的临时目录权限为 drwx--S---，owner 不可写 | conanfile build() 里 replace 掉 configure 中 `umask 077 &&` 前缀（mktemp/mkdir 直接调用），验证目录可写（同 E114/E060 根因） |
| 3 | 上游 ExternalProject PATCH_COMMAND 跑 autoreconf 重新生成 configure，会覆盖修复 | autoreconf 会基于 configure.ac 重新生成 configure，丢失对生成的 configure 的直接修改 | patches/0001 将 PATCH_COMMAND 置空，直接使用 tarball 自带 configure |
| 4 | test_netstring 段错误（netstring_io_test SIGSEGV） | OHOS 上 tmpfile() 返回 NULL（musl 硬编码 /tmp，只读），测试未判空直接使用 | patches/0004：tests/unit/test_netstring.c 新增 make_temp_file()（$TMPDIR + mkstemp），替换 tmpfile() 并加断言 |
| 5 | test_socketmap 失败（`Operation not permitted`） | OHOS 禁止 **文件系统路径** AF_UNIX bind（EPERM；TCP/UDP bind 亦 errno=99） | 补丁 0002+0003（E461）：`endpoint.c` 支持 `unix:abstract:name`（abstract 命名空间 socket，bind 地址长度用 `offsetof+1+namelen`），`socketmap.py` 测试改用 abstract socket 并通过连接探测就绪 → **7/7 通过** |
| 6 | package() 安装 systemd unit 到 /etc 无权限 | 上游 INSTALL_SYSTEMD_SERVICE=ON 默认将 service 装到 /etc/systemd/system | conanfile generate() 设 INSTALL_SYSTEMD_SERVICE=OFF、GENERATE_SRS_SECRET=OFF |
| 7 | 本机 cmake/.harmonybrew 符号解析失败（_ZTINSt4__n119__shared_weak_countE） | 本机环境 libc++ ABI 不匹配问题 | 用 /data/service/hnp/bin/cmake；SDK lld 需 libxml2，conanfile `_build_env()`（OHOS_SDK_LLVM_LIB 环境变量或 glob 探测 SDK llvm/lib）在 build()/package() 中显式设置 LD_LIBRARY_PATH |

## 源码修改
- patches/0001-cmake-utils.cmake.patch：add_autotools_dependency 传 --build/--host（AUTOTOOLS_BUILD_HOST_ARGS，OHOS/HarmonyOS 检测）、PATCH_COMMAND 置空（禁 autoreconf）
- patches/0002-src-endpoint.c.patch：unix endpoint 支持 unix:abstract:name（abstract AF_UNIX socket，E461），bind 地址长度 offsetof+1+namelen
- patches/0003-tests-blackbox-socketmap.py.patch：blackbox socketmap 测试改用 unix:abstract:name 与连接探测
- patches/0004-tests-unit-test_netstring.c.patch：tmpfile() → $TMPDIR mkstemp

（confuse 依赖源码的 config.sub/configure 修改在 conanfile build() 内 replace_in_file 处理，不打入 patches/）

## 依赖版本
- libConfuse 3.3（源码 vendored，静态编译）
- Check 0.15.2（源码 vendored，测试框架）
- 系统库：libc/libm/pthread（OHOS SDK）

## 验证结果
```bash
# 本地 ctest（上游 7 项）：
#   test_netstring/test_sha1/test_util/test_database/test_srs2/test_config → 6 PASS
#   test_socketmap → 通过（abstract socket 修复，E461）
#   通过率 7/7 = 100%
# conan-verify（G0-G4 + L2/L4/L5 八门禁）→ 全 PASS
# test_package：postsrsd -v → "2.0.11"；postsrsd -h → 含 "PostSRSd" → PASS
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py + conandata.yml | Conan 配方（application 类型，FetchContent 依赖本地化） |
| commands.json | 命令行工具声明（type=tool, binary） |
| test_package/ | postsrsd -v/-h 功能验证 + MANIFEST.yml 上游测试声明 |

## 注意事项
- OHOS 禁止**文件系统路径** AF_UNIX socket bind（EPERM）：postsrsd 的 socketmap/milter 端点在 OHOS 上
  使用 `unix:abstract:name`（abstract 命名空间，E461），bind 地址长度用 offsetof+1+namelen；
  SRS 核心编解码逻辑（srs2.c/sha1.c）由单元测试覆盖，socketmap 端到端由 blackbox 测试 7/7 验证。
- FetchContent 依赖须本地化（FETCHCONTENT_SOURCE_DIR_*），否则 CI/离线环境 configure 期联网失败。
---

**编译结束**: 2026-09-27 20:10
**最终状态**: built
