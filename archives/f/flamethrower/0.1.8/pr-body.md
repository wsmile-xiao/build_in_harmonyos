## PR 信息

- **三方库名称**：Flamethrower
- **上游版本**：0.1.8
- **上游仓库地址**：https://deb.debian.org/debian/pool/main/f/flamethrower/flamethrower_0.1.8.orig.tar.gz
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新：AppConfig 可选变量契约）
- **使用知识库**：E2154 AppConfig optional-variable registration

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 上游归档无 `t/`、`test/` 或等价入口 |
| 集成测试 | 0 | 上游没有注册集成测试 |
| 其他测试 | 0 | MakeMaker 未提供独立可执行测试套件 |
| **合计** | **0** | `0/0`（不适用），已盘点完整上游归档 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试框架 |
| 集成测试 | 0 | 不变 | 未虚构上游分母 |
| 鸿蒙特有测试 | 1 | +1 | Conan `test_package` consumer，内部断言不拆分计数 |
| **合计** | **1** | **+1** | OpenHarmony 目标端 `1/1` 通过 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游归档没有可修改的正式测试用例。本 PR 仅新增独立 `test_package` consumer。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

- **补全的测试范围**：新增 1 个 consumer，覆盖命令版本、模块加载、AppConfig omitted/explicit/unknown 路径、udpcast 依赖可见性及负向退出码。
- **补全原因**：上游 0.1.8 没有正式测试套件，需要证明打包后的真实命令和 Perl 配置路径可用。
- **新增测试文件清单**：
  1. `archives/f/flamethrower/0.1.8/test_package/test_flamethrower.sh`，目标端 consumer 与精确诊断 oracle。
  2. `archives/f/flamethrower/0.1.8/test_package/conanfile.py`，Conan 显式测试入口。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（不适用）
- 新增测试用例通过率：1/1（100%）

- Fresh isolated OHOS/arm64 W0 以 `--build=never` 从 `ohpcd` 解析 `appconfig/1.71.1`、`perl/5.42.2` 和 `udpcast/20250223`。
- 真实目标端 W3 使用唯一 launch，consumer `1/1`，退出码为 0，测试 stderr 为 0，并在结束后回读远端任务根不存在。
- Official finish 生成并校验 `.ci-result.json`；aggregate finish 与 W3 子步骤按独立状态记录。
- 独立 W4 要求 P0/P1/P2/P3 全部为 0，W5 使用隔离 fixture 校验 E2154 草稿对。

---

## 补充说明

- **关联 Issue**：#2313
- **队伍名称**：天天开心
- **申请人显示标识**：2301_80739235
- **源分支**：2301_80739235:feat/flamethrower-0.1.8
- **目标分支**：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- **其他说明**：本包是 Debian/SystemImager 的纯 Perl Flamethrower 0.1.8，不是同名 DNS-OARC C++ 项目；四域知识查重未发现与 E2154 等价的既有规则。
