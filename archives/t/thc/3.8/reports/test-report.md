# Test Report — thc 3.8 (OHOS aarch64)

## R51 上游测试清点

- 上游仓库 `vanhauser-thc/thc-ipv6` v3.8 **无正式测试框架**：
  - 无 `test/` 或 `tests/` 目录
  - `Makefile` 无 `test` target
  - CI（GitHub Actions）无测试阶段
- 结论：上游测试用例数 = **0**（单元 / 集成 / 其他均 0）

## 适配后测试（鸿蒙消费者端到端，test_package）

全部在 OHOS aarch64 真实运行 conan 包内二进制，共 **3** 断言（R51 鸿蒙特有消费者用例）：

| # | 用例 | 输入 | 期望输出 | 结果 |
|---|------|------|----------|------|
| A1 | address6 正向解析 | `fe80::0211:22ff:fe33:4455` | `00:11:22:33:44:55` | PASS |
| A2 | address6 正向解析 | `fe80::aabb:ccff:fedd:eeff` | `a8:bb:cc:dd:ee:ff` | PASS |
| A3 | address6 错误路径（鸿蒙特有）| `2001:db8::1` | stderr 含 `Error:`，进程退出非 0 | PASS |

- 运行命令：`conan test archives/t/thc/3.8/test_package`
- 结果：`PASS=3 FAIL=0`（100%）

## 真实验证结果

- 编译状态：通过（conan create revision `5bf76dbdf5a7ae75d49a947398978be8`，OHOS aarch64 / clang）
- 上游测试用例通过率：0/0（上游无测试）
- 新增测试用例通过率：3/3（100%）
- W3 本地 CI 模拟：`.ci-result.json` `exit_code=0`，`JC_ERRORS=0`
- conan-verify：Verdict PASS（G0–G4 + L2/L4/L5）

## 已知限制

- `fragrouter6` / `connsplit6` 因 `libnfnetlink/libnfnetlink.h` 未注入未编译（Makefile 优雅降级），不影响主包（其余 66 个二进制正常产出）。
