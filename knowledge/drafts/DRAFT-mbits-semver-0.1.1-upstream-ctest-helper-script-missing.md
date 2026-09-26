# DRAFT-mbits-semver-0.1.1-upstream-ctest-helper-script-missing：上游 add_test 引用的测试包装脚本在官方所有分支均缺失——最小补丁补齐，保持 ctest 注册项真实可执行

> Contributor: pc4-36 | Status: Draft | Updated: 2026-09-22
> Source: mbits-semver 0.1.1 适配（task mbits-semver-0.1.1-r01-pc4-36）
> 对应：`knowledge/drafts/DRAFT-mbits-semver-0.1.1-upstream-ctest-helper-script-missing.kv`

## 现象

ctest 注册项直接 Failed：

```text
/storage/.../python3.12: can't open file '.../tests/semver-test.py':
[Errno 2] No such file or directory
```

对上游仓库逐分支核验：`raw.githubusercontent.com/mbits-libs/semver/{v0.1.1,main,master}/tests/semver-test.py` 全部 **404**。

## 根因

上游 `CMakeLists.txt` 注册 `add_test(NAME semver.exit COMMAND python3 tests/semver-test.py ...)`，
但该包装脚本**从未随任何 tag/分支入库**——属上游发布缺陷，不是平台限制，
也不是本库适配问题。

## 修复（源码测试入口恢复规则）

在当前库配方允许范围内以最小补丁补齐同名包装脚本——只做"运行被测二进制并透传退出码"，
不伪造任何测试逻辑：

```python
import subprocess, sys
rc = subprocess.call([sys.argv[1]])
sys.exit(rc)
```

## 验证

补齐后 `ctest --output-on-failure`：`1/1 Test #1: semver.exit ..... Passed`

## 适用边界 / 反例

- ✅ 包装脚本在官方所有 tag/分支均确认缺失（需逐分支 404 核验）
- ❌ 脚本实际存在只是路径错误 → 修路径，不新增补丁
- ❌ 以"上游缺陷"为由把注册项写成通过或跳过 → 必须补齐后真实执行

## 查重关系

- similar_to: E353（同属 upstream-tests/ctest 域，但 E353=静态目标名不匹配，机制不同）
