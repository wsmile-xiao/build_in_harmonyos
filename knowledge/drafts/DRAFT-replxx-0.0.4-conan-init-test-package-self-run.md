# DRAFT-replxx-0.0.4-conan-init-test-package-self-run

**主题**：ohc `conan-init` 生成的 `test_package/conanfile.py` 的 `test()` 仅调用 `cmake.test()`（CTest）而无 `self.run()`，官方 CI **L0d** 静态门禁判定为 `stub_test_method`（`test() method has no self.run() call — likely a stub`），即使本地 conan-verify / test_package / W3 prdiff 均已通过。

**来源事件**：`replxx/0.0.4` R02 L0d 返工。PR 7625 官方 CI 在 L0d 失败；本地 G1–G4、test_package、W3 prdiff 均通过。修复 `test()` 加入 `self.run(消费者二进制, env="conanrun")` 后，conan-verify G1–G4 PASS，`test_replxx` 9 断言 ALL PASS。

## 问题

| 项 | 内容 |
|---|---|
| 触发工具 | `conan-verify` / `finish` / `build_and_test.sh` / `submit` |
| 阶段 | testing / quality-gate |
| 错误签名 | `test() method has no self.run() call — likely a stub` / `stub_test_method` / `L0d.*self.run` |

## 根因

`ohc-run conan-init` 为编译型 CMake 库生成的 `test_package/conanfile.py` 模板，`test()` 只写：

```python
def test(self):
    cmake = CMake(self)
    cmake.test()
```

即用 CTest 间接驱动，**不包含 `self.run(...)` 调用**。官方 CI 的 L0d 静态门禁按 `test() method has no self.run() call — likely a stub` 判定该 `test()` 为空壳（stub_test_method）而拒绝 PR，即使本地门禁全绿。根因是生成模板与 CI 静态契约不一致：门禁要求 `test()` 必须包含真实、可失败传播的 `self.run()` 调用（执行打包后的消费者二进制/脚本），而非依赖 CTest 间接执行。

## 方案

1. 修改 `test_package/conanfile.py` 的 `test()`：构建出消费者二进制后，直接用
   `self.run(消费者二进制绝对路径, env="conanrun")` 执行——让 L0d 看到真实 `self.run()` 调用且失败可传播（非零退出 → Conan test 失败）。
2. 消费者二进制必须真实调用被测包 API（保留并验证实际断言），不得退化为仅打印字符串的空壳测试（同时满足 R34 反欺骗与 L1e 破坏性反向验证）。
3. 修复后必须重新 `conan-verify`（G2 conan create 会执行 test_package）确认 ALL PASS，再走 finish/W2/W3（prdiff 模式）与 W4 审计。

```python
# test_package/conanfile.py
import os

def test(self):
    test_bin = os.path.join(self.cpp.build.bindirs[0], "test_replxx")
    self.run(test_bin, env="conanrun")
```

消费者测试 `ohos_spec_test.cxx` 调用 `replxx::Replxx` 的 `history_add / history_size / get_state / set_*` 等真实 API，9 断言 ALL PASS。

## 验证

- 命令：`conan create archives/r/replxx/0.0.4 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`
- 修复前：本地 `conan-verify` G1–G4 通过、`test_package` 执行 `./test_replxx` ALL PASS、W3 prdiff 通过，但官方 CI L0d 仍判 stub（因 `test()` 无 `self.run()`）。
- 修复后：`conan-verify` G1–G4 PASS，`test_package` 经 `self.run("./test_replxx")` 执行，9/9 断言 ALL PASS（见 `reports/conan-create.log`）。

## 适用边界

任何经 `ohc-run conan-init` 生成 `test_package`、且打包产物含可运行消费者二进制（库/工具均可）的编译型 C/C++ 库，在官方 CI L0d 静态检测下可能命中 `stub_test_method`。

## 反例与排除

- **资源/数据型包**（E255 papirus-icon-theme、E281 festvox 等）：无编译、无消费者二进制，`self.run()` 无法直接执行二进制，属不同场景（其 L0d 规避依赖 package_type/脚本运行），不适用本方案。
- **多用例诊断**（E239）：针对 `self.run` 失败传播/聚合诊断的增强，不解决"`test()` 无 `self.run()` 被 L0d 判 stub"这一触发问题。

## 查重差异

- 四范围查重：正式条目 `E255`/`E281` 已定义"L0d 门禁要求 `test()` 必须含 `self.run()`"语义与**资源型包**规避方案；`E241` 为数据包模式；`E239` 为多用例诊断。草稿层无同主题命中。
- 本草稿补充**编译型库 + conan-init 模板 `cmake.test()` 无 `self.run()` → L0d stub** 的具体触发与修复，`similar_to: [E255, E281]`。
- 关联 `knowledge/drafts/DRAFT-replxx-0.0.4-conan-init-test-package-self-run.kv`（字段一一对应）。
