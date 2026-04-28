# boxes 2.3.1 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-04-13
- 编译器: clang
- 状态: partial

## 编译步骤
1. 在 vendor/ 编译 libunistring 1.0 和 PCRE2 10.40
2. 应用补丁（修改 Makefile + boxes.c stub ncurses）
3. `make build CC=clang`

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 gcc | CC=gcc 赋值 | 改为 CC?=gcc |
| 2 | libunistring configure 不识别 HarmonyOS | 缺少平台检测 | 更新 config.guess/config.sub |
| 3 | PCRE2 config.sub 不识别 ohos | OS 不在白名单 | 使用 --build=aarch64-unknown-linux-gnu |
| 4 | ncurses 编译困难 | configure 创建乱码目录 | stub 绕过，固定 80x24 |
| 5 | strip 命令缺失 | 系统 strip 不可用 | 使用 llvm-strip |

## 验证结果
```bash
echo "Hello World" | boxes  # ✅
echo "Test" | boxes -d shell  # ✅
echo "Hello" | boxes | boxes -r  # ✅
```

## 注意事项
- ncurses 被绕过，终端列数/行数固定为 80/24
- 需 flex/bison 工具
