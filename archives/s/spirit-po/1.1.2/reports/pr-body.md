- **三方库名称**：spirit-po
- **上游版本**：v1.1.2
- **上游仓库地址**：https://github.com/cbeck88/spirit-po
- **适配路径**：路径 A（基础适配）+ 路径 B（知识库扩展）
- **使用知识库**：openharmony-compile-agent；边界参考 E035、E099、E257、E307、E321、E322；新增候选 E543

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 126 | `test/main.cpp` 自研 `TEST`/`CHECK_*` 宏的运行时 assertion 计数 |
| 集成测试 | 206 | `test_libintl/main.cpp` 按 `test_libintl/po/*.po` 枚举的 PO 数据驱动 executable-level cases |
| 其他测试 | 0 | 上游无其他独立测试套件 |
| **合计** | **332** | **126 assertion + 206 data-driven cases；不把构建变体重复计入分母** |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|-------------|------|
| 单元测试 | 126 | 不变 | 上游 `test/main.cpp`，126/126 通过 |
| 集成测试 | 206 | 不变 | 保留完整分母；OHOS 缺 `libintl.h` 与 libintl 链接库，206 项按证据跳过 |
| 鸿蒙特有测试 | 0 | 不变 | 不伪造 OHOS 特性测试；独立消费者测试单列 |
| **合计** | **332** | **不变** | 126 PASS + 206 SKIP / 332，0 FAIL |

**独立 Conan 消费者测试**：1 个可执行用例，1/1 通过；不与上游 332 重复。

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试

## 验证结果

- 编译状态：通过（OHOS aarch64，clang 15，`conan create` 成功；`test_package` 退出 0）
- 上游测试用例通过率：126/332（38.0%；另有 206 项因明确 OHOS 能力缺失按证据跳过，0 FAIL）
- 新增测试用例通过率：1/1（100%）
- W3 `build_and_test.sh`：Success 1 / Failed 0（L0 pass，L1 pass，L2 skip-无bin，L4 pass，L5 warn-无产物）

## 补充说明

- 首次上游 clang 编译报 `exceptions.hpp:24:3: error: unknown type name 'uint'`；用规范 `refresh-patch --auto` 生成两个 `std::size_t` portability 补丁，不改上游测试、不引入 `#ifdef __OHOS__`。
- libintl 206 项跳过具体技术原因：本 OHOS worker 有 `msgfmt 0.26`，但没有 `libintl.h`，也没有 `libintl.so/.a`；上游 `test_libintl/CMakeLists.txt` 要求 `find_package(Intl REQUIRED)` 并链接 `${INTL_LIBRARIES}`，不能以 msgfmt 冒充运行时时对照。属允许的「环境限制/缺特性」类别。
- 依赖为已发布并经 W0 核验的 `boost/1.90.0`；本 PR 不修改共享 Boost 配方。
- 知识库路径 B：E543 候选草稿已随本 PR 提交；对应路径 B Issue 已按官方模板填写申请人/队伍，并与本 PR 关联。
