- **三方库名称**：Chinese Calendar（Conan 包名：`chinese`）
- **上游版本**：1.0.3.r58（固定源码提交 `593d89df7956253618da38e91891fb76516daf46`）
- **上游仓库地址**：https://launchpad.net/chinese-calendar；源码地址：https://codeload.github.com/WhiredPlanck/chinese-calendar/tar.gz/593d89df7956253618da38e91891fb76516daf46
- **适配路径**：路径 B（贡献创新）
- **使用知识库**：openharmony-compile-agent；Qt6 模块分包、qmake 模块路径、Qt5→Qt6 API 兼容经验

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：上游未提供正式单元测试框架或测试目录 |
| 集成测试 | 0 | 来源：上游 `chinese-calendar.pro` 未提供集成测试目标 |
| 其他测试 | 0 | 未发现可执行的上游测试脚本 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 未新增单元测试 |
| 集成测试 | 0 | 不变 | 未新增集成测试 |
| 鸿蒙特有测试 | 1 | 新增 | 针对鸿蒙 Conan 消费者侧安装产物的测试 |
| **合计** | **1** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游未提供正式测试用例，因此不存在上游测试用例修改。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试

- **补全的测试范围**：新增 1 个鸿蒙 Conan consumer test；同一次测试执行验证 3 项安装产物断言，不拆分虚增测试用例。
- **补全原因**：上游仅包含桌面应用源码，没有正式测试框架或测试目标，需要验证 Conan 包在鸿蒙消费者侧的可用安装布局。
- **新增测试文件清单**：
  1. `archives/c/chinese/1.0.3.r58/test_package/conanfile.py` — 构建并执行 `chinese_consumer_test`。
  2. `archives/c/chinese/1.0.3.r58/test_package/chinese_consumer_test.cpp` — 检查 `bin/chinese-calendar` 可执行、`usr/share/chinese-calendar/db/KylinLunar.db` 存在、`usr/share/applications/chinese-calendar.desktop` 存在。
  3. `archives/c/chinese/1.0.3.r58/test_package/CMakeLists.txt` — Conan 消费者测试的 CMake 构建入口。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（不适用；上游无测试目标）
- 新增测试用例通过率：1/1（100%）

## 补充说明

- 使用 clang（`aarch64-unknown-linux-ohos`）和 qmake + make 完成 OHOS 构建。
- 新增 7 个 Qt6 兼容补丁，处理 `QRegExp`、`QTextCodec`、`QDesktopWidget`、QtSql 头文件路径以及 Qt6 模块分包链接路径问题。
- 本地 `conan create archives/c/chinese/1.0.3.r58 --profile=ci/conan/profiles/ohos-aarch64 --build=missing` 通过，鸿蒙消费者测试输出 `chinese HarmonyOS consumer test passed`。
- 远程 CI #42918 已通过，Conan `test_package`、L0 门禁和 L1 门禁均通过；最新提交后的 CI 正在重新构建。
- GUI 程序未在无显示服务器的 CI 环境中启动事件循环；消费者测试验证可执行入口和必需运行时资源完整性。
- 归档状态为 `built`，尚未上传制品仓。
