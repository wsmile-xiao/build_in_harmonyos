# pybind11 3.1.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only 头文件库）
- 编译日期: 2026-09-20
- 编译器: clang/clang++ 15.0.4 (aarch64-linux-ohos, OHOS SDK 26.0.0.18)
- 状态: built（本地 W3 验证通过，待 CI/release 流水线发布）

## 源码与校验
- 上游: https://github.com/pybind/pybind11 (v3.1.0)
- sha256: ef712655692a2e9bf7bb7874c022564a45f91d847ddee987e720cd9e28849665
- 官方 URL 直连不可达（worker 网络限制），下载经 ghfast.top 镜像代理（字节与官方一致，sha256 实测），
  conandata.yml 保留官方 URL，CI 构建期由 build_and_test.sh 自动注入镜像 fallback（E017 同机制）。

## R47 语言判定（lang-preflight 误判记录）
- 工具输出: detected=python / env_unsupported（manifest=pyproject.toml 优先、绑定覆盖要求 cpp≥70% 未触发）。
- 判定依据: SKILL R47 边界规则明确"pybind11 绑定包判 cpp"；历史 2.10.1 published 归档同为 cpp；
  DRAFT-onnx 官方裁定同模式（C++ 库 + Python 绑定/打包仓库判 python）为误判；本库交付物为
  include/pybind11/*.h 头文件库（project(pybind11 LANGUAGES CXX)、install(TARGETS pybind11_headers EXPORT)），
  pyproject.toml 仅承载可选 Python 打包。→ 按 cpp 继续适配，误判作为知识候选记录（七轴查重见下）。

## 编译步骤
1. init-build: 下载官方 tarball → 解压 .orig/.work → 骨架。
2. conan-verify（G0-G4 全 PASS，含 conan create 干净构建 + test_package 消费者编译/运行）。
3. 上游测试套件: 独立构建目录 PYBIND11_TEST=ON + 宿主 python3.12 构建全部 11 个测试扩展模块，
   重链接 libpython3.12（cmake 直出模块在 OHOS 上 dlopen EACCES，显式链接 libpython 后可加载）→ pytest 全量运行。

## 上游测试双口径台账（r02 最终版，2026-09-20）
统计口径: 全目录 tests/ 完整枚举（用户测试源 77 个 test_*.py 驱动 + 74 个 test_*.cpp 模块 +
框架头/样例/子目录/fixture + 12 个测试扩展模块）。

- source_declared_total: 1349 项（pytest 收集：77 个 test_*.py 驱动的全部用例项；
  另 74 个 test_*.cpp 为 C++ 侧绑定实现模块，随扩展模块编译进 pybind11_tests 等 12 个 .so，
  由 pytest 项消费，不重复计数为独立用例；框架头 constructor_stats.h/local_bindings.h/
  pybind11_tests.h 等为测试支撑头，非独立用例；tests/pure_cpp、test_cmake_build、extra_*、
  test_with_catch 为子目录构建样例/额外包，非 pytest 用例，单独计数）。
- configured_executable_total: 1349（当前 OHOS 配置下 12 个扩展模块全部构建成功并可导入；
  较 r01 增加 eigen_matrix/eigen_tensor 等模块——r02 以 C++20 + Eigen3 重建并装 numpy/scipy）。
- executed_passed_total: 1324
- failed: 1（test_cross_module_exception_translator, RuntimeError，见下）
- skipped: 21（上游条件跳过，见下；r02 已从 r01 的 51 项逐项消除 30 项）
- xfailed: 2 / xpassed: 1（test_unnamed_namespace_a，上游 PR#4319 已知问题）
- 全量通过率: 1324/1349 = 98.15%；当前配置可执行集合通过率: 1324/1328 = 99.70%
  （可执行 = 收集 1349 − 跳过 21 = 1328；未通过 4 = 1 failed + 2 xfailed + 1 xpassed）

r02 消除的 30 项 skipped（原 51 项）:
- C++17/20 头文件与特性类（<optional>/<string_view>/<variant>/<filesystem>/<barrier>/
  <span>/std::monostate/__cpp_inline_variables/__cpp_noexcept_function_type 等约 28 项）:
  r01 测试模块按编译器默认 gnu++14 构建致特性宏未定义 → r02 以 -DCMAKE_CXX_STANDARD=20
  重建全部 12 个扩展模块，这些用例转实跑并通过。
- eigen_matrix/eigen_tensor 模块（r01 未构建）: r02 以 Eigen3 3.4.1（ohpcd registry）提供
  EIGEN3_INCLUDE_DIR 重建 → eigen 系列用例实跑；scipy 依赖经 pip 安装 1.18.1 消除 2 项。
- <boost/optional>（test_stl）: r02 安装 boost/1.84.0 头文件并带 -DPYBIND11_TEST_BOOST 重编
  test_stl.cpp → 转通过。
- PYBIND11_HANDLE_REF_DEBUG（test_pytypes::test_accessor_moves）: r02 带该宏重编
  test_pytypes.cpp → 转通过。

失败用例逐项说明:
- test_exceptions.py::test_cross_module_exception_translator（RuntimeError，r02 重跑确认）:
  跨模块异常翻译器在 OHOS 上不生效——上游测试自身在 ANDROID/FREEBSD/MACOS 平台标记 xfail
  （See Issue #2847, PR #2999/#4324/#5925），OHOS 与 Android 同为受限动态加载语义，
  跨 .so 注册的 py::register_exception_translator 在另一模块抛异常时查不到翻译器。
  属上游已知平台行为，非本配方缺陷；恢复条件: 上游修复跨模块翻译器注册机制。

跳过用例分类（21 项，r02 逐项核证均为真实上游/平台/Python 版本条件，非本库可修）:
- <ranges>（test_pytypes 3 项）: 上游显式排除 clang<16（test_pytypes.cpp 守卫引用
  llvm/llvm-project#52696）；OHOS 工具链 clang 15.0.4 → 真实上游工具链条件。
- C++20 非类型模板参数（test_pytypes 2 项）: __cpp_nontype_template_args 在 clang15 未定义
  （实测 VAL=0）→ 工具链特性缺口；恢复条件: clang16+/GCC11+。
- <experimental/optional>（test_stl 1 项）: clang15 libc++ 不提供该实验头（实测 MISSING）→
  平台头文件缺口。
- NDEBUG cast safety（test_native_enum 1 项）: Release 构建定义 NDEBUG，上游显式跳过
  cast 安全检查（源码 165 行字符串）；恢复条件: 非 NDEBUG 构建。
- GIL deadlock（test_thread 1 项）: 宿主 CPython 3.12.9 GIL 启用，上游标记跳过防死锁。
- interpreters legacy/3.14.0b3+（test_multiple_interpreters 6 项）: 宿主 Python 3.12.9 低于
  3.14.0b3、interpreters 模块不支持 config 参数 → Python 版本条件；恢复条件: 3.14+。
- managed dict traversal（test_class 1 项）: 宿主 CPython 3.12.9 缺 3.13.13+/3.14.4+
  特性 → Python 版本条件。

## HarmonyOS 专项测试（消费者验证）
- test_package/test.cpp: 消费者视角编译探测——包含 <pybind11/pybind11.h>，静态断言
  PYBIND11_VERSION_MAJOR==3/MINOR==1/PATCH==0/HEX==0x030100F0，运行期打印
  "pybind11 3.1.0 (hex 0x030100F0) CXX17=yes"。
- 实际运行: conan create 内 test() 执行 ./test_pybind11 → exit 0，真实输出如上（R34 实质 API 调用）。
- Python.h 编译期硬依赖由 test_package generate() 注入宿主 sysconfig include（非包依赖，L0i 解析为空）。

## 知识候选台账与路径判断
候选 1（已验证、可跨库复用 → 路径 B new_draft）: lang-preflight 对"C++ 头文件库 + Python 绑定/打包"
仓库误判 python。真实错误: detected=python + env_unsupported；根因: _manifest_scan 的
pyproject.toml 优先于 CMakeLists.txt，绑定覆盖要求 cpp 占比≥70%（pybind11 仓库 .py 测试驱动
抬高计数致 cpp 51%）→ 覆盖不触发；修复/方案: 交付物语言证据升级（CMake project LANGUAGES CXX +
install(TARGETS) 导出目标 + 绑定开关默认 OFF 为准）；验证: 本任务 conan-verify G0-G4 全过 +
pytest 1324/1349 实跑；适用范围: 所有"C++ 库 + 根级 pyproject.toml/setup.py"三方库。
七轴查重 vs 既有草稿（DRAFT-onnx-1.20.0-lang-preflight-pyproject-priority-cpp-deliverable-misdetect、
DRAFT-libcec-8.1.7-langpreflight-binding-subdir-misdetect、DRAFT-libuninameslist-langpreflight-setuptools-binding-misdetect）:
- exact_duplicate: false（对象库不同，pybind11 为绑定框架本体）
- causal_duplicate: false（同为 lang_preflight 误判家族，但触发细节不同：onnx=nanobind 未入标记；
  pybind11=标记命中但 cpp 占比不足）
- trigger_overlap: true（pyproject 优先 + 绑定覆盖阈值，与 onnx 草稿触发条件重叠）
- solution_overlap: true（deliverable-language-evidence-escalation 同为推荐方案）
- combination_novelty: true（pybind11 为"绑定框架本体 + 头文件交付物"的判 cpp 强案例，
  R47 规则文本与工具实现冲突的官方口径记录）
- boundary_novelty: true（SKILL R47 明文"pybind11 绑定包判 cpp"与 lang_detect 实现不一致，
  边界规则应覆盖 70% 阈值的适用性）
- test_migration_novelty: false（无测试迁移）
结论: 部分重复但新增差异（pybind11 判 cpp 的强边界案例 + R47 明文 vs 工具实现冲突）已由本轮
真实日志验证 → new_draft（DRAFT-pybind11-3.1.0-langpreflight-cpp 同 stem .md/.kv 配对）。

候选 2（既有草稿覆盖，复用）: OHOS clang15 libc++ C++20 头文件缺口 → DRAFT-ohos-clang15-libcxx-cxx20-capability-gaps
已存在，reuse_existing。
候选 3（非噪声但仅本库，不跨库）: cmake 直出测试 .so 在 OHOS dlopen EACCES、显式链接 libpython
后可加载——本地验证环境问题，配方 PYBIND11_TEST=OFF 不触发，不计入知识草稿（如实记录于台账）。
候选 4（r02 新增、已验证、可跨库复用 → new_draft）: 上游测试大量 "no <头文件>/feature not
available" skip 的根因常是测试模块按编译器默认标准（gnu++14）构建而非头文件缺失——r02 以
-DCMAKE_CXX_STANDARD=20 重建测试模块，C++17/20 特性类约 28 项 skip 转实跑通过（51→21 skipped，
1324 passed）；真正不可消除仅三类（<experimental/optional> libc++ 不提供、clang15 未定义
__cpp_nontype_template_args、<ranges> 上游显式排除 clang<16=llvm#52696）。七轴查重 vs
DRAFT-ohos-clang15-libcxx-cxx20-capability-gaps: causal_duplicate=false（构建标准 vs 头缺失，
实测 c++20 下头可用）、trigger_overlap=true、solution_overlap=false、combination_novelty=true、
boundary_novelty=true（修正"头缺口"叙述边界）→ new_draft（DRAFT-pybind11-3.1.0-test-cxx20-rebuild
同 stem .md/.kv 配对，随本库同 PR 交付）。

路径决定: path_b（知识库扩展）——r01 new_draft 候选 1（langpreflight-cpp）+ r02 new_draft
候选 4（test-cxx20-rebuild）建立草稿，随本库归档同 PR 交付；候选 2 复用既有草稿。

## 依赖版本
- 无 requires/tool_requires（header-only，L0i 解析为空）；Python/pytest 仅测试环境宿主依赖。

## 验证结果
- conan-verify: G0-G4 全 PASS（conan create 干净构建 + 消费者 test() 实跑通过）。
- 上游 pytest: 1151 passed / 1 failed（上游 Android 家族已知）/ 51 skipped（libc++ 缺口）/
  2 xfailed / 1 xpassed。
- W3: conan create 复验通过（见 .ci-result.json）。

## 注意事项
- PYBIND11_NOPYTHON=ON: 配方构建阶段零 Python 依赖；Python.h 仅消费者编译期需要。
- 上游测试需宿主 python3.12 + pytest + numpy（已装 numpy 2.5.3），扩展模块需显式链接
  libpython3.12 方可 dlopen。
---

**编译结束**: 2026-09-21 03:44
**最终状态**: built
