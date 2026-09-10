# DRAFT-E5xx: OHOS musl 默认不发射 unwind tables 导致栈追踪库输出空栈

## 错误特征
```
backtrace frames: 0
frames: 0
<empty trace>
trace.frames.size() == 0
```

## 根因分析
OHOS musl 环境的 clang 默认优化级别（-O1/-O2）**不发射 .eh_frame / unwind
tables**——这与 glibc 生态常见发行版不同（GCC/发行版 clang 通常默认带
`-fasynchronous-unwind-tables`）。所有依赖 unwind 信息的栈追踪方案在运行期
拿不到任何帧：

- `execinfo.h` 的 `backtrace()` 返回 0
- `_Unwind_Backtrace` 的回调一次都不触发
- 栈追踪库输出 `<empty trace>`

**最阴险的点：编译链接全部成功，零告警**——只有运行期才能发现空栈。

实测对照（HarmonyOS PC arm64，clang 15.0.4）：

| 编译选项 | backtrace() 返回 | _Unwind_Backtrace | cpptrace generate_trace() |
|---|---|---|---|
| 默认 -O1/-O2 | **0 帧** | 回调不触发 | `<empty trace>` |
| 加 `-funwind-tables` | 3 帧 | 回调正常 | 完整栈帧（文件名+行号） |

## 推荐方案
对需要运行时栈展开的目标（库本体、测试程序、消费方示例）显式加
`-funwind-tables`：

```cmake
# CMakeLists.txt（对需要回溯的 target）
if(NOT MSVC)
    target_compile_options(<target> PRIVATE -funwind-tables)
endif()
```

```python
# Conan 配方 generate() 全局注入
tc.variables["CMAKE_CXX_FLAGS"] = "... -funwind-tables"
```

注意：栈库头文件里的 `CPPTRACE_FORCE_NO_INLINE`/`__attribute__((noinline))`
只能保证函数不被内联，**不能弥补缺失的 unwind tables**。

## 受影响范围
HarmonyOS PC（musl libc）上任何依赖栈展开的代码：
- 栈追踪库：cpptrace / libbacktrace / backward-cpp / boost::stacktrace
- 崩溃收集器 / 性能采样器 / 异常诊断工具
- 凡 -O 优级编译且需要运行时回溯的目标

## 验证方法
最小探针（验证命令）：
```c
#include <execinfo.h>
#include <stdio.h>
int inner() { void* buf[16]; int n = backtrace(buf, 16); printf("frames: %d\n", n); return n; }
int outer() { return inner(); }
int main() { return outer() > 0 ? 0 : 1; }
```
不带 `-funwind-tables` 编译运行输出 `frames: 0`（exit 1）；加 flag 后
`frames: 3`（exit 0）。

## 实测证据（cpptrace 1.0.4 适配）
- 不带 flag：`smoke.cpp` 探针 `backtrace frames: 0`
- 加 flag：cpptrace unittest **155/155 PASSED**，test_cpptrace_ohos 真实
  展开 4 帧且 libdwarf 符号化输出 `文件名:行号`
- 知识图谱查重：零命中（E528/E529 是 libunwind 构建环境问题，E216 是
  CMakeDeps components 问题，根因均不同）——全新平台级知识条目
