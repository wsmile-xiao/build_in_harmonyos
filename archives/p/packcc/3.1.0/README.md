# packcc 3.1.0

## 软件简介

packcc 是一个用于 C 语言的解析器生成器（Parser Generator），基于 PEG（Parsing Expression Grammar）语法。

- **主页**: https://github.com/arithy/packcc
- **许可证**: MIT
- **语言**: C
- **构建系统**: CMake

## 编译状态

| 项目 | 值 |
|------|------|
| 版本 | 3.1.0 |
| 状态 | published |
| 编译日期 | 2026-06-30 |
| 编译器 | Clang 15.0.4 |
| 构建类型 | Release |
| Conan 验证 | 8/8 门禁通过 (G0-G4 + L2/L4/L5) |

## 产物

- `bin/packcc` — 解析器生成器可执行文件 (ELF 64-bit ARM64)
- `share/packcc/import/` — 7 个 .peg 导入文件 (char/code/util 目录)

## 文件清单

| 文件 | 说明 |
|------|------|
| `conanfile.py` | Conan 配方（CMake 构建，R26 静态链接） |
| `conandata.yml` | Conan 数据文件（含 sha256 校验和） |
| `manifest.yaml` | 归档清单（编译配置、状态、知识沉淀） |
| `notes.md` | 适配笔记（编译步骤、问题与解决方案） |
| `reports/test-report.md` | 测试报告（make check 结果 + Conan 验证结果） |
| `reports/conan-verify-report.md` | Conan 验证详细报告 |
| `reports/conan-create.log` | conan create 构建日志 |
| `reports/baseline.json` | 产物基线指纹 |
| `test_package/` | Conan test_package（smoke test） |
| `.staging-verified` | Staging 验证标记 |
| `.conan-verified` | Conan 验证标记 |

## 使用方法

```bash
# 生成解析器
packcc -o parser input.peg
# 生成 parser.h 和 parser.c

# 编译生成的解析器
cc -I. parser.c main.c -o parser
```
