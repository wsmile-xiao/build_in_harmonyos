# opencsg 1.8.2 适配 PR 描述

> PR 标题建议：`【知识库扩展】opencsg 1.8.2 HarmonyOS PC 适配（路径 B 候选）`
> （若走积分赛专用申报，按 `templates/积分赛事PR模板.md` 的关键词前缀规则；
> 本文已按该模板结构组织。）

- **三方库名称**：opencsg（OpenCSG）
- **上游版本**：OpenCSG 1.8.2（tag `opencsg-1-8-2-release`，2026-02-08 发布）
- **Conan 包版本**：`opencsg/1.8.2`（与上游一致，未递增后缀）
- **上游仓库地址**：https://github.com/floriankirsch/OpenCSG
- **适配路径**：**路径 A（基础适配）+ 路径 B（贡献创新）**（B 类候选，最终由评审判定）
- **使用知识库**：build_in_harmonyos SKILL（含知识图谱 error-patterns 查询）+ 本 PR 新增的 7 对知识草稿
- **分支**：`feat/opencsg-1.8.2`
- **issue**：本轮不使用 issue 编号

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | OpenCSG 1.8.2 **无单元测试套件**（无 ctest / 无 test 目录） |
| 集成测试 | 0 | 无 |
| 示例程序 | 1 | `example/main.cpp`（GLUT 演示，需真实 GL 上下文） |
| **合计** | **1** | 仅 1 个需真实 GL context 的示例程序 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试 |
| 集成测试 | 0 | 不变 | 上游无集成测试 |
| **鸿蒙消费者测试（新增）** | **1 个测试程序 / 11 项断言** | 新增 | `test_package/test_opencsg.cpp`：9 项确定性断言 + 2 项运行时加载器探针 |
| 鸿蒙特有测试 | 2 | 新增 | 探针断言 `libGLv4.so` 导出 `glGetString`、`libEGL.so` 导出 `eglGetProcAddress` |
| **合计** | **1 程序 / 11 断言** | **+11 断言** | 消费者视角验证安装后的包 |

## 上游测试用例修改说明

- [x] **否**，未修改上游任何测试用例或示例代码。
- `example/` 通过 `-DBUILD_EXAMPLE=OFF` 在构建中关闭（**未删除**），
  因其为需 GLUT + 真实 GL context 的演示程序，留待应用侧/真机可选验证。

## 补全测试用例说明

- [x] **是**，上游无单元测试，适配后补全了消费者测试。

- **补全的测试范围**：安装后的 `libopencsg` 公开 API — 版本宏（2）、`Primitive` 基类
  构造/析构 + `setOperation`/`getConvexity`/`setBoundingBox`（4）、`setOption`/`getOption`（2）、
  `setContext`/`getContext`（1），以及运行时加载器探针（2）。
- **补全原因**：上游仅含示例程序、无正式测试框架，无法在无头 CI 运行。
- **新增测试文件清单**：
  1. `test_package/conanfile.py` — 消费者测试配方（build + 运行，`env="conanrun"`）
  2. `test_package/test_opencsg.cpp` — 消费者测试源（实质调用被测包 API，R34）
  3. `test_package/CMakeLists.txt` — `find_package(OpenCSG)` + 链接 `OpenCSG::opencsg`
  4. `test_package/MANIFEST.yml` — 上游测试声明（CI L0e）

## 验证结果

- **编译状态**：通过（本机 OHOS SDK 交叉编译 + 真机 `conan create` 均通过）
- **上游测试用例通过率**：不适用（上游无测试用例，无执行项）
- **新增测试用例通过率**：11/11（100%）— 设备 shadow CI 实跑，全部 `[ok]`
- 真机 shadow CI 门禁：`L0_RESULT=pass` / `L1_RESULT=pass` / `L2_RESULT=skip: no bin/ dir` /
  `L4_RESULT=pass` / `L5_RESULT=pass`，`L1e` 破坏性反向验证通过，exit code 0

### 编译/产物验证细节

