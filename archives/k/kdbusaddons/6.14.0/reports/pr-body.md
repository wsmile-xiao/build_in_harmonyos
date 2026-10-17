## PR 信息

- **三方库名称**：kdbusaddons
- **上游版本**：6.14.0
- **上游仓库地址**：https://download.kde.org/stable/frameworks/6.14/kdbusaddons-6.14.0.tar.xz
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 2 | 来源：上游 autotests/（`ecm_add_tests` 注册 deadservicetest + kdbusservicetest，UNIX 下含 kdbussimpleservice 辅助程序） |
| 集成测试 | 0 | 上游未单独注册集成测试 |
| 其他测试 | 0 | 无 |
| **合计** | **2** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 2 | 不变 | 上游 autotests 沙箱实测 2/2 通过（kdbusservicetest exit 0、deadservicetest 3 passed/0 failed），详见 reports/dbus-autotests-run.md |
| 集成测试 | 0 | 不变 | - |
| 消费测试（test_package） | 1 | +1（新增） | test.cpp 3 项断言（KDEDModule API 往返 + moduleForMessage 解析），1/1 通过 |
| **合计** | **3** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 逐条说明：
> 1. **修改的测试文件**：无（上游 autotests 源码未改动）
>    - **修改原因**：上游 autotests（kdbusservicetest/deadservicetest）需要运行中的 D-Bus session bus；CI 构建沙箱无 dbus-daemon 二进制且 unix socket 创建被禁（Operation not permitted），故配方 conanfile.py 保持 `BUILD_TESTING=OFF` 不编译上游测试
>    - **修改内容**：仅在 conanfile.py 的 generate() 设置 `BUILD_TESTING=OFF`，未修改上游任何测试源码
>    - **沙箱实测补充**：在本机 OHOS 沙箱内自建 dbus-daemon 1.14.10（源码构建）+ abstract session bus，实际编译并运行上游 2 个 autotests 全部通过（2/2 = 100%），详见 reports/dbus-autotests-run.md

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 若选择「是」，须说明：
> - **补全的测试范围**：为验证 KF6DBusAddons 核心 API 在 OHOS 上的可用性（不依赖 D-Bus session bus），新增 test_package 消费测试 1 项
> - **补全原因**：上游 autotests 需运行中的 D-Bus session bus，CI 沙箱不可用；补一个不依赖 bus 的消费测试保证 CI 内可执行
> - **新增测试文件清单**：
>   1. `test_package/test.cpp` — 3 项断言（KDEDModule::setModuleName/moduleName 往返、moduleForMessage 解析 /modules/foo、signal 消息返回空模块名）
>   2. `test_package/CMakeLists.txt` — find_package(KF6DBusAddons) + add_test
>   3. `test_package/conanfile.py` — test() 中 cmake.test() + 直接运行 test_kdbusaddons 二进制（R34 真实执行包产物）

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：2/2（100%）（沙箱内自建 D-Bus session bus 实测，详见 reports/dbus-autotests-run.md）
- 新增测试用例通过率：1/1（100%）（test_package test_kdbusaddons）

### 编译验证
- 编译器: clang (aarch64-unknown-linux-ohos)
- 编译状态: 成功
- 构建系统: cmake
- 配置选项: `-DKF_IGNORE_PLATFORM_CHECK=TRUE -DWITH_X11=OFF -DBUILD_TESTING=OFF`

### 产物验证
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 编译无错误 | PASS | 构建系统: cmake, 状态: built |
| 产物存在性 | PASS | conan create 验证 |
| ELF 格式 | PASS | aarch64-unknown-linux-ohos |
| 上游测试运行 | PASS | 沙箱 session bus 实测 2/2（kdbusservicetest、deadservicetest） |
| 运行测试 | PASS | test_package 通过: 1, 失败: 0, 跳过: 0 |
| 动态依赖 | PASS | 依赖: qtbase-sql-dbus/6.11.1 |

### 补丁说明
- `0001-CMakeLists.txt.patch`: 注释顶层 `ecm_install_po_files_as_qm(poqm)`，规避其强制 `find_package(Qt6 COMPONENTS LinguistTools)`（Qt6LinguistTools 属 qttools，制品仓未发布）导致的 configure 失败

### 依赖
- qtbase-sql-dbus/6.11.1（Qt6Core/Qt6DBus/Qt6Test，FEATURE_dbus=ON）
- ecm/6.20.0（build requirement）

### 测试结论
- 总体评价: 通过
- 已知限制: CI 沙箱无 dbus-daemon，配方保持 BUILD_TESTING=OFF；上游 autotests 已在本机沙箱实测 2/2 通过

### 遇到的问题与解决方案
- **1**: 根因=CMake configure 失败：Qt6_FOUND=FALSE，缺 LinguistTools, 解决方案=顶层 CMakeLists `ecm_install_po_files_as_qm(poqm)` 经 ECMPoQmTools 强制 `find_package(Qt6 COMPONENTS LinguistTools)`，Qt6LinguistTools 属于 qttools，制品仓未发布
- **2**: 根因=关键决策：依赖选型, 解决方案=任务描述称 qtbase/6.11.1"含 Qt6Core/DBus"，但配方与 notes 证实 qtbase/6.11.1 的 `FEATURE_dbus=OFF`；Qt6DBus 只由 qtbase-sql-dbus/6.11.1 提供（依赖 dbus/1.14.10）
- **3**: 根因=make jobserver mkfifo: Operation not permitted, 解决方案=平台限制（临时目录 mkfifo 受限），无实际影响

### 验证命令
```
conan create archives/k/kdbusaddons/6.14.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
# exit 0；test_package: 1/1 tests passed；test_kdbusaddons 直接运行 exit 0
```

产物：`lib/libKF6DBusAddons.so`（ELF arm64 共享库）、`bin/kquitapp6`、`include/KF6/KDBusAddons/` 公共头、`lib/cmake/KF6DBusAddons/` 的 Config/Version/Targets/Macros、`share/qlogging-categories6/` 日志分类。

## 补充说明

- 上游 autotests 需要运行中的 D-Bus session bus；CI 沙箱无 dbus-daemon 且 unix socket 创建被禁，配方保持 `BUILD_TESTING=OFF`（避免 CI 失败）
- 本机 OHOS 沙箱已自建 dbus-daemon 1.14.10 + abstract session bus 实测运行上游 2 个 autotests 全部通过（2/2 = 100%），证明 D-Bus 功能在 OHOS 上正确，非功能缺陷；完整过程与证据见 `reports/dbus-autotests-run.md`
- 产物含可执行文件 `bin/kquitapp6`（辅助工具，非主产物），本库为 library 包，按 R38 不需要 commands.json
