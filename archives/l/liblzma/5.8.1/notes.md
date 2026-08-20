# liblzma 5.8.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-24
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `conan source` 获取 xz-5.8.1 源码
2. 应用补丁：`config.guess` 添加 OHOS 平台识别
3. `./configure --disable-scripts`（禁用依赖 /bin/sh 的脚本）
4. `make` 构建 liblzma.so/liblzma.a 及工具
5. `make check` 运行上游测试套件（13 个测试程序，18 个断言）
6. `make install` 安装产物

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 失败：临时目录权限 drwx--S--- | autoconf AS_TMPDIR 在 `umask 077` 下调用 `mktemp -d`/`mkdir`，setgid 继承 + 无组执行位 = MAC 阻止写入 | 创建 mktemp wrapper，用 `mkdir -m 775` 创建 `drwxrws--x` 目录（chmod 在 OHOS 不生效，须用 `-m` 在创建时设置） |
| 2 | xzdiff/xzgrep 脚本安装失败 | 脚本依赖 /bin/sh，HarmonyOS 无此路径 | `--disable-scripts` 跳过脚本安装 |
| 3 | xz 工具运行时找不到 liblzma.so | 动态链接库不在默认搜索路径 | extra_ldflags 添加 `-static`，工具静态链接 liblzma.a |

## 源码修改

- `patches/0001-build-aux-config.guess.patch`: 为 config.guess 添加 HarmonyOS（ohos）系统分支

## 依赖版本

无外部依赖。liblzma 是 XZ Utils 中的自包含压缩库。

## 验证结果

```bash
# L1: make check（上游测试套件）
make check
# 结果: 全部 13 个测试程序通过，18 个断言通过

# L2: ELF 格式与运行验证
file src/liblzma/.libs/liblzma.so.5  # ELF 64-bit aarch64
./src/xz/xz --version                 # xz (XZ Utils) 5.8.1
```

## 交付物

| 文件 | 说明 |
|------|------|
| liblzma.so.5.8.1 | 动态库（供消费者使用） |
| liblzma.a | 静态库（工具静态链接用） |
| lzma.h, lzma_detector.h | 公共头文件 |
| xz, lzmadec, lzmainfo | 命令行工具（静态链接） |

## 注意事项

- mktemp wrapper 仅在 `self.settings.os == "OHOS"` 时创建，不影响其他平台构建
- wrapper 用 `mkdir -m 775` 创建临时目录（`drwxrws--x`），绕过 `umask 077` 造成的 `drwx--S---` 权限问题
- `--disable-scripts` 为全局配置，跳过 xzdiff/xzgrep 等脚本（HarmonyOS 无 /bin/sh）
---

**编译结束**: 2026-07-24 15:52
**最终状态**: built
