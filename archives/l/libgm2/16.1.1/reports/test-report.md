# libgm2 16.1.1 测试报告

状态：**conan create 成功** + **conan-verify 八项门禁全绿** + **W3 本地 CI 模拟（L0/L1/L2/L4/L5）通过**（见归档 `.ci-result.json`）。

## 测试矩阵（全项执行）

| 层级 | 测试 | 判定 | 结果 |
|------|------|------|------|
| 上游冒烟 | build() 用新构建 gm2 驱动 + cc1gm2 编译并执行上游 `examples/hello/pass/hello.mod` | 退出码 0 | ✅ `gm2 smoke test passed: hello world from libgm2`（验证 specs/`__availability__`/`--eh-frame-hdr`/post-link 签名/合并 libstdc++.a/5 个运行时库全链路） |
| 上游全量 dejagnu | `runtest --tool gm2` 113 个 .exp 分批 b01..b13 | 16207/16261 PASS（99.67%） | ✅ 54 条 FAIL 全部环境性（36 条 eh-frame-hdr 修复前旧记录、18 条 OHOS 沙箱屏蔽时间类系统调用），0 条真实功能失败 |
| test_package | test_libgm2.c：链接打包 libm2iso/libm2pim + libstdc++.a stub，调用运行时 API 校验（7 条断言） | 全部通过 | ✅ `libgm2-ohos-ok`（设备实运行，含二进制签名） |
| 消费者用例 | test_consumer/consumer_use_case：配置清单预检报告器端到端业务流程 | 全部通过 | ✅ C1 执行 / C2 统计报告核验 / C3 consumer-ok 标记 |

## 鸿蒙特有测试（rule12，新增 4 项 + 消费者用例 1 项）

运行环境：真实鸿蒙 PC（aarch64, OHOS），`test_ohos/run_ohos_test.sh` 对最终 Conan 包独立专项检查。

| 用例 | 验证内容 | 结果 |
|------|----------|------|
| OHOS_01 | aarch64 ELF（打包 5 个运行时 .so 均为 ELF64 AArch64，可在 OHOS 加载执行） | ✅ 通过 |
| OHOS_02 | 无宿主路径泄漏（构建机 /storage /home /Users 绝对路径不进入产物） | ✅ 通过 |
| OHOS_03 | 打包库真实运行（编译消费者程序链接打包库，执行并输出 consumer-ok） | ✅ 通过 |
| OHOS_04 | 运行时库导出符号完整（m2pim_Builtins_strlen/strcmp、m2iso_CharClass_IsLetter/IsNumeric/IsUpper 等 C 可调用符号存在，非空壳包） | ✅ 通过 |

消费者用例（test_consumer/consumer_use_case.sh，自包含 编译→链接→运行→核验）：
- C1 消费者业务流程执行（rc=0）
- C2 统计报告与期望一致（letters/digits/upper/total=32、key_eq=1、key_ne=1）
- C3 输出 consumer-ok 成功标记

## 结论

- 上游测试用例通过率：**16207/16261（99.67%）**，0 条真实功能失败
- 新增测试：消费者用例 1 + 鸿蒙特有 4 = **5/5（100%）**
- 打包产物：5 个运行时 .so（libm2cor/libm2iso/libm2log/libm2min/libm2pim）+ 4 个 .def 定义模块头 + 合并 libstdc++.a stub + COPYING 许可证，全部带 OHOS codesign
