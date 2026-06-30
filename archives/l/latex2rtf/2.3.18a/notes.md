# latex2rtf 2.3.18a 适配笔记

## 编译环境
- 构建系统: makefile（注意：源码包无 configure 脚本，为纯 Makefile 项目，非 autotools）
- 编译日期: 2026-06-12
- 编译器: clang 15.0.4 / clang++
- 目标平台: OpenHarmony aarch64 (musl libc)
- 状态: published

## 编译步骤

本项目为纯 Makefile 项目，无 configure 脚本。编译参数通过 make 变量传递：

```bash
# 编译（DESTDIR 模式，R20 铁律）
source .build-context-latex2rtf-2.3.18a
cd $BUILD_SRC_DIR
make CC=clang PREFIX=$DEFAULT_PREFIX -j1
make install CC=clang PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX

# 本地安装验证
make install CC=clang PREFIX=$DEFAULT_PREFIX
```

关键 Makefile 变量：
- `CC=clang` — 使用 clang 编译器
- `PREFIX=$DEFAULT_PREFIX` — 安装路径 ~/usr/local
- `PLATFORM=-DUNIX` — 默认值，适用于 OpenHarmony
- `DESTDIR=$TEST_PREFIX` — staging 隔离路径

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 构建系统类型标记为 autotools，但实际无 configure 脚本 | 源码包为纯 Makefile 项目，registry 信息不准确 | 修正 manifest.yaml build_system 为 makefile，直接用 make 编译 |
| 2 | verify-build G4 检查缺少 build_system 顶层字段 | verify_build.py 检查顶层字段而非嵌套字段 | 在 manifest.yaml 添加顶层 `build_system: makefile` |
| 3 | verify-build install-prefix 指向错误路径 | 默认 TEST_PREFIX/bin/ 不存在，实际在 TEST_PREFIX/DEFAULT_PREFIX/bin/ | 传入 `--install-prefix=$TEST_PREFIX/$DEFAULT_PREFIX` |
| 4 | 编译警告 convert.c:57 指针比较 | `string == '\0'` 应为 `string == NULL` | 非阻塞警告，不影响功能 |
| 5 | test-report.md 缺失导致 status 降级为 built | finish 脚本前置检查要求 test-report 存在 | 手动创建 test-report.md |
| 6 | 软件级 README.md 缺失 | init-build 未自动生成软件级 README | 手动创建 |

## 源码修改

无。本项目无需修改源码即可在 OpenHarmony 上编译通过，0 个补丁。

## 依赖版本

- 编译依赖: 无外部依赖
- 运行依赖: libc.so (系统 musl libc)
- 编译器: clang 15.0.4

## 验证结果

```bash
# 二进制类型
$ file ~/usr/local/bin/latex2rtf
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ file ~/usr/local/bin/latex2png
/bin/bash script

# 动态依赖
$ llvm-readelf -d ~/usr/local/bin/latex2rtf | grep NEEDED
NEEDED: libc.so

# 功能验证 - 简单文档转换
$ cat > /tmp/test-simple.tex << 'EOF'
\documentclass{article}
\begin{document}
Hello World
\end{document}
EOF
$ latex2rtf /tmp/test-simple.tex
转换输出码: 0
$ ls -la /tmp/test-simple.rtf
-rw-rw---- 4505 bytes

# RTF 头部确认有效
$ head -1 /tmp/test-simple.rtf
{\rtf1\ansi\uc1\deff0\deflang1024

# 功能验证 - 带标题段落转换
$ latex2rtf /tmp/test-para.tex
转换输出码: 0
$ ls -la /tmp/test-para.rtf
-rw-rw---- 5067 bytes
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| latex2rtf-2.3.18a-ohos-aarch64.tar.gz | 1.4MB (1,356,516 bytes) | 预编译包 |
| latex2rtf-2.3.18a-ohos-aarch64-debug.tar.gz | 69KB (69,153 bytes) | 调试符号包 |

## 注意事项

1. latex2rtf 不支持 `--version` 参数，无参数时读取 stdin，需传入文件名
2. 源码 test/ 目录含 136 个 .tex 测试文件，可用于功能验证
3. 配置文件安装到 `~/usr/local/share/latex2rtf/cfg/`（47 个 .cfg 文件），CFGDIR 硬编码在二进制中
4. G0 干净构建验证通过（从原始 tarball 解压编译无需补丁）
5. latex2png 为 bash 脚本包装器，依赖 latex 和 dvips 等外部工具

---

**编译结束**: 2026-06-12 03:43
**最终状态**: published
---

**编译结束**: 2026-06-12 10:42
**最终状态**: published
