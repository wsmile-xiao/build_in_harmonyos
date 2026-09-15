# OHOS 上 make jobserver mkfifo "Operation not permitted" 为非致命告警

> 草稿（DRAFT）。与同目录 `opencsg-1.8.2-make-jobserver-mkfifo-not-permitted.kv` 成对。

## 现象

真机 shadow CI 的构建日志出现（库构建与 test_package 构建各一次）：

```text
make: jobserver mkfifo: <TMPDIR>/GMfifo32539: Operation not permitted
[ 11%] Building CXX object src/CMakeFiles/opencsg.dir/area.cpp.obj
...
[100%] Linking CXX shared library libopencsg.so
```

## 根因

GNU make 在并行构建（`-j/N`，以及 CMake 生成的 `cmake --build <dir> -- -jN`）时会尝试在
`TMPDIR` 下 `mkfifo` 一个 jobserver FIFO。OHOS 的 `TMPDIR`（HMDFS 上的 CI run 临时目录）
限制该操作，make 打印告警并**回退到非 jobserver 调度**。该告警**不终止构建**：目标仍被
正常编译与链接。

## 判据

- **非致命**：日志随后出现 `Built target` / `Linking CXX` / `[100%]`，且产物存在。
- 不要仅为消除该行去改 `ci/` 脚本或并发度；也不要在单库配方里做平台级规避。
- 若确需恢复真正的并行 jobserver，属基础设施/环境修复（让 make 使用可 `mkfifo` 的目录），
  不写进单库配方。

## 快速的判据命令

```bash
grep -c "jobserver mkfifo" <build_log>                     # 可能出现若干次
grep -E "Built target|Linking CXX|100%\]" <build_log>      # 同时应有完成标记
ls -la <build_dir>/<lib>.so                                # 产物存在
```

## 适用范围

所有在 OHOS 上用 GNU make 并行构建（含 CMake 默认生成器）的库；在 `TMPDIR` 受限的 CI run
临时目录下更易出现。**与具体库无关**。

## 证据（opencsg 1.8.2）

设备 shadow CI 中两条 `jobserver mkfifo ... Operation not permitted` 告警之后，两次构建
均正常完成（`[100%] Built target opencsg` / `test_opencsg`），包与测试通过、exit code 0。
