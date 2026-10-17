# libbpp-seq 2.4.1 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-16
- 编译器: clang/clang++
- 状态: built（待真机预检回填实测通过率）
- 上游仓库: https://github.com/BioPP/bpp-seq
- 上游版本: v2.4.1（tarball sha256 dbfcb04803e4b7f08f9f159da8a947c91906c3ca8b20683ac193f6dc524d4655）

## 编译步骤

1. `get()` 下载 `https://github.com/BioPP/bpp-seq/archive/refs/tags/v2.4.1.tar.gz` 并校验 sha256。
2. `CMakeToolchain` 设置 `BUILD_TESTING=ON`、`CMAKE_POLICY_VERSION_MINIMUM=3.5`、`BUILD_SHARED_LIBS` 与 `CMAKE_POSITION_INDEPENDENT_CODE` 随 `shared/fPIC` 选项，并预置 `CMAKE_PREFIX_PATH=<build_folder>/bpp-core-prefix`；`CMakeDeps` 生成依赖信息（当前无外部 requires，仅占位）。
3. `build()` 先构建 vendor bpp-core（同工具链、`BUILD_TESTING=OFF`、`--parallel 1`、安装到 `bpp-core-prefix`，cmake 可执行文件优先 `HMBS_CMAKE`，构建目录均为 build_folder 子目录，不写只读 /tmp）；再 `cmake.configure()` + `cmake.build()` 构建 `bpp-seq-static` 与 `bpp-seq-shared`（OUTPUT_NAME 均为 `bpp-seq`，SOVERSION 12），头文件安装至 `include/Bpp`，CMake 包文件安装至 `lib/cmake/bpp-seq`；`package()` 合并 `bpp-core-prefix` 全量产物，`package_info()` 声明 `libs=["bpp-seq", "bpp-core"]`。
4. `build()` 内运行 `ctest --output-on-failure`：上游 `test/` 下 7 个 `.cpp` 用例（test_alignment_scores、test_alphabets、test_bowker、test_containers、test_io、test_sequences、test_walker）分别编译为独立可执行文件并注册为 ctest 用例，输出 `HMBS_UPSTREAM_TEST_RESULT` 标记。
5. `cmake.install()` 打包；`test_package` 以消费者视角编译运行 `test_bpp_seq.cpp` 并输出 `HMBS_TEST_PACKAGE_RESULT` 标记。

## 上游测试清点（源码审计，GitHub tag v2.4.1）

- `test/CMakeLists.txt`：`file(GLOB *.cpp)` 每个 `.cpp` 编译为独立程序并 `add_test`，链接 `${PROJECT_NAME}-shared`，`TIMEOUT 60000`。
- `test/` 下测试源（7 个）：
  - test_alignment_scores.cpp — 比对打分矩阵
  - test_alphabets.cpp — DNA/RNA/蛋白/密码子字母表实例化与类型判定
  - test_bowker.cpp — Bowker 同质性检验
  - test_containers.cpp — 序列容器操作
  - test_io.cpp — Fasta/Mase/Clustal/Phylip 等格式读写
  - test_sequences.cpp — BasicSequence 严格/兼并匹配查找
  - test_walker.cpp — SequenceWalker 遍历
