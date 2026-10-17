# OHOS sysroot `stdout (stdout)` 递归宏 → `-Wdisabled-macro-expansion`

## 现象

在 OHOS 本机构建 NVTX 3.6.0-c-cpp 上游测试套件（tests/）时，`inj-c`/`inj-cpp`
两个测试注入库编译失败，clang 报 20 个同类错误：

```text
error: disabled expansion of recursive macro [-Werror,-Wdisabled-macro-expansion]
    LOG_ERROR("(init v2) NVTX_CB_MODULE_CORE is not supported.\n");
note: expanded from macro 'LOG_ERROR'
#define LOG_ERROR(...) fprintf(stdout, "[" ... "] ERROR: " __VA_ARGS__)
note: expanded from macro 'stdout'
#define stdout (stdout)        <-- OHOS sysroot /usr/include/stdio.h:67
```

## 根因

OHOS SDK sysroot 的 `stdio.h` 把 `stdout` 定义为**递归宏** `(stdout)`（musl 家族
差异实现）。当构建代码的宏（如 `LOG_ERROR(...) fprintf(stdout, ...)`）在参数中
直接引用 `stdout` 时，clang 判定为「被禁用的递归宏展开」并报
`-Wdisabled-macro-expansion`。若构建启用 `-Werror`（上游测试套件的
`CompilerWarnings.cmake` 普遍带 `-Werror`），该警告升级为错误，测试库编译即中断。

## 可复用修复模式

1. 仅对 OHOS 上的测试套件/scratch 验证构建追加 `-Wno-disabled-macro-expansion`
   （C 与 C++ 都加），**不**全局移除 `-Werror`，**不**禁用上游测试：
   ```bash
   cmake -S tests -B build -DENABLE_CUDA=OFF \
     -DCMAKE_C_FLAGS="-Wno-disabled-macro-expansion" \
     -DCMAKE_CXX_FLAGS="-Wno-disabled-macro-expansion"
   cmake --build build -j4 && ctest --output-on-failure
   ```
2. 若上游同时存在 musl redirect header（如 `sys/poll.h`/`sys/signal.h` 的
   `#warning` 重定向，见 E203 家族），可再追加 `-Wno-error` 处理该
   `#warning`；两个问题独立，需分别处理。

## 验证

- NVTX 3.6.0-c-cpp：追加标志后测试套件 100% 构建成功，ctest 106/106 通过
- 最小复现：`printf` 宏内含 `stdout` 的 C 文件在
  `/data/service/hnp/bin/clang -Werror -Wdisabled-macro-expansion` 下报同错误

## 适用边界

- 仅影响**构建期诊断**，不影响产物正确性；库配方（package）本身无此问题，
  该调整**不得写入 conanfile.py**。
- 该触发面与 E203（musl redirect header `#warning`）同属 OHOS sysroot
  头文件家族，但错误签名、诊断开关、修复手段均不同：E203 用 include 替换/
  `-Wno-error`，本条用 `-Wno-disabled-macro-expansion`。

## 反例

- ❌ 因该诊断关闭整个测试套件（`-DENABLE_*_TESTS=OFF`）——测试被虚假跳过
- ❌ 全局 `-Wno-error` 或 `-Wno-error=all`——掩盖同套件中真实的可移植性错误
- ✅ 仅降级 `-Wdisabled-macro-expansion` 单条诊断后完整运行测试