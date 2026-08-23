# cde-static-bundler — 离线静态环境打包助手

## 边界声明（重要）

`cde-static-bundler` 是与 CDE 1.0.0 一同打包、但在 `feat/cde-1.0.0`
分支内**独立命名**的辅助 CLI。它只做**静态 ELF 元数据解析**与**显式指定
资源根目录的文件拷贝**，**不使用** CDE 的 ptrace 动态跟踪引擎、LD_PRELOAD、
运行时拦截、进程跟踪或调试器，也**绝不执行被检 ELF**。

它**不能**绕过 R05/R06 已确立的 OHOS ptrace 策略，也**不构成** CDE 的
运行时兼容等价物或单独的竞赛库/独立版本交付。本工具仅作为离线打包辅助。

## 接口

```text
cde-static-bundler scan --entry <ELF> --resource-root <dir> \
    [--resource-root <dir> ...] [--libdir <dir> ...] [--output <bundle-dir>]
```

- `--entry <ELF>`：待静态分析的 ELF（必填）
- `--resource-root <dir>`：显式提供的资源根目录，其内部普通文件将被拷入包（可重复）
- `--libdir <dir>`：额外的非系统依赖查找目录（可重复）
- `--output <dir>`：输出包目录（默认 `./cde-static-bundle`）

## 行为

1. **静态 ELF 解析**：读取 ELF class、字节序、机器架构、`PT_INTERP` 解释器、
   `DT_NEEDED`、`DT_RPATH`、`DT_RUNPATH`；拒绝非 ELF/畸形输入与不支持的
   混合架构。
2. **依赖解析**：仅从安全声明的查找位置（入口目录、DT_RPATH/DT_RUNPATH
   中的 `$ORIGIN` 解析、`--libdir`）递归解析非系统 `DT_NEEDED`；系统库按
   排除清单记录且从不拷贝；必需的非系统依赖无法解析时**硬失败**并写入
   manifest。
3. **拷贝策略**：只拷贝入口、已解析的非系统依赖，以及显式 `--resource-root`
   内的普通文件；拒绝路径穿越、绝对目标逃逸、不安全相对路径与符号链接逃逸；
   输出侧优先物化普通文件而非生成符号链接。
4. **manifest.json**：包含入口、架构、解释器、依赖图、拷贝文件（来源 + 
   SHA-256）、系统排除、未解析依赖、资源根与工具/版本元数据；存在必需未解析
   依赖时 `complete` 恒为 `false`。

## 构建

```bash
export TMPDIR="$HOME/tmp" CC=clang CXX=clang++
clang -Wall -Wextra -O2 -static -o cde-static-bundler cde-static-bundler.c
```

静态链接失败时保留首个精确错误并如实报告，不得把动态产物伪报为静态。

## 版本

TOOL_VERSION = 1.0.0.0（随 CDE 1.0.0 一起打包，不单独交付）
