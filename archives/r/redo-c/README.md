# redo-c

## 简介
redo-c 是 Daniel J. Bernstein 设计的 redo 构建系统的一个单文件 C 实现（约 994 行，
零外部依赖，CC0 公有领域）。它是命令行工具：`redo`（无参数等价 `redo all`），以及
符号链接 `redo-ifchange`、`redo-ifcreate`、`redo-always`。

## OHOS 适配
- **构建系统**: 上游使用 .do 文件（redo 自举构建）。本配方直接在 source 目录用
  Conan 提供的 clang 编译 redo.c 生成 `redo` 可执行文件（等价 redo.do 的
  `cc -O2 ... -o redo redo.c`），再按 links.do 创建三个符号链接。
- **依赖**: 无（零外部依赖，纯 POSIX + 内嵌 SHA-256 实现）。
- **补丁**: 无（未改上游源码）。
- **产物**: bin/redo 可执行文件 + bin/redo-ifchange、bin/redo-ifcreate、
  bin/redo-always 符号链接。

## 功能验证
```bash
redo -h            # usage: redo [-kfsx] [-jN] [-Cdir] [TARGETS...]
# 端到端 .do 构建验证见 test_package（hello.do → redo hello → 校验目标内容）
```

## 参考
- 上游: https://github.com/leahneukirchen/redo-c （tag v0.3, commit c19b03dc）