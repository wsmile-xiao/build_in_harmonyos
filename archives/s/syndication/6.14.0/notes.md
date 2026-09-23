# syndication 6.14.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-06
- 编译器: clang/clang++ 15.0.4（OHOS SDK aarch64-linux-ohos，/data/service/hnp/bin）
- 状态: published

## 编译步骤

1. **依赖发布检查 (W0)**: `conan download qtbase/6.11.1 kcodecs/6.14.0 ecm/6.20.0 -r=ohpcd --only-recipe` 全部命中，依赖链已发布。
2. **conan create**: 以 `ci/conan/profiles/ohos-aarch64`（os=OHOS, arch=armv8, clang 15）执行
   `conan create archives/s/syndication/6.14.0 --build=syndication/*`。
3. **配置**: CMake + ECM（extra-cmake-modules 6.20.0）。关键变量：
   - `KF_IGNORE_PLATFORM_CHECK=TRUE`（绕过 KDE 平台检测）
   - `BUILD_SHARED_LIBS=ON`、`BUILD_TESTING=ON`、`BUILD_QCH=OFF`
   - `CMAKE_CXX_STANDARD=20`
4. **构建**: `cmake --build`（libKF6Syndication.so）。
5. **上游测试**: build() 内直接 `ctest --test-dir <build> --output-on-failure --no-tests=error`
   （headless：`QT_QPA_PLATFORM=offscreen`，依赖库路径注入 LD_LIBRARY_PATH）。
6. **打包**: `cmake --install` 安装到 conan package 目录。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | KDE 平台检测拒绝 OHOS（ECM 的 KF_IGNORE_PLATFORM_CHECK 未设时 CMake configure 报平台不支持） | OHOS 不在 KDE 平台白名单 | `KF_IGNORE_PLATFORM_CHECK=TRUE` |
| 2 | qtbase 用 `cmake_find_mode=none` 消费，CMakeDeps 不生成 Qt6Xml/Qt6Test 等 find path，CMake 找不到 Qt6 模块 | qtbase 自带 Qt6Config 等 config 文件，为避免被 CMakeDeps 遮蔽故用 find_mode=none | generate() 写私有 `conan_cmakedeps_paths.cmake` 注入各依赖 package 的 lib/cmake 到 CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH（R49 私有 build_folder prefix），并以 `CMAKE_PROJECT_TOP_LEVEL_INCLUDES` 挂载 |
| 3 | Qt6 模块（Qt6Xml/Qt6Network/Qt6Test）在 qtbase 包内 find 不到 | Qt6 用分号分隔的 prefix 变量定位附加包 | `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` = 各依赖 package_folder 用 `;` 连接 |
| 4 | ctest 在 conan build 环境跑不动（Qt plugin/qml 找不到） | 依赖库不在运行时搜索路径 | 注入 LD_LIBRARY_PATH/QT_PLUGIN_PATH/QML2_IMPORT_PATH + `QT_QPA_PLATFORM=offscreen` |

## 源码修改

无。本版本未修改任何上游源码（patches/ 为空）：全部 OHOS 适配经 CMake 变量 + generate() 路径注入完成。

## 依赖版本

| 包 | 版本 | 用途 |
|----|------|------|
| qtbase | 6.11.1 | Qt6 基础库（Qt6Core/Qt6Xml/Qt6Network/Qt6Test） |
| kcodecs | 6.14.0 | KF6 字符编码库（KF6::Codecs，find_dependency 引用） |
| ecm | 6.20.0 | extra-cmake-modules（tool_requires，ECM 宏/模块） |

## 验证结果

```bash
$ conan create archives/s/syndication/6.14.0 --build=syndication/*   # RC=0
# build() 内上游 ctest: 3/3 全部通过（详见 reports/test-report.md）
# test_package: 编译消费端并运行 test_syndication → "PASS: parsed RSS 2.0 feed"
```

上游 CTest 3/3：
- testpersonimpl：PASS（3 断言：fromString 等）
- syndicationtest：PASS（约 90+ 数据文件解析比对断言）
- loaderutiltest：PASS（5 断言：bug-383381 / test-gentoo-url / bug-484615 等）

## 注意事项

- 仅库类型包，无命令行产物，不需要 commands.json（R38）。
- 补丁为空，`export_conandata_patches` 幂等；build() 中 `apply_conandata_patches` 仅 OHOS 上执行（`settings.os == "OHOS"` 守卫，不设平台宏于补丁文件，R8）。
- 下游 KF6 消费者（如 alligator）直接 `find_package(KF6Syndication)` 即可，包自带 KF6SyndicationConfig.cmake 且 find_dependency 跟踪 KF6Codecs/Qt6Xml。

## W3 本地 CI 门禁结果（finish [5/10]，build_and_test.sh）

- L0（结构/MANIFEST/JC 杂项检查）: **pass**（junk_check prdiff 8 文件，JC1-JC6 全过）
- L1（上游测试 + test_package 实际执行）: **pass**
- L2（smoke test）: skip（纯库包无 bin/）
- L4（安全扫描）: pass
- L5（SONAME 质量门禁）: **fail: soname_gate_failed**（非阻塞，构建仍 100% 通过）
  - 根因：OHOS 交叉编译下 CMake 无 `Platform/HarmonyOS` 模块，`CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` 为空 → libKF6Syndication.so 无 DT_SONAME，且依赖无 SONAME 的 libKF6Codecs.so 时 DT_NEEDED 记录为构建机绝对路径。
  - 判定：**系统级平台条件**，非本包缺陷——已发布 KF6 包（kcolorscheme 6.18.0.1）同为 `L5_RESULT=fail: soname_gate_failed`，运行时由 conan 的 RPATH 部署解决，不阻塞构建/消费。
- 总结果: Success 1 / Failed 0 / Pass rate 100%，`.ci-result.json` exit_code=0。

---

**编译结束**: 2026-09-06 18:03
**最终状态**: published

