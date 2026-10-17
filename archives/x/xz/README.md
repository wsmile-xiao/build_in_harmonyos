# XZ Utils

## 简介
通用数据压缩软件，提供高压缩比的 LZMA2/XZ 格式支持，包含 xz、lzma、xzcat 等工具。

## OHOS 适配
- 需修补 config.guess 的 HarmonyOS 识别（config.sub 已内置 ohos 三元组）
- autotools 构建；`--disable-scripts` 规避 OHOS 无 /bin/sh
- mktemp wrapper 绕过 OHOS 上 `mktemp -d` 的权限缺陷
- 交叉编译时程序用 libtool 的 `-all-static` 静态链接（裸 `-static` 会被 libtool 吞掉）
- 5.2.3: 3 个补丁（config.guess, config.sub, configure umask 修复）
- 5.6.2: 12 个补丁文件（含自动生成的构建文件）
- 5.8.1 / 5.8.3: 仅 1 个补丁（config.guess）

## 依赖
- 标准 C 库

## 功能验证
```bash
xz --version
echo "test" | xz | xz -d
```

## 版本
- 5.2.3: published (2026-06-25), 功能测试 67/67 PASS, liblzma API 完全正常
- 5.6.2: partial (2026-04-20)
- 5.8.1: built (2026-09-21), make check 18/18 PASS + liblzma API / xz CLI 往返 2/2 PASS
- 5.8.3: published (2026-09-11)
- 5.8.3.1 / 5.8.3.2: published / built

## 参考
- 官网: https://tukaani.org/xz/
