# pokerstove 1.1 适配笔记

## 编译环境
- 构建系统: cmake (≥3.0 要求，本机 cmake 4.1.2 需 CMAKE_POLICY_VERSION_MINIMUM=3.5)
- 编译日期: 2026-09-03
- 编译器: clang/clang++ 15.0.4 (OHOS 原生工具链 /data/service/hnp/bin/clang)
- 状态: built（conan-verify 8 道门禁全过，CI upload 待 PR 合并后）

## 编译步骤

探索阶段（conan CMakeToolchain 方式，R1 参数最少化）：

```bash
# 1) conan 安装依赖生成工具链（绝对路径 profile，避免 conan cache 旧同名 profile 干扰）
conan install --requires=boost/1.84.0 -g CMakeToolchain -g CMakeDeps \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

# 2) 配置（CMAKE_POLICY_VERSION_MINIMUM=3.5 是必须的：根 CMakeLists 要求 cmake 3.0，
#    cmake 4.x 已移除 <3.5 兼容）
cmake -S $BUILD_SRC_DIR -B build \
  -DCMAKE_TOOLCHAIN_FILE=$PWD/conan_toolchain.cmake \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_BUILD_TYPE=Release

# 3) 构建
cmake --build build -j4
```

产物：libpeval.a、libpenum.a（静态库）+ ps-eval/ps-colex/ps-lut（CLI 工具）+ googletest 1.14.0（捆绑）测试程序。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | boost/core/detail/sp_thread_sleep.hpp: `use of undeclared identifier 'pthread_setcancelstate'`（E127 命中） | OHOS musl libc 不提供 pthread_setcancelstate（同 Android）；conan boost/1.84.0 包把 BOOST_SP_NO_PTHREAD_SETCANCELSTATE 宏挂在 boost_headers 组件 defines 上，只有链接 Boost 目标的程序能继承，pokerstove 的 peval/penum 库源码只 include boost 头不链接 Boost | 根 CMakeLists.txt 增加 HarmonyOS 守卫的全局 define（见"源码修改"） |
| 2 | cmake 4.1.2 配置报错 `Compatibility with CMake < 3.5 has been removed`（根/子 CMakeLists 均要求 3.0） | cmake 4.x 移除 <3.5 兼容 | 配置时传 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（配方内用 CMakeToolchain cache_variables 固化，不改上游 cmake_minimum_required） |
| 3 | conan create 主包成功但 test_package 编译报 `boost/operators.hpp file not found`（新知识，草稿 DRAFT-conan2-cmakedeps-transitive-include-strip） | Conan 2 CMakeDeps 只对消费者直接 requires 的包生成含 include dirs 的完整配置；经 pokerstove 传递引入的 boost 在 test_package 端 `boost_Boost_headers_INCLUDE_DIRS_RELEASE` 为空（主包构建有 toolchain CMAKE_INCLUDE_PATH 兜底故不报错，形成"主包过/测试挂"隐蔽差异；requires visible=True 实测无效） | test_package/conanfile.py 的 requirements() 显式声明 `self.requires("boost/1.84.0")`（CCI 生态消费带 boost 公共头库的常规做法） |
| 4 | 首次 conan create 报 package() `TypeError: unsupported operand type(s) for /: 'str' and 'str'` | conan 2 的 self.source_folder/self.package_folder 是 str 不是 Path | package() 内用 `Path(self.source_folder) / ...` 包装 |
| 5 | 打包后发现 include/ 下混入 gtest/gmock 头文件+静态库 | 上游捆绑 googletest 的 INSTALL_GTEST 默认 ON，其 install 规则随 cmake.install() 装进包 | CMakeToolchain 注入 `INSTALL_GTEST=OFF`（上游官方选项，注释明确建议嵌入项目关闭） |

## 源码修改

**CMakeLists.txt**（根）：project() 之后新增平台守卫 define（refresh-patch --auto 固化为补丁）：

