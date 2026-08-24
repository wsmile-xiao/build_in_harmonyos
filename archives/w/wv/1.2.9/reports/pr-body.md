## PR 信息

- **三方库名称**: wv
- **上游版本**: 1.2.9
- **上游仓库地址**: https://github.com/AbiWord/wv
- **前置依赖关系**: 直接依赖 `glib/2.84.0.1.1`、`libgsf/1.14.58`、`libxml2/2.15.3.1`、`libpng/1.6.58` 和 `zlib/1.3.1.1`；所有依赖均作为独立适配包消费，本 PR 不混入依赖库修改。
- **适配路径**: 路径 A（基础适配）+ 路径 B（知识库扩展）
- **使用知识库**: HarmonyOS PC 三方库适配共性问题；E081/E093/E307/E309；`DRAFT-conan-staticlib-transitive-headers`；`archives/w/wv/1.2.9/reports/path-b-candidate.md`

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | wv 1.2.9 发布包未携带 testsuite |
| 集成测试 | 0 | 上游没有可作为本 PR 门禁执行的独立测试入口 |
| 其他测试 | 0 | 无 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|-----------:|------|
| Conan test_package | 1 个可执行文件 | +1 | 真实链接 `libwv` 并调用公开 API |
| 鸿蒙消费者断言 | 3 | +3 | 覆盖 `wvInitDTTM`、`wvInitSHD`、`wvInitDCS` 及初始化结果 |
| **合计** | **1 个可执行文件 / 3 个断言** | **+1 / +3** | |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无可执行 testsuite，适配后补全了 Conan 消费者测试

- **补全的测试范围**:
  1. 编译并链接安装后的 `wv::wv` Conan target。
  2. 调用三个公开初始化 API。
  3. 校验三个数据结构的关键字段均被初始化为零。
- **补全原因**: 上游 1.2.9 发布包未提供测试套件，消费者测试用于验证头文件、依赖传播、链接产物和最小运行时 API。
- **新增测试文件清单**:
  1. `archives/w/wv/1.2.9/test_package/conanfile.py`
  2. `archives/w/wv/1.2.9/test_package/CMakeLists.txt`
  3. `archives/w/wv/1.2.9/test_package/test.c`

---

## 验证结果

- 编译状态: 通过
- 上游测试用例通过率: 0/0（上游未提供 testsuite，不声明百分比）
- 新增消费者断言通过率: 3/3（100%）
- Shadow CI runner: `codex-wv-r18-wv-wv-1.2.9-shadow-r18-20260821-234825-21984`
- Conan create: 通过
- L0/L1/L4/L5: 通过
- L2: 非阻塞 skip，已安装 CLI 均不满足 version/help 探针
- Build Summary: Total 1, Success 1, Failed 0
- Package: `wv/1.2.9#66cd91e92991b63c66b81ca115a34fae:e2e9c2e2ac191f51e4f1e065fc93d0516a8b9a91#65123a5bfba4c59303953b28ba72dff3`

---

## 知识库扩展说明

- 新增 `knowledge/drafts/E336-draft-wv-libgsf-header-closure.{kv,md}`。
- shadow r11 中，`wvSummary.c` 已获得正确 libgsf include 路径，但因未直接包含声明所有者 `gsf-doc-meta-data.h`，三个 metadata API 被按旧式隐式 `int` 处理，并产生两个指针转换编译错误。
- 仅增加直接头文件后，shadow r13 中 `wvSummary.o` 编译、`wvSummary` 链接及 wv 包创建均通过，构建推进到独立的 test_package CMake 工具发现问题。
- 草稿沉淀的通用规则是：旧 C 源码在依赖头文件拆分后必须直接包含 API 所属公共头，不应关闭 `implicit-function`/`int-conversion` 诊断、手写函数声明或全局强制 include。
- 已与 E081/E093（目标 libc 缺失 API）、E309（包缺生成公共头）、E307（测试缺 CMake）及既有 Conan `transitive_headers` 草稿划清边界。
- 详细前后对照和诚实边界见 `archives/w/wv/1.2.9/reports/path-b-candidate.md`；最终 B 类认定以赛事评审为准。

---

## 补充说明

- 关联任务: `contrib-2910`
- 任务分支: `feat/wv-1.2.9`
- PR 源分支: `feat/wv-1.2.9`（与任务分支逐字一致）
- 目标分支: `OpenHarmonyPCDeveloper/build_in_harmonyos:main`
- 代码路径: `archives/w/wv/1.2.9`
- 知识草稿: `knowledge/drafts/E336-draft-wv-libgsf-header-closure.{kv,md}`
- 已知限制: 上游无 testsuite；当前消费者测试为 1 个可执行文件、3 个 API 断言，未覆盖完整 Word 文档解析。
- 适配边界: 本 PR 仅包含 wv 目录和 wv 直接相关知识草稿，不修改基础设施目录或依赖库配方。
