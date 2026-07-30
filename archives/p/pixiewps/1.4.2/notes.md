# pixiewps 1.4.2 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile，无 configure)
- 编译日期: 2026-07-27
- 编译器: clang
- 状态: success (待远端 CI 验证)

## 上游信息
- 仓库: https://github.com/wiire-a/pixiewps
- 许可证: GPL-3.0+
- 语言: C (C99)
- 功能: 离线 WPS 暴力破解工具 (pixie-dust attack)

## 依赖分析 (W0)
- 外部 Conan 依赖: 无
- 加密库: libtomcrypt + tomsfastmath 已内置源码树 (src/crypto/tc, src/crypto/tfm)
- 系统库: pthread (musl libc 内置，-lpthread 为兼容 stub)

## 编译步骤
```bash
# R33: CC 由 Conan conf 提供 (tools.build:compiler_executables:c)，通过 make 变量传递
make CC="clang" -j1
```

Makefile 关键变量:
- `CC` — 编译器，由 Conan conf 提供 (clang)，通过 make 命令行变量传递 (R33)
- `CFLAGS = -O3` — 上游默认优化级别
- `INTFLAGS = -std=c99 -I src/crypto/tc` — 内部编译标志
- `LIBS = -lpthread` — pthread 链接 (musl libc 兼容 stub)

## ELF 签名 (R38/E082)
- 构建产物 pixiewps 为可执行二进制，OHOS 要求 ELF 签名后才能执行
- package() 方法中调用 binary-sign-tool 进行签名
- 签名前使用 llvm-objcopy 移除 .codesign 段 (如有)
- 签名工具不存在时跳过 (CI worker 会补签)

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 | 源码无平台特定代码，纯 Makefile 项目直接构建 | 无需补丁 |
| 2 | ELF 签名 | OHOS 要求二进制必须签名才能执行 | package() 中调用 binary-sign-tool |

## 上游测试
- 上游无自动化测试套件 (Makefile 无 check/test target)
- test_package 以 `pixiewps -V` (版本输出) 和 `pixiewps -h` (用法屏幕) 烟雾测试覆盖
- `-V` 和 `-h` 按设计返回 ARG_ERROR(3)，test.sh 显式处理该退出码并验证输出字符串

## 验证结果
- `pixiewps -V` 输出 "Pixiewps 1.4.2" (待 CI 验证)
- `pixiewps -h` 输出用法屏幕 (待 CI 验证)
- L2 烟雾测试: --version/--help 返回非零退出码 (ARG_ERROR=3)，L2 为 warn (非阻塞)

## 注意事项
- 命令行工具，已声明 commands.json (R38)
- 加密库内置，制品仓无下游依赖链
- 首次运行可能弹窗确认 (鸿蒙安全机制)