```cmake
# OHOS (HarmonyOS) musl libc does not provide pthread_setcancelstate.
# Boost 1.84 headers (boost/core/detail/sp_thread_sleep.hpp, pulled in by
# smart_ptr) need this feature-detection macro to skip that code path.
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    add_definitions(-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE)
endif()
```

## 依赖版本

- boost/1.84.0（ohpcd 已发布，含 program_options 组件，shared；仅需 program_options 头与库）
- zlib/1.3.1（boost 的传递依赖）
- googletest 1.14.0：源码捆绑（src/ext/googletest），无需外部依赖，OHOS clang 15 编译通过
- pthread（OHOS 提供）

## 验证结果

```bash
$ cd build && ctest --output-on-failure
1/3 Test #1: TestPeval  ....   Passed    0.04 sec   # googletest 捆绑套件（8 个 test 文件）
2/3 Test #2: TestPenum  ....   Passed    0.13 sec
3/3 Test #3: TestUtil   ....   Passed    0.03 sec
100% tests passed, 0 tests failed out of 3

$ source ../conanrun.sh && ./bin/ps-eval --game h AcAs Kh4d --board 5c8s9h
The hand AcAs has 97.6768 % equity (959 8 0 0)    # 97.68% + 8 平分池，枚举全部剩余牌
The hand Kh4d has 2.32323 % equity (15 8 0 0)

$ ./bin/ps-eval AcAs
The hand AcAs has 85.2037 % equity (1781508418 5701156 0 0)  # AA vs random=85.2%，与官方文档经典值一致
A random hand has 14.7963 % equity (304661670 5701156 0 0)
# 注：单手全枚举 1.78B 次评估，本机耗时约 110s；test_package 用带 board 的快速用例

$ ./bin/ps-colex AcAs Kh4d
2c3c: 0
2c4c: 1
...   # 输出起手牌 colex 索引，正常
```

产物：bin/{ps-eval,ps-colex,ps-lut,peval_tests,penum_tests,util_tests}、lib/{libpeval.a,libpenum.a,libgtest*.a,libgmock*.a}

## 注意事项

- conan cache 中存在旧版 `ci/conan/profiles/ohos-aarch64` 同名 profile（gnu14/libstdc++11/无 os.version，2026-08-25 残留），按名字解析会命中旧版；必须用绝对路径或从仓库根目录调用（ohc 工具内部用绝对路径，不受影响）
- 源码 URL 直连 GitHub 超时（网络封锁），用 ghfast.top 镜像前缀下载；conandata.yml 仍写官方 URL（R39）
- pokerstove 上游 CMakeLists 硬编码 `-std=c++14`，与 profile 的 cppstd=17 共存时 -std=c++14 在后生效，clang 15 无兼容问题
- install(TARGETS ...) 无 DESTINATION，走默认 bin/lib；头文件上游不安装，配方 package() 需手动拷贝 src/lib/pokerstove → include/pokerstove
- finish 的 G0 clean-build-verify 子步骤报 configure exit 127：该子检查只支持 autotools（硬编码 ./configure + make），对 cmake 项目不适用；真实干净构建验证由 conan-verify G2（tarball 解压 + apply 补丁 + conan create 全流程）覆盖，G2 PASS
- finish 的 E017 镜像注入/恢复逻辑有 bug：注入时把 conandata.yml 的 url 改写为镜像列表，"恢复"后未还原为单官方 URL（曾出现 gh-proxy.com 残留），需人工 `git checkout` 恢复并核实（PR6091 教训同源）
---

**编译结束**: 2026-09-03 12:51
**最终状态**: built
**conan-verify**: 8 道门禁全部通过（G1 配方完整性 / G0 预构建风险 / G2 conan create 干净构建含三层 test_package / G3 系统同名库 / G4 产物完整性 L2/L4/L5）——2026-09-03 12:38，报告 reports/conan-verify-report.md
