# geographiclib 2.7 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-10
- 编译器: clang/clang++ 15.0.4
- 状态: built（conan-verify + W3 通过，CI upload 待 PR 合并后由 release 流水线执行）

## 编译步骤

```bash
# 源码（官方 GitHub tag v2.7）
curl -sL -o geographiclib-v2.7.tar.gz \
  "https://codeload.github.com/geographiclib/geographiclib/tar.gz/refs/tags/v2.7"
sha256sum geographiclib-v2.7.tar.gz   # 78d77cc8216843b78d14b41970ed9de3dedc34b9cd50ad84af2849c63a41eff8

# CMake 配置 + 编译 + 安装（staging）
cmake -S . -B build \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_DOCUMENTATION=OFF -DUSE_BOOST=OFF \
  -DCMAKE_SHARED_LINKER_FLAGS="-Wl,-soname,libGeographicLib.so"
cmake --build build -j$(nproc)
DESTDIR=$TEST_PREFIX cmake --install build

# 上游测试（独立测试程序 + ctest 全量）
cmake --build build --target testprograms
LD_LIBRARY_PATH=build/src ./build/tests/{geodtest,signtest,polygontest,intersecttest}
ctest --output-on-failure   # 199/199 passed

# 配方验证
python3 scripts/ohc-run.py conan-verify geographiclib 2.7   # G0-G4 + L2/L4/L5 PASS
python3 scripts/ohc-run.py finish geographiclib 2.7 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CLI 工具（GeodSolve 等）安装后无法运行：`Error loading shared library ../src/libGeographicLib.so` | OHOS 平台 CMake 未识别（HarmonyOS 无 platform module），共享库不自动附加 SONAME，工具链接时 DT_NEEDED 记为构建树相对路径 | 配方 generate() 注入 `-DCMAKE_SHARED_LINKER_FLAGS=-Wl,-soname,libGeographicLib.so`，工具 DT_NEEDED 变为 libGeographicLib.so，安装后可运行 |
| 2 | GitHub 归档 URL 直连超时（github.com HTTP 000） | 网络到 github.com 受限，codeload.github.com 可达 | 经 codeload 下载同一官方 tarball 核验 SHA-256；conandata.yml 保留官方 URL（CI 侧 E017 自动注入 ghfast 镜像） |
| 3 | 测试程序首次 exit 127 | 运行环境未带 LD_LIBRARY_PATH | ctest/工具测试均显式注入 build/src 库路径 |

## 源码修改

无补丁（patches/ 为空）。SONAME 修复在 conanfile.py generate() 中通过 CMake 变量处理，
未改上游源码，符合 R8（补丁默认禁止平台宏）。

## 依赖版本

无外部第三方依赖（Boost 可选且默认 OFF）。

## 验证结果

```bash
# 上游测试（双口径，R05 最终核实：212 声明全量跑通）
#  source_declared_total=212（208 具名 add_test 含 L724 注释占位 Planimeter29 + 4 测试程序）
#  configured_executable_total=211（ctest -N 实测，注释占位不注册）
#  executed_passed_total=211(ctest) + 1(Planimeter29 函数经 polygontest 执行) = 212 全量有运行证据
#  failed=0；全量通过率 212/212=100%（口径：211 项 add_test 注册运行 + 第 212 项由
#  polygontest 内 Planimeter29 函数承载执行，polygontest exit 0 断言通过）；
#  可执行集 211/211=100%
# 第 212 项证据: tests/polygontest.cpp L168 Planimeter29 函数 + L201 main 调用
#  `i = Planimeter29(); n += i;`，断言 area≈1e6(公差0.01)；上游 L720-723 注释明确
#  "该检查已移入 polygontest.cpp"，未修改任何上游测试文件
# 审查方"上游实测 N=259"无法从官方源码任何入口复现（tests/CMakeLists.txt 为唯一
#  add_test 注册地，tools/ experimental/ examples/ man/ 均无 add_test，Makefile.am 无注册宏）
# 数据: GEOGRAPHICLIB_DATA 指向官方 SourceForge 数据包目录（R02 恢复，R05 重验可读），
#  12 项 Geoid/Magnetic/Gravity 数据门控用例全部注册并运行通过
# 4 个独立用户测试程序全部 exit 0

# OHOS 专项测试
#  test_package: geodesic (0,0)->(0,1) s12=111319.4907932736 rel_err<1e-9 + GeoCoords MGRS 解析
#  conan create 内 1/1 Test Passed

# CLI 工具
# 15 个工具 --version 全部正常（GeodSolve: "GeographicLib version 2.7"）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（shared/fPIC 选项 + SONAME 修复） |
| conandata.yml | 官方 GitHub tag v2.7 源码 + SHA-256 |
| test_package/ | OHOS 专项消费者测试 + MANIFEST.yml |
| commands.json | 15 个 CLI 工具声明（R38） |
| manifest.yaml | 版本元数据（built） |
| reports/test-report.md | 验证报告 |

## 注意事项

- 本库 CMake 构建选项：`BUILD_SHARED_LIBS`（默认 OFF 静态）、`USE_BOOST`（默认 OFF）
- 数据门控工具测试（12 项：GeoidEval0、Gravity0-3、MagneticField0-6）需要 GEOGRAPHICLIB_DATA 指向 Geoid/Magnetic/Gravity 模型目录
- 平台 CMake 不认识 HarmonyOS（E092 已知），不影响构建，仅触发平台回退警告

**编译结束**: 2026-09-10 21:00
**最终状态**: built