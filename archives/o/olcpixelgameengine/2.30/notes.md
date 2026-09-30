# olcpixelgameengine 2.30 适配笔记

## 编译环境
- 构建系统: 无（单头文件 C++17 库，header-only 打包）
- 编译日期: 2026-09-29
- 编译器: clang/clang++ 15 (aarch64-unknown-linux-ohos, OHOS SDK 26.0.0.18)
- 状态: built（本地 conan create 验证通过，待 CI）

## 编译步骤
1. init-build：官方 tag 源码包 https://github.com/OneLoneCoder/olcPixelGameEngine/archive/refs/tags/v2.30.tar.gz
   sha256=fc7a5eced74bbc83dda217c367caf633d6108da811a6342e9742e035eaada7ea
2. lang-preflight：detected=cpp（源码 7 个 cpp，主体占比 100%）→ 通过
3. 适配验证：OHOS aarch64 工具链实测 `-DOLC_PGE_HEADLESS` 无头模式可编译、可链接、可运行
   （探针程序构造 olc::Sprite 像素回读 + PixelGameEngine::Construct 返回 OK）
4. conan-init 生成配方后改写为 header-only（见"遇到的问题"）
5. conan create 验证（G2）+ 消费者用例 test_package/test.cpp

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 默认生成 autotools 配方 | 无构建系统被误判为 autotools | 按 v12.21 header-only 模板改写 conanfile.py：package() 直接拷贝头文件，无 build() |
| 2 | conandata.yml sha256 为占位符 | 模板默认 | 实测 tarball 得 fc7a5eced74bbc83dda217c367caf633d6108da811a6342e9742e035eaada7ea 回填 |
| 3 | 许可证被误判为 MIT | 模板默认 | 上游 LICENCE.md 为 OLC-3，已修正 license=OLC-3 |
| 4 | test_package 模板生成空壳 test.c（只打印） | autotools 模板默认 | 重写为 test.cpp 真实消费者用例：OLC_PGE_HEADLESS 下调用公开 API（Sprite 像素读写/无头 Construct/Pixel 颜色），3 断言 |
| 5 | OHOS 无上游原生窗口后端（X11/GLUT/Win32/Emscripten 均不适用） | 上游平台层覆盖不足 | 采用上游原生 OLC_PGE_HEADLESS 无头模式（OLC_PLATFORM_HEADLESS/OLC_GFX_HEADLESS 为上游实现，非空壳 stub），不改上游头文件；消费方编译时定义 OLC_PGE_HEADLESS |
| 6 | 编译告警 9 条 missing-override（Platform_Headless/Renderer_Headless） | 上游代码风格 | 非错误，不影响编译链接运行；按上游原样保留 |

## 源码修改
无（无补丁；headless 为上游原生能力，未修改上游头文件）

## 依赖版本
无第三方依赖（header-only，零 requires）

## 上游测试台账（完整枚举 + 双口径）

### 枚举清单（上游 tag v2.30 源码，按目录逐项分类）

