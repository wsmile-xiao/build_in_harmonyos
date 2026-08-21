# vamp-plugin-sdk 2.10.0 编译笔记

## 概述

- 软件: vamp-plugin-sdk 2.10.0
- 构建系统: Autotools (configure.ac + Makefile.in)
- 编译日期: 2026-08-19
- 状态: built（本地验证通过，未上传）
- 分支: feat/vamp-plugin-sdk-2.10.0
- 执行: pc2-9 (r02 连续适配本地闭环)

## 源码

- 官方仓库: https://github.com/vamp-plugins/vamp-plugin-sdk
- 发布版本: 2.10.0 (2020-05-18)
- 源码归档: codeload 标签 tar.gz
  - URL: https://codeload.github.com/vamp-plugins/vamp-plugin-sdk/tar.gz/refs/tags/vamp-plugin-sdk-v2.10
  - SHA-256: b552bc91817294c7f90ea07d70938642ebf15d5e3bafc81cf7d55efab9995399
  - 文件大小: 316165 字节
- 许可证: BSD-3-Clause (COPYING)
- 注: github.com 直连超时；codeload.github.com 可达，使用官方标签归档并核验 SHA-256

## 依赖

- 无强制第三方依赖（第 1 轮 dependency_complete）
- 可选 simple-host 路径（libsndfile）保持禁用：--disable-programs

## 构建配置

- configure 参数: --disable-programs（核心 SDK 库）
- 编译器: clang/clang++ 15.0.4 (OHOS aarch64)
- 构建目标: sdk（libvamp-sdk.a/.so + libvamp-hostsdk.a/.so）
- 产物: 头文件 vamp/、vamp-sdk/、vamp-hostsdk/；libvamp-sdk.a、libvamp-hostsdk.a；pkgconfig 三个 .pc

## 测试

- 上游测试入口: test/run-test-plugin-regression.sh + `make test`（依赖 plugins host）
- 本轮未执行原因:
  1. vamp-simple-host 需 libsndfile（host/vamp-simple-host.cpp:56）
  2. regression 脚本引用独立仓库 vamp-test-plugin，SDK tarball 不含
- test_package 有效验证: PluginLoader 实例化 + composePluginKey 断言，通过

## OHOS 平台约束记录

1. TMPDIR=$HOME/tmp 已使用（/tmp 只读）
2. CC=clang CXX=clang++（无 GCC）
3. sign-elf: 静态构建无 ELF 需签名；test_package 可执行文件已用 binary-sign-tool 签名（.codesign 验证通过）
4. HMDFS 软链接: 上游 install 目标用 rm -f && ln -s（与 HMDFS 兼容），配方 package() 同样使用
5. SELinux/权限: autoconf `umask 077 && mktemp -d` 创建 0700 临时目录（属主被强制为 20001006），非属主 euid 无法写入 → configure 失败。解决方案: 配方 build() 内置 mktemp shim（umask 002）前置到 PATH（非 chmod 路径）
6. make jobserver mkfifo 被拒（Operation not permitted）→ 使用 make -j1
7. 裁剪内核影响: 无

## 知识沉淀

- HMDFS 下 autoconf mktemp umask 077 临时目录权限问题及 shim 解决方案（已记录 manifest.yaml）
- conan AutotoolsToolchain + basic_layout 在 OHOS 上生成 build-release/ 分离构建目录导致相对路径失效 → 改为树内构建

## 门禁结果

1. 本地编译: 通过（conan create exit 0）
2. 上游测试核验: 识别入口，未执行（原因如上），test_package 补足
3. 新增/替代测试: test_package 通过
4. 依赖检查: 无强制第三方依赖
5. conan create: 通过
6. conan-verify: 通过（G0-G4 PASS）
7. finish: 部分完成（W3 通过，close-archive 补 notes.md 后重跑）
8. W3 本地 CI: 通过（.ci-result.json 已生成）
9. PR 文件原子性: 仅目标库目录变更

## 未执行/未完成

- 上游 regression 测试: 未执行（需 libsndfile host + 独立 vamp-test-plugin 仓库）
- conan upload / 远端发布: 本轮禁止远端动作
- submit / push / PR / Issue: 本轮禁止
---

**编译结束**: 2026-08-19 20:37
**最终状态**: built
