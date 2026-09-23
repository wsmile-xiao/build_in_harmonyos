# ols dev-2026-06 适配笔记（HarmonyOS PC / aarch64）

## 0. 结论

- 上游构建命令在本平台**直接可用**：`odin build src/ -show-timings -collection:src=src -out:ols -no-bounds-check -o:speed -define:VERSION=dev-2026-06`（ci.sh#L42 等价形）。
- **0 补丁**（未修改上游任何源码/脚本/测试用例）；唯一平台动作是**链接期注入 OHOS libc 线程取消符号空桩**（见 §2）。
- 上游测试 **860/860 全通过**（真跑，非豁免）；test_package **6/6** 通过（无头 LSP 会话）。
- 结论定性：本库在 2026-09-12 因 odin 编译器依赖链断裂被判定分支 B；odin 本体（PR !10021）适配双绿后，按 odin 计划「关键机制结论」定向续跑，本次一次通过。

## 1. 构建形态与命令

| 项 | 上游 | 本适配 |
|----|------|--------|
| 本地构建 | `build.sh`（`odin build src/ -show-timings -collection:src=src -out:ols -microarch:native -no-bounds-check -o:speed -define:VERSION=$VERSION`，build.sh#L70） | 采用 ci.sh 形态（去掉 `-microarch:native`，避免与宿主 CPU 特性耦合） |
| CI 构建 | `ci.sh`（`odin build src/ -show-timings -collection:src=src -out:ols -no-bounds-check -o:speed -define:VERSION=$OLS_VERSION`，ci.sh#L42） | **同形**，仅 `-out` 取绝对路径、`-define:VERSION` 固定为登记版本 |
| 测试 | `ci.sh CI`：`cd tests && odin test ../tests -collection:src=../src -o:speed -define:ODIN_TEST_THREADS=1` | 同形 + `-extra-linker-flags:<空桩.o>` |
| 版本注入 | `OLS_VERSION` 默认 `nightly-<UTC日期>-<短sha>` | 固定 `dev-2026-06`（登记版本，保证可复现与可断言） |

## 2. 平台关键点：OHOS libc 缺线程取消符号（root cause 级）

- **现象（报错原文）**：
  ```
  ld.lld: error: undefined symbol: pthread_setcancelstate
  >>> referenced by ols
  >>>               <build>/ols.o:(thread::[thread_unix.odin]::_create.__unix_thread_entry_proc-0)
  ld.lld: error: undefined symbol: pthread_setcanceltype
  ```
- **根因**：OHOS libc（SDK sysroot 与设备端）未导出 `pthread_cancel` / `pthread_setcancelstate` / `pthread_setcanceltype` / `pthread_testcancel`；ols 经 `core:thread` 创建请求线程（`src/main.odin#L56 thread.create_and_start_with_data`）与 checker worker，其上链 `core:thread/thread_unix.odin` 引用这些符号。
- **处置**：build() 内生成无害空桩 `ohos_libc_compat.c`（仅补齐链接语义，不改变被测代码行为），`clang --target=aarch64-linux-ohos -c` 编译后以 `-extra-linker-flags:<stub.o>` 注入。**不修改上游源码**。
- **复用出处**：odin dev-2026-08 适配（`learninglog/20260912odin-dev-2026-08/`）已实测同一根因，其空桩与结论可直接迁移到 Odin 生态其余包（odinfmt 未用到线程故无此问题）。
- **备选方案为何不用**：`-Wl,--unresolved-symbols=ignore-all` 可过链接期，但运行期加载报 `Error relocating ...: symbol not found`（设备端亦确无此符号），不可行。

## 3. 运行期环境

- `bin/ols`：`DT_NEEDED` 仅 `libc.so`、`RUNPATH=$ORIGIN` → 消费者无需任何环境变量。
- `bin/builtin/`：上游 README 要求 `builtin/` 位于 ols 二进制同级（`get_builtin_path` 用 `/proc/self/exe` 推断目录；回退 `OLS_BUILTIN_FOLDER`、`/usr/share/ols/builtin`）。缺该目录时 ols 仍可响应 initialize，但日志报 `Failed to find the builtin folder ...`。
- odin 根（`base/core/vendor` collections）由 ols 运行期自行解析：优先执行 `odin root`（`config.odin_command` 默认 `odin`，PATH 查找），失败则回退环境变量 `ODIN_ROOT`，再回退 `ols.json` 的 `odin_root_override`。**这是一项消费者侧配置**，不是本包的安装期依赖（故未进 `requirements()`）。

## 4. 无头环境的上游行为（如实记录，已上报主脑判定）

`stdin` 提前 EOF（客户端异常断开）时：reader 线程 `thread_request_main` 在读失败处直接 `return`，主循环 `consume_requests` 仍做 `sync.sema_wait` → **进程永久阻塞**，不会被回收。
→ 影响：无头测试/守护场景**不能靠关闭 stdin 收尾**，必须显式走 `shutdown` + `exit`（`notification_exit` 才置 `config.running = false`）。
→ 本适配未修改该行为（属上游健壮性问题，非平台适配缺陷），已在 learninglog 落盘并上报主脑。

## 5. 测试设计

### 5.1 上游测试（build() 内真跑，非致命）
- 入口：`cd tests && odin test ../tests -collection:src=../src -o:speed -define:ODIN_TEST_THREADS=1`（与 ci.sh CI 分支一致）。
- 结果：`Finished 860 tests in 3.6587s. All tests were successful.`（rc=0）。
- 计数核对：静态 grep `@(test)` 命中 863 处，其中 3 处不构成测试（`completions_test.odin` fixtures 字符串内 1 处 `foo_test`；`completions_test.odin`、`signatures_test.odin` 的 `/* */` 注释块内各 1 处），故真实声明 = 860；另以 `-define:ODIN_TEST_JSON_REPORT` 交叉核对 runner 结果条目 = 860，三者一致。

### 5.2 test_package（消费者视角，6 项，无头 LSP 会话）
1. `bin/ols version` → `ols version dev-2026-06`，rc=0（服务端启动前的纯 IO 退出路径）。
2. `bin/builtin/{builtin.odin,intrinsics.odin}` 与 `bin/ols` 同级。
3. `initialize` 握手：`id` 回显、`result.capabilities` 存在 + 8 项能力字段断言（hover/definition/typeDefinition/documentSymbol/documentFormatting/references/workspaceSymbol/rename 与 completion.triggerCharacters）。
4. `didOpen` + `documentSymbol`：返回函数符号 `add`(line 4)/`main`(line 8)，`kind=12`（SymbolKind.Function）。
5. `shutdown` → `{"id": 2, "result": null}`。
6. `exit` 通知后进程 rc=0 优雅退出（124 = 超时即失败）。

- 断言模式全部先对真实响应逐条校验（避免「假通过」）。
- 会话用 `timeout 120` 兜底，防止上游 stdin-EOF 阻塞行为把 CI 拖死。
