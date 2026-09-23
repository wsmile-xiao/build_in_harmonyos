# libleidenalg 0.13.0 适配笔记

## 编译环境

- 构建系统: cmake（上游要求 >= 3.23）
- 编译日期: 2026-09-14
- 编译器: clang/clang++
- 状态: built（待真机预检通过后由 HMBS 统一提交）
- 上游版本: 0.13.0（2026-05-24 发布，新增 minimum community size 支持）
- 上游仓库: https://github.com/vtraag/libleidenalg
- 源码包: https://github.com/vtraag/libleidenalg/archive/refs/tags/0.13.0.tar.gz（51600 字节）
- 源码 SHA256: `134e33bf68222b301cf5fbe93b5a8af222f2910caac34b85e33afac6e9365d2a`

## 编译步骤

CMake 标准流程，依赖由 Conan 提供：

```bash
conan create archives/l/libleidenalg/0.13.0 --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

配方关键点：`requirements() igraph/1.0.0`（transitive_headers/libs），
`generate()` 将 `BUILD_SHARED_LIBS` 跟随 `shared` 选项并透传 `fPIC`，
`build()` 依次 `cmake.configure()` + `cmake.build()`，
`package()` 复用 `cmake.install()` 并附带 LICENSE，
`package_info()` 声明 `libs=["libleidenalg"]`、`requires=["igraph::igraph"]`、
`cmake_target_name=libleidenalg::libleidenalg`、`system_libs=["m"]`（Linux/OHOS）。

## 上游测试审计

- GitHub contents API（ref=0.13.0）根目录：无 tests/、test/、testing/ 目录，
  无 CTestTestfile、pytest/tox 配置。
- 根 `CMakeLists.txt`（67 行）：仅 project/find_package(igraph)/add_subdirectory/
  install/export；无 enable_testing/add_test/BUILD_TESTING/add_subdirectory(tests)。
- `src/CMakeLists.txt`：仅 add_library（11 个 .cpp）+ export header + install。
- `include/CMakeLists.txt`：仅 FILE_SET headers（11 个公开头）。
- `example/`：仅 example.cpp 单个演示程序；README 明确说明该目录不包含在
  release 源码包中，不属于自动化测试套件。
- 结论：上游确无测试。`test_package/MANIFEST.yml` 写入 `upstream_tests_exist: false`
  + 非空 `upstream_test_audit`，`upstream_check_command` 置空，
  `upstream_test_in_build: false`；`test_package/conanfile.py test()` 在真实运行
  `./test_leidenalg` 之后输出 `status:"no_tests"`、`discovered:0`、`executed:0` 及 reason。

## test_package 设计

`test_leidenalg.cpp` 基于上游 `example/example.cpp` 扩展为 6 个断言的消费者测试：

1. Zachary 图点数为 34；
2. Zachary 图边数为 78；
3. CPM 分区 optimise 后 membership 合法；
4. CPM 质量不回退（after >= before，有限值）；
5. Modularity 分区 optimise 后 membership 合法；
6. Modularity 质量不回退。

随机种子固定为 42（`set_rng_seed`），CPM resolution 取上游示例值 0.05。
失败时打印 `FAIL:` 并返回非零，HMBS 标记如实翻转为失败；证伪方式：
将 `igraph_famous` 换成非法名称或把期望点数改错，重跑必现 FAIL。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Windows 本机大小写不敏感导致 libXext/libxext 双目录在 `git status` 中常显 modified | 上游同时存在 `archives/l/libXext` 与 `archives/l/libxext`，Windows 合并为同一目录 | 不触碰该目录，本 PR 仅新增 `archives/l/libleidenalg`，由 HMBS 在大小写敏感的真机/CI 侧校验 |
| 2 | 上游测试数无法填写 | 上游确无测试 | 按守则走 no_tests 路径，测试用例数留待真机 evidence 轮填写，本轮不猜测 |
| 3 | 真机 cmake project() 处 CMAKE_C/CXX_COMPILER 检测失败（同指纹多轮复现，TMP 重定向＋STATIC_LIBRARY＋CMakeDeps 后仍失败） | E092：CMake 无 Platform/HarmonyOS 模块，CMAKE_SYSTEM_NAME=HarmonyOS 时编译器 ID 检测失败 | generate() 内把 CMAKE_SYSTEM_NAME 别名为 Linux（cache＋variables 双设，PROCESSOR=aarch64；ball/jwt-cpp 先例），编译器仍用工具链的 OHOS clang；STATIC_LIBRARY（E191）与 CMakeDeps 保留 |
| 4 | 真机 source() 下载 github.com 归档两次 ConnectTimeout（connect timeout=30） | 真机到 github.com 直连超时，非配方逻辑问题 | conandata.yml 的 url 改为有序列表：gh-proxy.com 镜像在前、官方 URL 在最后回退（复用 ci/conan/build_and_test.sh 的 GitHub 镜像映射，sha256 不变） |
| 5 | 真机 cmake project() 处 CMAKE_C/CXX_COMPILER identification unknown 同指纹连续三轮复现，Linux 别名＋STATIC_LIBRARY＋SONAME 路线无效（当时误判 igraph 控制组有效） | 证伪不成立：igraph 仅为缓存命中 Already installed 并非当轮新鲜构建；去掉别名后日志出现 System is unknown to cmake, create: Platform/HarmonyOS，证明 cmake 4.4.3 确无 HarmonyOS 模块，E092 别名仍必需 | 已恢复 Linux 别名但换实现：仅 cache_variables 双设（byte-lite 精确形态，去掉 variables 双设/STATIC/SONAME），新增 conf 编译器可用性守卫与 Environment save_script 持久化 TMP，test_package 同步别名 |
| 6 | 上轮回退未生效：日志 WARN 回退触发但 CMake 仍用 /data/service/hnp/bin/clang(++)，C/CXX identification unknown 同指纹第 3 次复现 | tc.variables 优先级低于工具链 conf 钉死的编译器，CLI -D 的 cache_variables 才能覆盖；且 os.access(X_OK) 在 chmod=0 文件系统不可靠，路径存在不等于可运行 | 本轮改用 cache_variables 覆盖编译器＋subprocess --version 真实可运行探针＋CC/CXX 经 save_script 固化，主与 test_package 同步 |
| 7 | 真机 cmake project() 处 CMAKE_C/CXX_COMPILER identification unknown 同指纹第 4 次复现（generic_system OHOS＋lld/libxml2 探针路线，OHOS 平台名警告已消除但编译器检测仍失败） | 上一方案无效的原因：①平台名不是阻塞变量——NNG 草稿（knowledge/DRAFT-nng-*.md）已实证 unknown-platform 仅为警告级、POSIX 库可构建，且 .kv 明确 forbid CMAKE_SYSTEM_NAME 伪装；Linux 别名→原生 HarmonyOS→OHOS 名三次互斥的身份变异复现同一指纹，反证阻塞点在别处；②lld/libxml2 探针是重复建设——profile 已在基建层注入 SDK llvm/lib 的 LD_LIBRARY_PATH，且裸 `cc src -o bin` 无 sysroot/target 标志，复现不了 CMake 带标志的编译器测试，只能给出假信号 | 本轮换路线：与已验证的同族依赖 igraph（archives/i/igraph/1.0.0，原生 CMakeToolchain、无任何平台名覆盖、无链接器探针）完全对齐——主配方与 test_package 删除 generic_system 覆盖与全部链接器探针逻辑，仅保留 HMBS 点名的 readonly_tmp 修复；新增失败闭环诊断（configure 异常时转储 CMakeError.log/CMakeOutput.log 尾部、clang --version 实测、toolchain 编译器/系统/sysroot 行后重抛），不绕过任何检查、不跳过测试，为下轮提供真凭而非截断摘要 |
| 8 | 上轮新增的诊断探针首次给出决定性证据：`cannot run /data/service/hnp/bin/clang --version: [Errno 2]`（编译器路径在预检沙箱内根本不存在），且 CMakeError/Output.log 在构建树下不存在 | 前六轮全部假设 conf 编译器路径存在、只变异其周围配置（平台名/编译器覆盖/链接器运行库），该假设被证伪——文件级缺失时任何工具链内容变异都不可能生效；旧探针另有一个缺陷：os.access(X_OK) 在 chmod=0 文件系统不可靠，且变量覆盖优先级低于工具链文件 | 本轮新路线（编译器存在性门控）：build() 先实测 conf 编译器可运行则零改动（CI worker 路径保留字节一致）；缺失时从 live 沙箱解析可运行的 SDK clang（PATH→LD_LIBRARY_PATH 兄弟 bin→有界祖先 walk，逐个 --version 实测），仅重写本配方生成的 conan_toolchain.cmake 的两行 set()（不动上游 CMakeLists、不动共享 profile），找不到则 fail-closed 抛错；主与 test_package 同步 |
| 9 | 编译器门控生效：真机解析到 harmonybrew SDK clang 并重写 toolchain，configure 通过、构建推进到 8%，随后 `GraphHelper.h:4:10: fatal error: 'igraph/igraph.h' file not found` | 仓内 igraph/1.0.0 把 includedirs 覆盖为 `["include/igraph"]`，其 CMakeDeps 目标只带 `-I<igraph>/include/igraph`（仅够 `<igraph.h>`）；而上游 libleidenalg 源码用 `#include <igraph/igraph.h>`，需要父目录 `-I<igraph>/include`（官方 igraph 打包本就提供该父目录） | 本轮最小补偿：主配方与 test_package 在 generate() 中经 `self.dependencies["igraph"].package_folder` 取包路径，把 `-I<igraph>/include` 追加进 `tc.extra_cflags/cxxflags`（仅影响本包工具链，不动上游源码、不动 igraph 配方）；缺键时警告跳过 |

## 依赖版本

- igraph/1.0.0（仓内已归档 `archives/i/igraph/1.0.0`，CMakeDeps 提供 `igraph::igraph`）

## 验证结果

```bash
# 本轮为未提交工作树，真机预检由 HMBS 在本轮结束后同步执行
# 预期真机输出：
# HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"...test_leidenalg","discovered":6,"passedCount":6}
# HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"...audit...","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,...}
```

## 注意事项

- 本轮严禁 commit/push/建 PR；工作树保持未提交，等待 HMBS 真机全部门禁。
- PR 正文测试数字留待真机 evidence 轮回填，本轮不估算。
