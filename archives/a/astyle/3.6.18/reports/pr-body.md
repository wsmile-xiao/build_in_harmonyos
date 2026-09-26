## PR 信息

- **三方库名称**：astyle
- **上游版本**：3.6.18
- **上游仓库地址**：https://gitlab.com/saalen/astyle
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新）
- **使用知识库**：E7008-draft-A7F3；cmake-library-public-header-and-define-audit

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 上游发布入口未提供独立单元测试清单 |
| 集成测试 | 0 | 上游回归脚本按风格目录执行，不是独立集成框架 |
| 其他测试 | 16 | `AStyleTest/regression-sh` 下 16 个 `style_*` 目录 |
| **合计** | **16** | 清单见 `reports/upstream-test-inventory.txt`，实际命令见 `reports/upstream-test.log` |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 0 | 不变 | 配方不改变上游测试分类 |
| 集成测试 | 0 | 不变 | 配方不改变上游测试分类 |
| 鸿蒙特有测试 | 2 | +2 | `test_package/test.cpp` 调用 `AStyleMain` 和 `AStyleGetVersion` 两项真实 API 断言；OHOS arm64 真机消费者 RC0 |
| **合计** | **2** | +2 | 新增消费者清单绑定 `test_package/MANIFEST.yml` |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游 `AStyleTest/regression-sh` 及其输入文件保持原样；配方只在 native 构建中运行该脚本，交叉构建时按 `can_run`/`cross_building` 规则不在主机执行目标程序。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

独立的 Conan 消费者是包接口验证，不替代或改写上游 16 个回归目录。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：16/16（100%）
- 新增测试用例通过率：2/2（100%）

验证细节：

- native 静态库、共享库和实际安装前缀消费者均通过；消费者调用 `AStyleMain`、`AStyleGetVersion`。
- OHOS arm64 `conan create` 返回 RC0，目标消费者编译成功。
- W3 `astyle-3.6.18-w3-r004` 使用官方原生签名器 `selfSign=1`，目标消费者真机 RC0；PID `54649` / start token `20875700`、签名状态和零字节输出独立回读，远端根已释放并通过 postrelease。
- `r003` 因 `$22` start-token 解析错误冻结失败，已独立清理，未与 `r004` 拼接证据。

---

## 补充说明

- 关联 Issue：#2620
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/astyle-3.6.18
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：该适配对应依赖任务 5829 和 `POTENTIAL_SIMPLE` 中的 `libastyle-dev`。上游 CMake 安装规则未安装公开头文件，配方显式安装 `astyle.h`、`astyle_main.h` 并导出 `ASTYLE_LIB`。E7008 草稿补充库/CLI 双入口与真实消费者断言的可复用边界；不执行本地 P0/P1 扫描，平台 AI Review 以 PR 创建后的最新结果为准。
