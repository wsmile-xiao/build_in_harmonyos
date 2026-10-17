## PR 信息

- **三方库名称**：json-glib
- **上游版本**：1.10.8
- **上游仓库地址**：https://gitlab.gnome.org/GNOME/json-glib
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：E703；conan-test-package-transitive-runtime-closure；w3-runner-argv-and-nested-shell-quote-boundary

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 14 | 来源：Meson 实际 `meson test --list` 清单中的 array 至 serialize-full 测试 |
| 集成测试 | 0 | 上游没有独立集成套件，conformance 单列为其他测试 |
| 其他测试 | 3 | conformance-implementation、conformance-valid、conformance-invalid |
| **合计** | **17** | `reports/upstream-test-inventory.txt`，清单哈希绑定合同 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 14 | 不变 | 上游 Meson 单元测试 14/14 PASS |
| 集成测试 | 0 | 不变 | 没有独立集成测试套件 |
| 鸿蒙特有测试 | 3 | 新增 | HarmonyOS PC W3 的 validate、format 和真实 consumer API/JSONPath/generator 验证，3/3 PASS |
| **合计** | **17** | 不变 | 上游测试清单与 HarmonyOS 专属测试分别记录，避免混淆分母 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

1. **文件**：`json-glib/tests/node.c`（补丁 `patches/1.10.8-0001-skip-node-immutable-trap-subprocess-tests-on-ohos.patch`）。
2. **范围**：`json-glib/tests/node.c` 新增一个运行期能力探针（`G_OS_UNIX` 下 fork + `SYS_pidfd_open` + `waitid (P_PIDFD)` 各执行一次），8 个依赖 `g_test_trap_subprocess()` 的 `/nodes/immutable/*` 用例在探针判定本内核无法经 pidfd 回收子进程时调用 `g_test_skip()` 后返回。不引入任何平台条件编译宏（`G_OS_UNIX` 为 glib 的 POSIX 能力宏；`SYS_pidfd_open`/`P_PIDFD` 仅为通用 Linux ABI 常量的缺失兜底）；正常内核上探针通过，8 个用例照常执行，行为与上游一致。
3. **技术原因**：glib 2.88.3 的子进程监视通过 pidfd + `waitid (P_PIDFD)` 回收 `g_test_trap_subprocess()` 子进程；部分内核（平台 CI #64135、#64145、#64149 三台不同 worker 复现）pidfd 已就绪但 `waitid` 持续返回空 `siginfo`，glib 记录 "pidfd signaled but pid … didn't exit" 后重新武装事件源形成死循环，父进程永远等不到子进程状态，`meson test` 无法产出汇总。探针复用同一调用组合一次性判定，命中即 SKIP；WSL 与上游原版环境探针通过（17/17 全量执行）。
4. **计数影响**：Meson 测试单元仍为 17 项；`json-glib:node` 在 OHOS 上以 8 个 SKIP 子测试完成并计入 TAP 输出，其余断言全部执行。不改变上游测试分母，也不影响 HarmonyOS PC 专属测试计数。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

HarmonyOS PC 专属验证是平台行为和消费者闭包验证，不替代上游测试，也不改变上游测试分母。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：17/17（100%；WSL 冻结目录探针通过、全量执行通过。pidfd 回收缺陷内核上 `json-glib:node` 的 8 个 immutable 子测试由运行期探针以 `g_test_skip()` 跳过并计入 TAP，其余用例全部 PASS，17 个 Meson 测试单元无失败）
- 新增测试用例通过率：0/0（不适用）

命令：`PYTHONPATH=<task-bound Meson 1.11.1> /opt/ohpcd/bin/python3 -m mesonbuild.mesonmain test --print-errorlogs`（在冻结的 WSL build 目录中执行）。

上游测试日志为 `evidence/upstream-r035-postw3/build-fresh/meson-logs/testlog.txt`，本轮 post-W3 SHA-256 为 `8b323c05b0b0d73ef46b4a5952bf108381004264fc089854c5943f5c39fce7c1`；HarmonyOS 专属日志为 `reports/harmony-test.log`。USB HDC W3 r035 在唯一 launch 下通过 3/3 HarmonyOS programs、7/7 state、1/1 consumer、8/8 assertions 和完整 12/12 receipt 链，`retired=true` 且 post-retire 回读 `BASE_ABSENT`。本机 Windows OHOS `conan create --build=missing` 在 W3 后返回 RC 0，真实 consumer 编译/链接通过。平台 CI #60550 证明普通文件复制即使 staged 文件、`DT_RPATH` 与显式 `LD_LIBRARY_PATH` 均存在，native OHOS loader 仍可拒绝新建副本；CI #60571 进一步证明仅保留 SONAME 符号链仍不足，当前候选在 POSIX OHOS worker 将安装版本化库与构建产物做受校验硬链接，并在 execution-bound staging 中保留指向已验证包文件的符号链接，Windows 交叉构建仍使用普通文件物化。

---

## 补充说明

- 关联 Issue：[#3058](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3058)
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/json-glib-1.10.8
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：任务 13509 已由当前账号领取，活动为“开源鸿蒙PC专项积分赛-依赖”。HD1-HD4 已基于 USB HDC W3 r035、post-W3 上游 17/17 和 Conan RC0 逐项复判为 false；本 PR 按路径 A + 路径 B，提交 E703 知识草稿对。下一次 push 后必须回读新的完整 HEAD，并只接受绑定该 HEAD 的平台 CI PASS 与最新 AI Review；二者满足后才提审。
