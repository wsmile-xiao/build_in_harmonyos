# E550 草稿：`can_run()` 隐式跳过导致 W3/CI L1e 反向测试误判空壳

## 错误特征
正向 `conan create` 日志里消费者已真实执行（swuniq：`OHOS aarch64 ELF and sliding-window pipe consumer: PASS (2/2)`），但 `ci/conan/build_and_test.sh` 的 L1e 随后报：

```
[sabotage] bin/ moved away
[fail] L1e: test passed WITHOUT package artifacts — fake test detected (R34)
L1_RESULT=fail: negative test: test does not depend on package
```

## 根因
- 正向：`conan create -pr:h=ohos-aarch64 -pr:b=ohos-aarch64`，build/host 同为 OHOS armv8，`can_run(self)` 为真，测试执行。
- 反向（L1e）：`conan test <test_package> <ref> -pr <ohos-aarch64>` 只给 host profile，build profile 取 x86 默认 → `can_run(self)` 为假。
- `test()` 写成 `if can_run(self): self.run(...)`，于是反向测试**什么都没跑就返回 0**，被判为"不依赖被测包"。
- 在 x86 runner 上，OHOS 静态 aarch64 可由 `qemu-aarch64` 实跑，所以这个跳过同时掩盖了本可完成的真实验证。

## 解决方案
不用 `can_run()` 作为静默跳过条件；按物理机器选择执行方式：
- `platform.machine()` 为 `aarch64/arm64` → 直接执行；
- 否则显式用 `qemu-aarch64` 运行测试程序，并把 qemu 路径传给测试程序，用它再 exec 被测 CLI；
- 两者都不可用 → `ConanInvalidConfiguration` 明确失败，绝不静默通过。

swuniq 0.5 的 `test_package/conanfile.py` / `test.c` 即按此修改。

## 验证
`python3 scripts/ohc-run.py finish swuniq 0.5 built`：W3 日志应出现 `[ok] L1e: Negative test confirmed — test genuinely depends on swuniq`，且正向仍 `PASS (2/2)`。

## 禁止
- ❌ `if can_run(self): self.run(...)` 后无 else —— 在 L1e 单 profile 下必然假通过；
- ❌ 为过 L1e 在测试里硬编码 `exit 1` 或检查文件是否存在来冒充依赖 —— 必须真实执行包内二进制。

## 关联
- `E428`：test_package 子脚本经 PATH 找不到包内 CLI（同属 application 包消费者测试，但根因是 PATH 继承，不是 profile 差异）。
- `E544` 系列草稿：x86 runner 上动态 OHOS 产物缺 musl loader 无法运行；本例产物为静态，因此 QEMU 可行。
