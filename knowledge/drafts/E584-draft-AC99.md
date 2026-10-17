# E584: ConanFile.run() 输出流继承导致编译器全量静默失败（make 只报 Error 1）

## 错误特征

- `make[2]: *** [CMakeFiles/xxx.dir/src/foo.cpp.obj] Error 1` —— **每一个**编译单元都失败
- `make[2]: *** [Makefile:NNN: all] Error 2`（或 `*** [CMakeFiles/Makefile2:...] Error 2`）
- 日志里 `grep -c "error:"` = **0**：没有任何 `error:` / `warning:` / 编译器诊断行
- 同一台机器、同一 profile、同一命令在**交互 shell** 下（或把整个 `conan create` 输出重定向到文件时）却编译成功
- `conan-verify` 的 G2 与 W3 的 `build_and_test.sh` **同时**判负

## 触发条件

- 构建系统: cmake（autotools 同理）
- 阶段: compilation（build）
- 环境: OHOS / HarmonyOS PC + Conan 2 + clang 15（`aarch64-linux-ohos`）
- 调用路径: `conan create` / `ci/conan/build_and_test.sh`（即由 `ConanFile.run()` 派生编译进程）

## 根因分析

`ConanFile.run()` 内部走 `conan_run()`，其默认 `stdout = stdout or sys.stderr`（Conan 2 `conans/client/runner.py`）会把**配方进程自身的 stdout/stderr 句柄继承**给子进程。在该平台上，clang 处于「stdout 被继承 / 非 tty」的形态时会静默失败：所有 TU 编译失败但**一个诊断字符都不输出**，make 失去全部线索，只能报 `Error 1`。

关键迷惑点：报错信息指向 `make`，但 `make` 本身正常（能跑、能正确报退出码），因此极易被误判为「runner PATH 缺 make / 工具链环境问题」而走向错误方向。与之对照的 E540（`make: inaccessible or not found`、exit 127）是完全不同的模式。

## 解决方案

### 推荐方案

在配方内把 configure / build / install 每步的输出绑定到各自独立的日志文件，使子进程不再继承配方进程的输出流：

```python
def _step_log(self, label):
    log_dir = os.path.join(self.build_folder, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{label}.log")
    handle = open(log_path, "w")
    self.output.info(f"CMake step '{label}' log: {log_path}")
    return {"stdout": handle, "stderr": handle}

def build(self):
    cmake = CMake(self)
    cmake.configure(**self._step_log("configure"))
    cmake.build(**self._step_log("build"))
```

autotools 项目等价写法：`self.run(f"{cmd} > {log} 2>&1")`。

配合「失败时回显日志尾部 + 抛出带日志路径的异常」，可在失败时立刻拿到真实诊断。

先例：libncurses 6.6_p20260516（同一平台、同一路径）；本条目来源 isoimagewriter 26.04.0。

### 禁止做法

- ❌ 把「make 报 Error 1 且零诊断」当成环境问题，靠换会话 / 重跑碰运气
- ❌ 只在外层把 `conan create` 输出重定向到文件就认为已修好——外层重定向恰好能过，掩盖了配方缺陷，CI/harness 仍会失败
- ❌ 用 `-D__OHOS__` 之类平台宏「绕过」——与本次错误无关的旁路，且会被审计判为伪造平台识别

## 验证
```bash
conan create <recipe> \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing 2>&1 | tee build.log
# 命中判据: build.log 含 "*** [xxx.obj] Error 1" 且 grep -c "error:" build.log = 0
# 修复后复跑 conan-verify（G2）与 finish（W3）应同时转绿
```

## 关联条目
- 易混淆: E540（`make: inaccessible or not found` / exit 127，根因是 runner PATH，不是本条）
- 相关: E537（KF6 DT_NEEDED 相对/陈旧绝对路径，常与本条在同一包内前后脚出现）
