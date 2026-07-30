# defaultbrowser 1.1 适配笔记

## 编译环境
- 构建系统: custom
- 编译日期: 2026-07-13
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 获取上游源码: `defaultbrowser-1.1.tar.gz`。
2. 检查源码实现，确认依赖 macOS Foundation/ApplicationServices framework。
3. OpenHarmony 不提供这些系统框架，因此不进行原生编译。
4. Conan 配方打包上游源码到 `share/defaultbrowser`，并安装占位 `bin/defaultbrowser`，运行时明确提示该工具仅适用于 macOS。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无法在 OpenHarmony 编译上游程序 | 上游 Objective-C 代码依赖 macOS Foundation/ApplicationServices | 归档源码并提供 macOS-only 占位命令，避免误报可用能力 |

## 源码修改

无补丁。

## 依赖版本

无外部构建依赖。

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify defaultbrowser 1.1
# PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2 配方 |
| conandata.yml | 上游源码 URL 与 sha256 |
| test_package/ | 消费者测试，验证 macOS-only 提示 |

## 注意事项

该包是 macOS-only 工具，在 OpenHarmony 上预期不可提供真实默认浏览器切换能力。归档目的是记录不可移植原因，并让安装后的命令给出清晰提示。

## 最终状态

COMPLETED: defaultbrowser 1.1 已完成归档与验证。
