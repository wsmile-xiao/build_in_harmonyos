# E548 — test_package 断言绑定环境相关返回值（本机绿 / CI 沙箱红）

## 错误特征

CI 评论报 `类别: 测试失败`，日志尾部形如：

```
dlopen(libhidapi-libusb.so, RTLD_NOW) -> ok
hidapi 入口符号可解析: 14/14
dladdr(hid_enumerate) -> .../p/hidap04f75c3eccb36/p/lib/libhidapi-libusb.so
hid_init() -> -1
ERRtest failed: test_ohos_loader_dependency_contract @ test_package/test.c:480
```

关键是**同一份代码本地 `conan create`/W3 全绿，CI 必红**（或反之）：断言把一个随宿主环境变化的返回值当成了常量。

## 触发条件

- 构建系统: 任意（conan / cmake / autotools）
- 阶段: test_package（`conan create` 的测试阶段）与 CI 校验阶段
- 相关环境差异: `/dev/bus/usb` 访问权限、udev/systemd 服务、`/usr/lib` 路径存在性、
  `/tmp` 可写性、容器内网络可达性、沙箱 cgroup/namespace 限制等

## 根因分析

`test_package` 的断言描述了"适配正确性"，但实际绑定的是"宿主环境能力"：

- openhmd 的鸿蒙特有消费者用例（`test_package/test.c`）断言 `hid_init() == 0`。
  `hid_init()` 由 hidapi 的 libusb 后端实现，内部调用 `libusb_init()`：
  - 开发机可访问 `/dev/bus/usb` → 返回 `0`，本地 W3 与 `conan-verify` 全绿；
  - CI 沙箱无 USB 设备节点访问 → 返回 `-1`，断言失败，CI 红（build-51367）。
- 该用例的真实目的是验证**依赖闭包在运行期可用**（装载器按制品仓命名解析 `.so`、
  `hid_*` 入口全部可解析、`dladdr` 回报真实路径），与宿主是否具备 USB 访问无关。
- 同类反模式：断言 `/tmp` 可写、断言存在 `/usr/lib/libdl.so`、断言网络可下载、
  断言二进制 `chmod +x` 生效（HMDFS 行为差异）等——都是把环境当常量。

## 解决方案

### 推荐方案

把断言从"单值相等"改成"值域 + 语义标注"，并只调用可安全调用的 API：

```c
/* 0 = libusb 后端可用；-1 = 当前环境无 /dev/bus/usb 访问（沙箱常见）。
 * 两者都接受，不把环境差异误判为适配缺陷。 */
rc = hid_init_fn();
printf("    hid_init() -> %d（0=libusb 后端可用；-1=无 /dev/bus/usb 访问，沙箱环境正常）\n", rc);
TAssert(rc == 0 || rc == -1);

/* 仅在初始化成功时调用配套 API，避免未初始化状态下的未定义行为；
 * 依赖闭包已由 dlsym(hid_exit) 非空断言覆盖。 */
if (rc == 0)
    hid_exit_fn();
```

要点：

1. 断言表达"契约"（符号存在、可解析、可调用、返回值受控），不表达"宿主能力"；
2. 平台/环境不满足时显式 SKIP 并打印原因（`printf` + `return`），不要 `exit(1)`；
3. 本地 W3 绿 ≠ CI 绿：环境相关断言必须在 CI 侧复核后再判定。

### 禁止做法

- ❌ 为了"让 CI 过"直接删除该断言或把用例改成 print-only（`R34`：test 必须实质调用被测包）；
- ❌ 把返回值硬改成 `-1`（本地又会红，只是把问题搬到另一侧）；
- ❌ 在断言失败分支里 `exit(0)` 伪造通过（欺骗检测，`review-memory.md` 类别一）。

## 验证

```bash
# 本地：见证 value domain 断言通过
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify openhmd 0.3.0.1   # G2 PASS
# CI 侧：评论 /rebuild 后确认 CI 校验通过（沙箱内 -1 也被接受）
python3 $SKILL_ROOT/scripts/gitcode_pr.py trigger-ci --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 9686
```

## 关联条目

- 相关: E524（依赖注入私有 prefix，同为"环境耦合导致 CI 红"的适配缺陷）
- 规则: R34（测试必须实质依赖被测包）、W3（本地验证不等于 CI 验证）、R44（CI 红先自诊断）
