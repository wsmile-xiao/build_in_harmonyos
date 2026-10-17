# E581 — USB 后端初始化失败未检查返回值 → 解引用未初始化指针 (Signal 11)

## 现象

`test_package` 运行阶段进程被信号杀死，日志中只有：

```
libosmosdr consumer tests (HarmonyOS PC aarch64)
Signal 11 (core dumped)
ERROR: libosmosdr/0.1.8.effcaa7: Error 139
```

关键特征：**崩溃前的横幅已经打印，但第一条用例的输出没有出现**。因此崩溃点在第一个库调用内部，
而不是测试驱动（`test()` / `self.run`）本身。同一个二进制在本机运行时正常通过全部用例。

## 根因

库的公共 API 直接调用 libusb 且不检查返回值：

```c
libusb_context *ctx;
libusb_device **list;          /* 未初始化 */

libusb_init(&ctx);             /* 失败时 ctx 保持未初始化 */
cnt = libusb_get_device_list(ctx, &list);   /* 失败时 list 保持未初始化 */
```

运行环境没有可用 USB 栈时（CI 容器/沙箱无法访问 USB 设备节点，或 `/dev/bus/usb` 权限被拒），
`libusb_init()` 返回负值并**不写出参**，随后的 `libusb_get_device_list()` / 解引用 / `libusb_free_device_list()`
作用在未初始化指针上 → `Signal 11 (core dumped)`。

本机有 USB 环境时这些调用成功，缺陷完全不暴露——**该模式是环境相关的（CI 与开发机表现相反），
不是确定性代码 bug**，因此"本机 W3 绿"不能证明 CI 会绿。

## 识别要点

1. 崩溃前有横幅、无首条用例输出 → 往"第一个库调用"查，不要先怀疑测试代码。
2. `test_package/conanfile.py` 里 `self.run(binary, env="conanrun")` 只是崩溃现场，不是原因；
   信号发生在被测库内部，包一层 try/except 或换 subprocess 都拦不住。
3. CI 绿过一次又变红、输入未变 → 优先怀疑环境相关路径（USB、display、GPU、网络设备）。

## 推荐修复（priority 1）

补齐 libusb 返回值检查，用补丁固化（不直接改源码树）：

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py refresh-patch --auto <name> <version>
```

要点：出参初始化为 NULL；`libusb_init()` 失败 → 直接返回"无设备"（count 0 / 名字空串 / open 错误码）；
`libusb_get_device_list()` 失败 → 先 `libusb_exit(ctx)` 再返回。不改语义、不加平台宏。

实测（libosmosdr/0.1.8.effcaa7，用返回失败的 libusb 替身复现）：

| 库 | `libusb_init` 失败 | `libusb_get_device_list` 失败 |
|---|---|---|
| 未打补丁 | rc=139 (SIGSEGV) | rc=139 (SIGSEGV) |
| 已打补丁 | rc=0，返回 0 个设备 | rc=0，返回 0 个设备 |

## 回退方案（priority 2）

不允许改三方库源码时，在 `test_package` 里探测运行环境是否有可用 USB 栈，无 USB 时跳过设备枚举用例并打印 SKIP 理由。
注意这**只让测试不再崩**，消费方在无 USB 环境仍会崩溃，所以优先级低于源码修复。

## 禁止策略

- 连续两个 libusb 调用都不检查返回值 → CI 无 USB 必崩，且崩溃点前无用例输出，排查成本极高。
- 只把 `self.run(...)` 换 subprocess / 包 try-except 就认为修好 → 信号发生在库内部，包装拦不住，会滑向 R43 调参螺旋。

## 相关条目

- E249 — Signal 11 / free 非 malloc 指针（同为未初始化指针家族）
- E040 — SIGSEGV 类运行期崩溃