- 辅助数据：example.aln、example.fasta、example.fastq、example.gff、example.mase、example.ph、example.ph3（随测试工作目录使用）。
- 开关：顶层 `CMakeLists.txt` 中 `enable_testing()` + `if(BUILD_TESTING) add_subdirectory(test)`，配方中强制 `BUILD_TESTING=ON`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(bpp-core 4.0.0 REQUIRED)` 找不到包；真机预检 `ERROR: Package 'libbpp-core/2.4.1' not resolved` | bpp-seq 2.4.1 强依赖同版本 bpp-core（bpp-core 2.4.1 提供 CMake 包版本 4.1.0），但 libbpp-core/2.4.1 尚未发布到 ohpcd，requires() 在图解析阶段即失败（L0i/R36），编译未开始 | 去掉 `requirements()`，改 vendor：conandata.yml 新增 `bpp_core`（v2.4.1 tarball），`source()` 双 get，`build()` 先以同工具链把 bpp-core 装到 `build_folder/bpp-core-prefix`（BUILD_TESTING=OFF、jobs=1、私有前缀），再经 `CMAKE_PREFIX_PATH` 配置 bpp-seq；`package()` 合并两套头文件/库/CMake 包配置，保持上游 `find_package(bpp-seq/bpp-core CONFIG)` 语义；单包满足 PF1，L0i 无外部依赖可查 |
| 2 | `cmake_minimum_required(VERSION 2.8.11)` 在新版 CMake 下报错 | 上游声明过旧，不兼容 CMake 4 默认策略 | 设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 进入兼容模式，不修改上游源码 |
| 3 | 上游同时构建 static/shared 两个目标，`BUILD_SHARED_LIBS` 无法二选一 | `src/CMakeLists.txt` 硬编码 `add_library(...-static STATIC)` 与 `add_library(...-shared SHARED)` | 保留上游双目标行为，两个产物都打包；`package_info()` 按 `shared` 选项表达消费者链接意图，不裁剪产物 |
| 4 | Conan 生成的 `bpp-seq-config.cmake` 会遮蔽上游同名包文件 | 若 `cmake_file_name` 设为 `bpp-seq`，CMakeDeps 产物优先于 `lib/cmake/bpp-seq/bpp-seq-config.cmake` | `package_info()` 中 `cmake_file_name` 取 `libbpp-seq`，上游 `find_package(bpp-seq CONFIG)` 继续走前缀路径，两套配置共存 |
| 5 | `src/Bpp/Seq/SymbolList.h:370/614` 报 `use of undeclared identifier 'random_shuffle'`（真机 clang 15 + `compiler.cppstd=17`）| `std::random_shuffle` 在 C++14 弃用、C++17 移除，上游 2.4.1 仍直接调用，ohos-aarch64 预设强制 C++17 | 新增 portability 补丁改用 `std::shuffle` + `std::mt19937`（C++11 起可用），仅替换随机重排实现，不改测试口径 |
| 6 | 构建树 ctest 报 `Error loading shared library ../src/libbpp-seq.so` / `../bpp-core-prefix/lib/libbpp-core.so` | 构建树 shared 库的 DT_NEEDED 为斜杠相对路径，OHOS/musl loader 按测试 WORKING_DIRECTORY 字面解析，不查 LD_LIBRARY_PATH，测试进程起不来 | 新增 testing 补丁：`test/CMakeLists.txt` 中测试可执行文件改链 `${PROJECT_NAME}-static`（测试源码与断言零改动）；`build()` 内 ctest 仍配绝对路径 LD_LIBRARY_PATH 双保险，`test_package` 优先按绝对路径链接静态归档，两套库产物仍全部构建打包 |
| 7 | CI 构建 #48961 报 `FileNotFoundError: 'cmake'`（`_build_bundled_bpp_core` 内 `subprocess.run`）| 裸 `subprocess.run(["cmake", ...])` 继承不到 Conan 聚合 buildenv（`conanbuild.sh`）；CI worker 基础 PATH 既无 cmake 也无 curl，`HMBS_CMAKE`/conf 均未注入，兜底 `"cmake"` 无法解析；`CMake(self)` 走 `self.run()` 不受影响 | 新增 `_cmake_bin()`（`user.hmbs:cmake_path` → `HMBS_CMAKE`/`CMAKE` → `shutil.which` → `/data/service/hnp/bin` 等绝对路径，rapidjson/pam-u2f 先例），vendored 三步共用；新增 `_ctest_bin()`（cmake 同目录 sibling → PATH → HNP 绝对路径），主配方 ctest 改直调不再经 bash 包装，test_package 同步加固（bash 缺失时直调） |

## 源码修改

补丁 `patches/0001-cxx17-random-shuffle-compat.patch`（portability）：`src/Bpp/Seq/SymbolList.h` 中两处 `random_shuffle`（C++17 已移除）在 ohos-aarch64 预设 `compiler.cppstd=17` 下报错 `use of undeclared identifier`，替换为 `std::shuffle` + `std::mt19937(std::random_device()())` 并新增 `<random>` 头文件；`std::shuffle` 自 C++11 可用，C++11/14/17 均可编译。

补丁 `patches/0002-ohos-test-link-static.patch`（testing）：`test/CMakeLists.txt` 中 7 个 ctest 可执行文件由链接 `${PROJECT_NAME}-shared` 改为 `${PROJECT_NAME}-static`；构建树 shared 库的 DT_NEEDED 为斜杠相对路径（`../src/libbpp-seq.so`、`../bpp-core-prefix/lib/libbpp-core.so`），OHOS loader 从测试工作目录无法解析，改链静态后测试源码与断言零改动，两套库产物仍全部构建打包。

## 依赖版本

- bpp-core 2.4.1 源码 vendor（conandata.yml `bpp_core`，提供 bpp-core CMake 包 4.1.0，满足 `find_package(bpp-core 4.0.0 REQUIRED)`；待 libbpp-core 单独发布后可切回 requires）
- 工具链：clang 15、libc++、C++11（上游 `CMAKE_CXX_FLAGS -std=c++11`）、CMake >= 3.5 兼容模式

## 验证结果

```bash
# 真机（HarmonyOS aarch64，与官方 CI 同源）预检：
# conan create archives/l/libbpp-seq/2.4.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 待 HMBS 预检回填：ctest 7/7 与 test_package 8/8 实测数据以预检日志为准
```

- 上游测试：`ctest --output-on-failure`（7 个用例），结果待真机回填。
- test_package：`test_bpp_seq.cpp` 8 项真实 API 断言经 ctest 运行，结果待真机回填。
- 证伪要求：确认参照文件非空、失败可被捕获、区分通过与静默跳过，见预检日志。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方，含上游 ctest 执行与 HMBS 标记 |
| conandata.yml | 官方 GitHub tag 源码 URL + sha256 |
| test_package/test_bpp_seq.cpp | 真实调用 DNA/RNA/蛋白字母表、BasicSequence、SequenceTools、VectorSequenceContainer 的消费者测试 |
| test_package/MANIFEST.yml | 上游 7 用例 + 消费者测试声明 |

## 注意事项

- 本机 Windows 检出时 `archives/l/libXext` 与 `archives/l/libxext` 因大小写不敏感同目录冲突显示为脏文件，与本适配无关，提交时不得将其纳入。
- 首次提交不含 `.hmbs/pr.json`，不执行 commit/push，由 HMBS 在真机全部门禁通过后统一提交。
