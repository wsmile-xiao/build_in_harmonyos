# E999 — 上游硬编码 /tmp 临时目录且不读 TMPDIR，OHOS /tmp 只读导致运行时崩溃

## 错误特征
```
podiff: cannot create temporary: Read-only file system
Abort trap (rc=134 / SIGABRT)
```
程序在"编译期一切正常、启动 --version/--help 也正常"，仅在真正需要写临时文件的运行路径（比对/转换）崩溃。

## 触发条件
- 构建系统: 任意（平铺 Makefile / autotools / cmake 均可能）
- 阶段: runtime / testing（test_package 实跑时暴露）
- 源码特征: `grep -n '"/tmp"' *.c` 命中硬编码常量；且全程无 `getenv("TMPDIR")`

## 根因分析
上游 C 程序把临时目录硬编码为 `"/tmp"`，未遵循 GNU TMPDIR 环境变量惯例。HarmonyOS PC 的 `/tmp` 只读（EROFS），`mkstemp()` 失败返回 -1，错误路径里 `abort()`（podiff 为 `error(...); abort;` 风格）直接 SIGABRT。**注意与 E002/E482 的区别**：那两条针对"程序读 TMPDIR 但环境未设"或"shell 自身临时文件"，本条程序根本不读 TMPDIR，纯设环境变量无效。

## 解决方案

### 推荐方案
源码补丁让临时目录优先读 TMPDIR（GNU 惯例），未设置时回落 `/tmp` 保持上游默认：
```c
const char *env = getenv("TMPDIR");
tmpdir = (env && *env) ? env : "/tmp";
```
完整示例见 `archives/p/podiff/1.4/patches/0002-main.c.patch`（含上下游回归验证：设置 TMPDIR 后比对模式正常，退出码语义 0/1/2/3 全部实测通过）。

### 禁止做法
- ❌ 只 `export TMPDIR=...` 就认为已修复（程序不读该变量，实证无效）
- ❌ 直接把默认常量改成某个绝对可写路径（丢失可移植性，仅作兜底）

## 验证
```bash
grep -n '"/tmp"' *.c                        # 定位硬编码
TMPDIR=$HOME/tmp ./tool a.po b.po; echo $?   # 适配前 134，适配后 0/1
```

## 关联条目
- 根因: E002（/tmp 只读平台事实）
- 相似: E482（zsh TMPPREFIX）、E325（test_package 可写 tmpdir 发现）、E265（测试期绕过 /tmp 只读）
