# ksanecore 26.04.0 适配笔记

## 编译环境
- 构建系统: cmake（KDE ECM 工程）
- 编译日期: 2026-09-20
- 编译器: clang/clang++ 15.0.4（OHOS SDK）
- 状态: built（conan-verify G0-G4 全通过）

## 编译步骤

```bash
conan create archives/k/ksanecore/26.04.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

配方关键点：
- `KF_IGNORE_PLATFORM_CHECK=TRUE`：绕过 KDE 平台白名单（OHOS 不在列表）
- `KF_SKIP_PO_PROCESSING=ON`：跳过翻译目录生成
- `BUILD_TESTING=ON`：启用 CTest（上游 autotests 仅定义宏、未注册用例，0 用例）
- 依赖注入：qtbase/6.11.1 + ki18n/6.26.0 + sane-backends/1.2.1 + tool_requires ecm/6.26.0
- `conan_cmakedeps_paths.cmake`：qtbase 使用 cmake_find_mode=none，需手动把依赖 lib/cmake 加入 CMAKE_PREFIX_PATH

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G2 conan create 失败：qtpaths 运行报 libc++_shared.so 加载错误 | ECM KDEInstallDirs 在 configure 期运行 qtbase 的 qtpaths 宿主工具，沙箱 LD_LIBRARY_PATH 中不兼容的 libc++_shared.so 遮蔽了兼容版本 | `_cmake_build_env()` 与测试环境 prepend `LD_LIBRARY_PATH=/system/lib64`（kconfig/kcrash/kio 6.26.0 先例） |
| 2 | test_package find_dependency(Qt6Gui) 找不到 Qt6GuiConfig.cmake | KSaneCore6Config.cmake 链式 find_dependency(Qt6Gui)，而 qtbase cmake_find_mode=none 导致 CMakeDeps 不注入其 lib/cmake | test_package generate() 生成 conan_cmakedeps_paths.cmake，遍历依赖注入 CMAKE_PREFIX_PATH/LIBRARY_PATH/INCLUDE_PATH（kxmlgui 6.18.0 先例） |
| 3 | test_package 链接目标 KSane::Core 找不到 | 上游 install(EXPORT) NAMESPACE 为 `KSane6::`，导出目标名是 `KSane6::Core` | 修正 CMakeLists.txt 链接 `KSane6::Core` |
| 4 | test_package 运行期 libc++_shared.so 加载失败 | 同问题 1，test() 阶段沙箱 libc++ 遮蔽 | test() 中 prepend /system/lib64 与 SDK llvm/lib（kcrash 6.26.0 先例） |
| 5 | 自研断言 `state()==StateHidden` 失败 | 默认构造 Option 无底层后端，源码 option.cpp:29 返回 `StateDisabled` | 按源码实际返回值修正断言为 StateDisabled |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`：顶层依赖段 stamp `KF6::I18n` 的 `IMPORTED_SONAME=libKF6I18n.so` 并清除 `IMPORTED_NO_SONAME`/`IMPORTED_NO_SONAME_RELEASE`（E537 relocatable linkage，kpackage 6.26.0 先例）
- `patches/0002-src-CMakeLists.txt.patch`：`src/CMakeLists.txt` 用 `target_link_directories(... PRIVATE ${KSANECORE_DEP_LIB_DIRS})` + 裸 `-lKF6I18n` 链接（替代 `KF6::I18n` target），并保留 KF6::I18n 的 include 目录为 SYSTEM PRIVATE（kpackage 6.26.0 0005 先例）

根因：ki18n 6.26.0 产物无 DT_SONAME，若按 IMPORTED_LOCATION 绝对路径链接，ld 会把 Conan cache 绝对路径写入 DT_NEEDED（不可迁移）；修复后 ld 记录 `libKF6I18n.so` basename。

## 依赖版本

- qtbase/6.11.1（Qt6 Core/Gui）
- ki18n/6.26.0（KF6I18n）
- sane-backends/1.2.1（Sane API）
- ecm/6.26.0（构建期 ECM，制品仓无 6.29.0 故采用已发布版本）

## 验证结果

```bash
# conan-verify（ohc-run.py）：G0-G4 全部 PASS
# 上游测试：autotests/CMakeLists.txt 仅定义 ksane_tests() 宏、未注册任何用例 → 0 用例
# 自研 test_package：18 断言全部通过（Option/DeviceInformation 公共 API，无需真实扫描硬件）
./test_ksanecore  # ALL TESTS PASSED
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方 |
| conandata.yml | 源码 URL + sha256（35091dc0...c3421a） |
| manifest.yaml | 版本级 manifest |
| test_package/ | 消费者测试（CMakeLists.txt + test.cpp + conanfile.py + MANIFEST.yml） |

## 注意事项

- ksanecore 是 skanlite 的传递依赖（skanlite → libksane → ksanecore），本包为最底层
- 制品仓无 ecm/6.29.0，采用 ecm/6.26.0（与其他 KF6 包一致）
- KSaneCore6Config.cmake 自带上游安装的 find_dependency 链，package_info 用 cmake_find_mode=none 避免 CMakeDeps 遮蔽
## 对话记录

### 对话 #1（2026-09-20）

- 任务：适配 ksanecore 26.04.0 至 HarmonyOS PC (arm64)（skanlite 传递依赖链 ksanecore → libksane → skanlite）
- W0/W1：上游 26.04.0 存在，依赖树（qtbase/ki18n/sane-backends/ecm）全部已发布；ksanecore/libksane 为未发布阻塞依赖，本包为最底层
- 编译：conan create 干净构建成功（G0-G4 全 PASS）；L5 soname 门禁 3 项问题全部修复（CMAKE_SHARED_LIBRARY_SONAME flag + E537 双补丁）
- 测试：上游 autotests 无注册用例（0）；自研 test_package 18 断言全通过
- 知识：E537（Conan cache 绝对 DT_NEEDED 泄漏→relocatable SONAME 链接修复）为完全复用；无新增草稿
---

**编译结束**: 2026-09-20 10:03
**最终状态**: built