| 入口 | 数量 | 分类 | 是否独立上游用例 | 是否实际运行 | 说明 |
|------|------|------|----------------|--------------|------|
| examples/TEST_Animate2D.cpp | 1 | 样例程序 | 否 | 未运行 | 需窗口后端（窗口模式），非测试框架用例 |
| examples/TEST_Camera2D.cpp | 1 | 样例程序 | 否 | 未运行 | 同上 |
| examples/TEST_Hardware3D.cpp | 1 | 样例程序 | 否 | 未运行 | 同上（还需 OpenGL） |
| examples/TEST_Patches.cpp | 1 | 样例程序 | 否 | 未运行 | 同上 |
| examples/TEST_QuickGUI.cpp | 1 | 样例程序 | 否 | 未运行 | 同上 |
| examples/TEST_Shaders.cpp | 1 | 样例程序 | 否 | 未运行 | 同上 |
| extensions/olcPGEX_*.h | 11 | 扩展头文件 | 否 | 编译验证（打包导出） | Graphics2D/Graphics3D/Network/PopUpMenu/QuickGUI/RayCastWorld/Shaders/Sound/SplashScreen/TransformedView/Wireframe |
| utilities/olcUTIL_*.h | 8 | 工具头文件 | 否 | 编译验证（打包导出） | Animate2D/Camera2D/Container/DataFile/Geometry2D/Hardware3D/Palette/QuadTree |
| tools/wasm/* | 3 | 构建工具脚本 | 否 | 未运行 | README/basic_template.html/pge2wasm.bat（WebAssembly 构建辅助） |
| contributions/README.md | 1 | 文档 | 否 | 未运行 | 第三方贡献说明 |
| olcExampleProgram.cpp | 1 | 示例程序模板 | 否 | 未运行 | 新项目模板程序 |
| olcPixelGameEngine.h | 1 | 主头文件 | 否 | 编译验证（消费者/鸿蒙测试） | 库本体 |
| LICENCE.md / README.md | 2 | 文档 | 否 | — | OLC-3 许可证 / 使用说明 |

### 双口径统计

- 上游**无正式测试套件**：无 tests/ 目录、无 ctest/GTest/pytest 注册、无 `make check` 目标；
  examples/TEST_*.cpp 为需要窗口/图形后端的样例程序，非测试框架的独立用例，不计入独立上游用例。
- `source_declared_total`（官方 tag 源码独立测试用例声明总数）= **0**
- `configured_executable_total`（当前 OHOS 配置实际实例化/注册的独立可执行用例数）= **0**
- `executed_passed_total` = 0，失败 = 0，未运行/未实例化 = 0（无独立用例）
- 全量通过率 = **0/0（n/a）**；映射链：无独立用例声明 → 无预处理/构建条件 → 无构建目标 → ctest -N 无上游注册项 → 无上游执行日志
- 本轮新增且实际运行的用例（与上游分别计数）：
  - 消费者用例（test_package/test.cpp）：1 个，编译链接运行通过（ctest 1/1 Passed）
  - 鸿蒙专项测试（test_ohos/ohos_pge_test.cpp）：1 个，OHOS 工具链编译运行通过（failures=0）

## 知识候选台账（knowledge_candidate_ledger）

### 候选 A：OHOS 无原生窗口后端的单头文件游戏引擎 → 上游无头编译模式
- **真实错误**：默认包含头文件编译失败——`__linux__` 自动选 OLC_PLATFORM_X11，OHOS sysroot 无 `X11/X.h`/`Xlib.h`
- **根因**：上游平台选择仅覆盖 Win32/X11/GLUT/Emscripten；OHOS PC 无原生窗口后端（E471 同款平台事实）
- **修复**：使用上游原生无头模式（编译宏 `OLC_PGE_HEADLESS` → `OLC_PLATFORM_HEADLESS`/`OLC_GFX_HEADLESS`/`OLC_IMAGE_HEADLESS`，上游实现非空壳），零补丁零改上游头；消费方以 `-DOLC_PGE_HEADLESS` 使用
- **验证**：test_package 消费者用例 ctest 1/1 Passed；test_ohos 鸿蒙专项测试 5 断言 failures=0（OHOS 工具链直接编译运行）
- **适用范围**：自带真实无头/离屏编译模式的窗口化图形库、游戏引擎（单头文件 C++17 类）
- **四范围查重**：正式知识 index.tsv 命中 E471（OHOS 无显示后端分类+探针）、E464（mygui dummy headless 验证）、E472（SDL dummy driver headless）部分覆盖；knowledge/doc/ 无直接重复；knowledge/graph/ E257/E321 关联；knowledge/drafts/ DRAFT-7353-raygui（需宿主后端，反例）
- **七轴查重**：exact_duplicate=false；causal_duplicate=false；trigger_overlap=部分（OHOS 无显示/窗口后端同源）；solution_overlap=部分（无头验证思路一致，机制不同：编译期宏 vs E464 运行时 dummy 资源 vs E472 环境 dummy 驱动 vs E471 测试分类）；combination_novelty=true（单头文件游戏引擎+上游 HEADLESS 宏+header-only 打包+消费方宏定义）；boundary_novelty=true（边界：上游自带真实无头模式才适用；反例 raygui 无无头模式须写后端/分类）；test_migration_novelty=true（OHOS 工具链直接运行无头引擎用例+消费者宏定义用例）
- **关系**：similar_to E471、similar_to E464、similar_to E472；prerequisite_of 无；conflicts_with 无
- **决定**：**new_draft（路径 B）**——草稿 `knowledge/drafts/DRAFT-olcpixelgameengine-2.30-olc-pge-headless-mode.{kv,md}`（同 stem 配对），随本 PR 交付

### 候选 B：conan-verify G1 要求 header-only 配方含 build()/export_sources()/补丁调用
- **真实错误**：G1 FAIL——"conanfile.py 缺少: build() 方法 / export_sources() 方法 / 补丁应用调用"
- **根因**：G1 为字符串级配方完整性检查，面向通用配方模板
- **修复**：补 `export_sources()`=export_conandata_patches(self)；`build()` 做真实完整性检查（校验主头存在，R34 不伪造编译日志）
- **验证**：conan-verify G1 PASS
- **查重**：E257（DRAFT-bshoshany-thread-pool-5.0.0-header-only-g1-build-gate）完整覆盖同类门禁 → exact/causal_duplicate=true，solution_overlap=完全
- **决定**：**reuse_existing E257**（不建草稿）

### 候选 C：Conan 2 header-only 包 package_type 误标 library
- **真实错误**：`ERROR: olcpixelgameengine/2.30@ohpcd/stable: Package type is 'library', but no 'shared' option declared`
- **根因**：Conan 2 的 library 类型要求声明 shared option；header-only 应使用 header-library
- **修复**：`package_type = "header-library"`；另注意 `copy()` 的 dst 必须用 `os.path.join(self.package_folder, ...)` 绝对路径（相对 dst 在 basic_layout 下解析到 build 目录 → `WARN: No files in this package!`）
- **验证**：G2 conan create + test_package 通过
- **查重**：E321（published）+ E322（cpp-taskflow 草稿）完整覆盖 header-only Conan2 header-library 打包 → causal_duplicate=true，solution_overlap=完全
- **决定**：**reuse_existing E321**（不建草稿）

### 路径决定汇总
- **path_b_new_draft**：候选 A → 路径 B（【知识库扩展】），new_draft 草稿已建（.kv/.md 配对）
- 候选 B/C 复用既有知识（E257/E321），不另建草稿
- 无 path_a_no_knowledge（本任务产生可跨库复用的新增知识）

## 验证结果
```bash
# OHOS 探针（直接源码编译运行）
/data/service/hnp/bin/clang++ -std=c++17 -O2 -fPIC -I<src> -pthread ohos_headless_probe.cpp -o ohos_headless_probe
./ohos_headless_probe
# → OHOS_HEADLESS_PROBE pixel=0xFF0000FF construct_rc=1 (rcode::OK=1)，退出码 0

# 消费者用例（conan create 内 test_package）
./test_olcpixelgameengine
# → CONSUMER sprite_pixel=0xFFFF0000 (BLUE) / construct_rc=1 (OK) / pixel_color=0xFF0000FF (RED)，CONSUMER_RESULT failures=0
```

## 交付物
| 文件 | 说明 |
|------|------|
| archives/o/olcpixelgameengine/2.30/conanfile.py | header-only 配方（OLC-3） |
| archives/o/olcpixelgameengine/2.30/conandata.yml | 官方 URL + sha256 |
| archives/o/olcpixelgameengine/2.30/test_package/ | 消费者用例（test.cpp + CMakeLists + MANIFEST） |
| archives/o/olcpixelgameengine/2.30/test_ohos/ | HarmonyOS 专项测试 |

## 注意事项
- 消费方必须在编译单元定义 `OLC_PGE_HEADLESS`（+ `OLC_PGE_APPLICATION`）才能使用本包；
  有窗口需求的业务方需自行提供窗口/渲染后端（如移植 X11/EGL 后端或接入 OHOS 图形栈）。
- 头文件 OLC_PGE_HEADLESS 编译有 9 条 upstream missing-override 告警，属上游原样，不影响使用。
---

**编译结束**: 2026-09-29 04:03
**最终状态**: built
