# librepo

librepo 是 RPM 软件栈（dnf/libdnf 体系）的仓库下载库：基于 libcurl 提供 rpm-md
仓库（repomd/metalink/mirrorlist）的下载与增量更新 API，支持 GPG 签名校验
（gpgme）、zchunk 分块下载与 metalink 镜像选择。

## OHOS 适配

- **构建系统**: CMake（原生构建，非交叉编译；clang 15 / OHOS 6.0 aarch64）
- **依赖解析**: 全部依赖统一走 pkg-config——上游 CMake 的 `FIND_PACKAGE(CURL)`
  与捆绑的 KDE 时代 `FindGpgme`（依赖 gpgme-config 脚本）在 OHOS 上不可用，
  补丁改写为 `PKG_CHECK_MODULES`
- **关闭项**: SELinux 标签（无 libselinux）、Python 绑定、文档、examples
- **启用项**: gpgme OpenPGP 校验、zchunk 1.5.2 分块下载、上游 check 测试套件

## 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| glib | 2.84.0.1 | 事件循环/异步基础设施（gio/gobject 传递依赖） |
| libxml2 | 2.15.3 | repomd/metalink XML 解析 |
| curl | 8.15.0.1 | HTTP/HTTPS 下载 |
| openssl | 3.5.6.1 | libcrypto 校验和计算 |
| gpgme | 1.24.0 | OpenPGP 签名校验（内部链 libassuan/libgpg-error） |
| zchunk | 1.5.2 | zck 分块下载 |
| check | 0.15.2 | 上游测试套件（test_requires） |

## 功能验证

```bash
ctest                                  # 上游 check 套件（test_main）
./test_librepo                         # 消费者测试，期望输出 LIBREPO_CONSUMER_OK
pkg-config --modversion librepo        # 期望输出对应版本号（1.20.0 / 1.18.0）
```

## 版本

| 版本 | 状态 | 归档 |
|------|------|------|
| 1.20.0 | published (2026-09-29) | `archives/l/librepo/1.20.0/` |
| 1.18.0 | building (2026-10-08) | `archives/l/librepo/1.18.0/` |

### 1.18.0 适配要点

- cmake 4 构建上游 `cmake_minimum_required(2.8.5...3.26)` 需
  `CMAKE_POLICY_VERSION_MINIMUM=3.5`
- glib/libxml2/zchunk/openssl/check 走 `PkgConfigDeps`；`zck` 与 `libxml-2.0`
  的 pkg-config 名与制品包名不一致，配方补转发 `.pc`
- 自带 KDE 版 `FindGpgme` 依赖 gpgme-config：预置 `GPGME_INCLUDES` /
  `GPGME_VANILLA_LIBRARIES` 缓存变量绕过；`FindCURL` 用 `CURL_LIBRARY` /
  `CURL_INCLUDE_DIR` 指向 conan 的 curl 包
- 测试 scratch 目录 `/tmp/librepoXXXXXX` 在 OHOS 只读，补丁改用 `g_get_tmp_dir()`
- `ENABLE_SELINUX=OFF`（OHOS 无 libselinux）、`ENABLE_PYTHON=OFF`
- 共享库 `cmake --install` 会改写 DT_RUNPATH 使 lld 写入的 `.codesign` 失效：
  安装后按 E077 四步重签
- 逐项证据与上游测试口径见 `archives/l/librepo/1.18.0/notes.md`

## 参考

- 上游仓库: https://github.com/rpm-software-management/librepo
- 归档: archives/l/librepo/