- 本机交叉编译（clang 15.0.4 → aarch64-linux-ohos）：`libopencsg.so.1.8.2` 链接成功（`[18/18]`）。
- 设备 `conan create` 产物：`lib/libopencsg.so`（ELF 64-bit LSB arm64，346560 bytes）。
- `DT_NEEDED=[libc++_shared.so, libc.so]`（**无 GL 链接依赖**，符合"运行期 dlopen"设计）；
  885 个 OpenCSG 导出符号；产物含 `libGLv4.so` / `libEGL.so` 字符串。
- 设备侧确认 `libGLv4.so` 导出 `glGetString`、`libEGL.so` 导出 `eglGetProcAddress`。

### 补丁说明

- `0001-glad-ohos-opengl-loader.patch`：`src/glad/src/gl.cpp` — glad 候选库名追加
  `libGLv4.so`；过程地址助手在 `glXGetProcAddressARB` 取不到时回退 `libEGL.so` 的
  `eglGetProcAddress`。**POSIX 通用写法，不引入平台宏**（R8 / preflight PF5）。
- `0002-src-CMakeLists-optional-opengl-lookup.patch`：`src/CMakeLists.txt` — `find_package(OpenGL REQUIRED)`
  降为可选（该目标不链接 GL；OHOS 无 GL 开发包）。两补丁对其他平台透明，符合 R8。

### 依赖

无 Conan 编译期依赖。运行期依赖设备提供的 `libGLv4.so` / `libEGL.so` 与 `libc++_shared.so`。

## 路径 B（贡献创新）候选说明

详见版本级 `PATH_B_CANDIDATE.md`。除本库适配外，本次从真实真机验证中提取了 **7 对可复用知识草稿**
（`knowledge/drafts/opencsg-1.8.2-*`），面向不同复用场景，其中多条适用于任何图形类/运行时加载型库：

| # | 草稿主题 | 通用价值 |
|---|---------|---------|
| 1 | 桌面 GL 运行时 dlopen 库在 OHOS 的适配（`libGLv4.so`+`libEGL.so`） | 所有 glad/glew 私有拷贝渲染库 |
| 2 | 无头 CI 真测试契约（无上下文断言 + 加载器探针） | 所有需 GPU/设备上下文的库，过 R34/L1e |
| 3 | 隔离 job hnp 工具链 PATH（`cmake: Error 127`） | 所有用 cmake/make/ninja 的 CI job |
| 4 | OHOS CMake 缺 Platform → 无 SONAME（含最小复现） | 所有 CMake 共享库 |
| 5 | `DT_NEEDED` 验证法（运行时加载型库 R26 自查） | 所有运行时加载型/系统同名库风险包 |
| 6 | 上游 tag 名≠版本号的归档选择 + 干净 `.tar.gz` basename | 所有 GitHub/GitLab tag 归档配方 |
| 7 | `make jobserver mkfifo` 非致命判据 | 所有 OHOS 并行 make 构建 |

## 补充说明

- 真机 shadow CI 已执行并通过（隔离 job + `ohos-test-runner.sh --mode heavy`，单包排队获锁）。
- 真机调用注意：hnp 工具链的 cmake/make/ninja 在 `/data/service/hnp/bin`，运行环境需把该目录
  放入 PATH 并传给 runner 的 `--path`（与既有可用 job 一致）；这不是配方问题，故未在库内加
  `tool_requires("cmake/...")`（ohpcd 无 cmake recipe，会触发 L0i 失败）。
- **未执行**（不视为通过）：制品仓 `conan upload`/release 流水线；`render()` 真实 CSG 渲染
  （需应用侧真实 GL context）；上游单元测试（上游无测试套件）。
- **已知限制**：OHOS CMake 缺 `Platform/HarmonyOS.cmake`，共享库不生成版本化 SONAME
  （最小复现确认，影响所有 CMake 库，非本库补丁问题）。
- 未提交任何生成物（`reports/`、`ci-metadata.json`）与敏感信息（真机 IP / 私钥路径等）。
- 完整结果见 `archives/o/opencsg/1.8.2/notes.md`。
