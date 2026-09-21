# E429 — Makefile 默认 CXXFLAGS 含 x86 专属 SIMD 标志（-msse4）在 aarch64 不适用

## 错误特征
```
clang-15: warning: argument unused during compilation: '-msse4' [-Wunused-command-line-argument]
```
或部分工具链报 hard error：
```
error: unknown argument: '-msse4'
error: unrecognized command-line option '-msse4'
```

## 触发条件
- 构建系统: plain Makefile / autotools（C++ 项目）
- 阶段: make / compilation
- 实例: last-align (LAST) 1652 的 `src/makefile` 默认
  `CXXFLAGS = -msse4 -O3 -Wall -g -std=c++11 -pthread`

## 根因分析
上游为 x86 SSE4 指令集优化，把 `-msse4` 硬编码进默认 CXXFLAGS。在
HarmonyOS aarch64 (armv8) 平台上，clang 无法使用该 x86 专属标志：
- clang 15 报 "argument unused" warning（不阻断，但污染编译日志）；
- 其他工具链/老版本可能直接报错阻断编译。

源码 SIMD 代码若用 `#if defined __SSE4_1__ / __ARM_NEON` 双分支守卫
（LAST 的 `src/mcf_simd.hh` 即如此），aarch64 会自动选 NEON 路径，
无需改源码。

## 解决方案

### 推荐方案：conanfile build() 覆盖 CXXFLAGS
```python
# conanfile.py build() 内构造 make 参数
assignments = {
    "CC": cc,
    "CXX": cxx,
    "CFLAGS": "-Wall -O2",
    "CXXFLAGS": "-O3 -std=c++11 -pthread",   # 移除 -msse4
    "CPPFLAGS": " ".join(include_flags),      # 依赖 include 目录
    "LDFLAGS": " ".join(libdir_flags),        # 依赖 lib 目录
}
self.run(f"make -j1 {make_args}", cwd=self.build_folder, env="conanbuild")
```
命令行为 make 命令行变量，会向子 make 传递，覆盖 Makefile 内默认值。

### 回退方案：改源码 Makefile（R6 允许改源码）
把默认 CXXFLAGS 中的 `-msse4` 移除，或用平台条件选择。

### 禁止做法
- ❌ 在 aarch64 上无条件传递 `-msse4`（日志污染 / 部分工具链拒绝）
- ❌ 用 sed 改 configure 生成文件（R6）

## 验证
```bash
# 确认编译命令不再含 -msse4
make -n CXXFLAGS="-O3 -std=c++11 -pthread" 2>&1 | grep -c msse4   # 期望 0
./bin/lastdb --version   # 二进制可运行
```

## 关联条目
- 相关: E006（asm 安全）、E016（汇编不识别）、E100（SIMD 未定义符号）
