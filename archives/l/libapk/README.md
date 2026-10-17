# libapk - Alpine Package Keeper core library

## 简介
libapk 是 Alpine Linux 包管理器 apk-tools 的核心库，提供版本比较、包数据库、依赖求解、签名校验、仓库解析与解包等包管理引擎能力。本目录适配上游 apk-tools 3.0.6 中的 libapk 部分。

## OHOS 适配
- 使用 Meson 构建（`meson configure/compile/install`），ninja 后端
- 加密后端固定 `openssl`，压缩依赖 `zlib` 与 `zstd`，均引用 Conan 制品仓版本（openssl/3.5.8.1、zlib/1.3.1.1、zstd/1.5.7.1（OHOS 后缀版本，conancenter 无此号故不会被遮蔽））
- 禁用 `docs/help/lua/python`（需要 scdoc/lua/python 绑定，OHOS 包构建不需要）
- 禁用 meson 原生 `tests`（cmocka 未发布 + shell/solver 用例依赖目标机 shell 环境），改由配方 build() 编译真实 libapk 并跑上游 `test/unit/version.data` 可比 harness，证据落盘 `res/upstream_test_result.json`
- 共享库构建后用 llvm-objcopy 剥旧 `.codesign` 并 binary-sign-tool 自签，保证 OHOS dlopen 可加载

## 功能
- 版本校验与比较（apk_version_validate/compare/match）
- 二进制大对象操作（apk_blob_*：split/contains/hash）
- 包数据库、依赖求解、签名校验、仓库解析（随 libapk.so 一并提供）

## 依赖关系
- 编译依赖：openssl/3.5.8.1、zlib/1.3.1.1、zstd/1.5.7.1（OHOS 后缀版本，conancenter 无此号）
- 构建工具：meson、ninja、pkg-config（由 CI/真机 conan 环境提供）

## 参考资料
- 上游仓库：https://gitlab.alpinelinux.org/alpine/apk-tools
- 镜像：https://github.com/alpinelinux/apk-tools
- 许可证：GPL-2.0-only
