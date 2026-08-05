# acpitool 0.5.1 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-08-04
- 编译器: clang/clang++ (CC=clang, CXX=clang++)
- 状态: built

## 编译步骤

```bash
./configure --prefix=/ --bindir=${prefix}/bin --sbindir=${prefix}/bin --libdir=${prefix}/lib --includedir=${prefix}/include
make -j1
make install DESTDIR=<staging>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 2005 版 config.guess 不包含 HarmonyOS/__OHOS__ 检测分支 | 添加 HarmonyOS 检测分支，输出 `aarch64-unknown-linux-ohos` |
| 2 | config.sub 不识别 ohos 三元组 | 2005 版 config.sub 未将 ohos 列为合法操作系统 | 添加 linux-ohos 到 maybe_os 模式、OS 白名单和 OS 处理分支 |
| 3 | configure 临时目录创建失败 | 构建环境当前目录 mktemp -d 创建临时目录后写入失败 | 移除 umask 077，直接用 mktemp -d 创建临时目录 |

## 源码修改

- patches/0001-config.guess-harmonyos.patch: config.guess 添加 HarmonyOS 系统识别
- patches/0002-config.sub-ohos.patch: config.sub 添加 ohos 三元组支持
- 注：configure 临时目录修改通过 conanfile.py 内联 sed 完成（第 58-60 行），无需独立补丁文件

## 依赖版本

无第三方 Conan 依赖（仅 musl libc 系统库）。

## 验证结果

```bash
# 编译验证
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# 编译通过，包已安装

# 运行时限制确认
ls /proc/acpi/  → MISSING (No such file or directory)
ls /sys/bus/acpi/  → MISSING (No such file or directory)

# Smoke test (acpitool -h)
acpitool -h  → 退出码 255（预期行为：ACPI 接口缺失，但帮助文本正常输出）
```

## 运行时限制（HarmonyOS PC 平台）

acpitool 依赖 /proc/acpi、/sys/bus/acpi 等 ACPI 事件接口，HarmonyOS PC（HongMeng Kernel 1.12.0）上述接口全部缺失（参见 DRAFT-acpid-acpi-missing，PR !3959）。编译验证通过，运行时无 ACPI 数据可读；知识库已记录此系统差异，不另建 draft。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/acpitool | ACPI 命令行查询工具 |

## 注意事项

- acpitool 在 HarmonyOS PC 上编译通过，但运行时无 ACPI 数据可读（ACPI 接口缺失）
- acpitool -h 仍可正常显示帮助文本，无需 ACPI 接口
- 已复用知识库 DRAFT-acpid-acpi-missing (PR !3959)，不另建 draft
---

**编译结束**: 2026-08-05 09:11
**最终状态**: built
