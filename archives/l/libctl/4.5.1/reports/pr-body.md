## PR 信息

- **三方库名称**：libctl
- **上游版本**：4.5.1
- **上游仓库地址**：https://github.com/NanoComp/libctl
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）；不申请路径 C
- **使用知识库**：沿用现有 HMDFS/config.status 经验；新增草稿 `knowledge/drafts/E2170-draft-2501.kv` 和同名 `.md`，最终编号请主编确认

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 1 | `utils/Makefile.am` 声明 `TESTS = test-prism`；源文件为 `utils/test-prism.c` |
| 集成测试 | 0 | 发行包未声明其他 Automake 集成测试 |
| 其他测试 | 0 | 发行包未声明其他 `TESTS`/`check_PROGRAMS` |
| **合计** | **1** | 完整清单见 `reports/upstream-test-inventory.txt`；实机 `make check -j1` 为 1/1 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 1 | 不变 | 未修改上游 `test-prism`，实机 1/1 通过 |
| 集成测试 | 0 | 不变 | 未添加上游集成测试 |
| 鸿蒙特有测试 | 1 | +1 | `test_package` 安装后消费者编译、链接和运行，输出 `LIBCTL_CONSUMER_PASS`；含路径与 `vector3_dot` 两项断言 |
| **合计** | **2** | **+1** | 上游 1/1；新增消费者 1/1；详见 `reports/test-report.md` |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有 `test-prism` 测试用例覆盖；另外增加安装后消费者验证
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：1/1（100%）
- 新增测试用例通过率：1/1（100%）
- 实机：HarmonyOS PC aarch64，`conan create` 返回 0；任务本地 W3 验证器返回 `W3_VALIDATOR_PASS`。
- 原始日志 SHA-256：`dc57864d47ea6db069b708bfadf8672e501d0ba8d7ce0659debf792490d27039`；收据链 SHA-256：`b23f92d905c0aecedfcb78b82882aa26bf9c504c9f4f04f0f99001afbcb8c6ce`。日志保存在任务私有证据目录，可供复核。
- 平台 CI、AI Review 和制品仓发布尚未完成；运行时仍有 GC `PT_GNU_RELRO` 警告，消费者正常退出，不宣称该警告已修复。

---

## 补充说明

- 关联 Issue：#3406（路径 B 知识库扩展申请）
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：OpenHarmonyPCDeveloper:feat/libctl-4.5.1
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：任务 #8151。发布版 Guile 2.2.7.1 缺少 `libguile.h`，使 configure 误落到旧 `guile/gh.h` 路径；匹配上游 Guile 2.2.7 的头文件随配方导出，并向消费者传递 Guile/GMP/GC 公开头路径。知识增量聚焦该诊断与 Conan 闭包，已有 HMDFS 临时目录知识不重复申报。官方源码包 SHA-256 为 `fcfeb2f13dda05b560f0ec6872757d9318fdfe8f4bc587eb2053a29ba328ae25`。
