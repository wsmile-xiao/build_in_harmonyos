# akms 0.3.0 适配笔记

## 编译环境
- 构建系统: custom（纯 POSIX shell 工具，无 C 编译）
- 编译日期: 2026-08-10
- 编译器: 不适用（shell 脚本）
- 状态: built

## 编译步骤

1. `sh -n akms akms-build akms-runas akms.kernel-hook` — 校验脚本语法（无编译）
2. package() 直接复制脚本：bin/akms、libexec/akms/{akms-build,akms-runas}、share/kernel-hooks.d/akms.hook、etc/akms.conf
3. 上游 Makefile 的 man 目标需 asciidoctor（OHOS 无此工具）→ 跳过 man 生成

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 本地 finish W3 L1e 误判"假测试" | 本地 ohc-run finish 的 conan-verify 创建 @ohpcd/stable 缓存条目 + W3 build_and_test 的 create（unset user/channel → plain ref）产生两个条目，L1e 复跑解析到未破坏条目 | harness 假阳性；CI 上 build_and_test 独立运行只有一条目，L1e 正常（清缓存独立运行验证 exit=0） |

## 源码修改

无（无补丁，上游源码未改动）

## 依赖版本

无（纯 shell 工具，无外部依赖；运行时仅 /bin/sh）

## 验证结果

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64   # G2 PASS
conan-verify: G0-G4 + L2/L4/L5 PASS
build_and_test.sh akms/0.3.0（清缓存独立运行，CI 等价）  # L0/L1 PASS，L1e 确认真实依赖
test_akms.sh: PASS=6 FAIL=0（存在性 + 可执行 + --version 0.3.0 + --help + 2 helper）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/akms-0.3.0.tar.gz | 18KB | 上游 GitHub 源码 tarball（与 conandata.yml 一致） |

## 注意事项

- akms 是 Alpine 内核模块支持工具（DKMS for Alpine），其内核模块构建功能为 Linux 特定；本适配按工具打包脚本与配置，`akms --version/--help` 在 OHOS 正常运行
- 上游 man 页（adoc 源）因 OHOS 无 asciidoctor 未生成，脚本已按 upstream Makefile 布局安装
---

**编译结束**: 2026-08-10
**最终状态**: built
