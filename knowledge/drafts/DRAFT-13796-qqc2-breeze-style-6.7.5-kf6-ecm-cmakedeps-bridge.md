# DRAFT-13796 — KF6/ECM 家族 conan 适配的 CMakeDeps 桥接组合

> 草稿状态：pending-editor-review（拟提升编号由主编确认，草稿以 PR 号命名占位）
> 来源：qqc2-breeze-style 6.7.5 适配 PR #13796（j669539，鸡屁股队）——kiconthemes/kirigami/kconfig 6.26.0 先例链

## 错误特征

```
CMake Error at .../ECMConfig.cmake: Could not find ECM ... (ECM_MODULE_PATH not set)
CMake Error: Could NOT find Qt6 (missing: Qt6Core_DIR)          # qtbase cmake_find_mode=none 断链
-- The following required packages were not found: ... (KDE platform check)
sh: cmake: Error relocating cmake: _ZTINSt4__n1: symbol not found   # 沙箱 libc++ 遮蔽
QQmlApplicationEngine: module "org.kde.breeze" is not installed
```

## 触发条件

- 项目：KF6/ECM 家族（qqc2-breeze-style / kirigami / kiconthemes / kconfig 等 KDE 系）
- 构建系统：CMake + ECM（extra-cmake-modules 作为 conan build require）
- 环境：OHOS 交叉构建（OHOS 不在 KDE 平台清单）+ conan CMakeDeps
- 阶段：cmake.configure / host 工具运行（moc/qmlcachegen/ecm_query_qt）/ test() QML 加载

## 根因分析（四个叠加缺口）

1. **CMakeDeps 生成的 ECMConfig.cmake 不传播 ECM_MODULE_PATH**：ECM 自带的
   Config.cmake 会设置该变量指向 modules/find-modules/kde-modules，CMakeDeps 生成
   的替身 Config 不带——ECM 模块查找整体失效。
2. **qtbase `cmake_find_mode=none` 断链**：该配置下 CMakeDeps 不把 qtbase 的
   lib/cmake 加入 CMAKE_PREFIX_PATH，Qt6 系 find_package 全断。
3. **KDE 平台检查拒绝 OHOS**：ECM 平台清单无 OHOS/HarmonyOS，默认报
   platform not supported。
4. **沙箱 libc++ 遮蔽**：构建沙箱 LD_LIBRARY_PATH 携带与 host 工具不兼容的
   libc++_shared.so，遮蔽 /system/lib64 的兼容版——cmake/moc/qmlcachegen 等
   OHOS ELF host 工具加载即 `Error relocating ... _ZTINSt4__n1` exit 127。

## 解决方案（四点组合，conanfile.py）

### 1) toolchain 变量：平台检查跳过 + ECM 三目录

```python
tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
ecm = self.dependencies.build.get("ecm")
if ecm:
    ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
    tc.variables["ECM_MODULE_PATH"] = ";".join([
        os.path.join(ecm_share, "modules"),
        os.path.join(ecm_share, "find-modules"),
        os.path.join(ecm_share, "kde-modules"),
    ])
```

### 2) 手写 conan_cmakedeps_paths.cmake（CMAKE_PREFIX_PATH 桥）

收集全部依赖（含 build）的 lib/cmake、包根、lib、include 与 ECM share 目录，
生成 paths 文件并在 CMakeUserPresets 预加载：

```python
lines = [
    "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
    f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
    f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
    f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
    f'set(CMAKE_MODULE_PATH "{";".join(modules)};${{CMAKE_MODULE_PATH}}")',
]
```

### 3) 运行期环境：/system/lib64 前置 + QML 载荷路径

```python
if str(self.settings.os) in ("OHOS", "HarmonyOS"):
    env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")  # 兼容 libc++ 优先解析
env.define("QT_QPA_PLATFORM", "offscreen")
# 每依赖前置 LD_LIBRARY_PATH/PATH/QT_PLUGIN_PATH/QML2_IMPORT_PATH
```

### 4) QML 模块型包的 package_info

```python
self.cpp_info.set_property("cmake_find_mode", "none")   # 项目自带 Config，防 CMakeDeps 影子
self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
self.runenv_info.prepend_path("QML2_IMPORT_PATH", os.path.join(self.package_folder, "lib", "qml"))
```

## 降级方案（fallback）

- ECM_MODULE_PATH 仍失败：CMakeUserPresets 硬编码绝对路径（应急）；
- 老 ECM 无 KF_IGNORE_PLATFORM_CHECK：patch KDEPlatformCheck.cmake 白名单追加 OHOS；
- 无 /system/lib64：task-local 复制兼容 libc++_shared.so 前置其目录。

## 红线

- 禁止全局污染 LD_LIBRARY_PATH（只前置 /system/lib64，沙箱原序保留在后）；
- CMakeDeps 影子配置会吞掉项目自带 Config——QML 模块型包必须 cmake_find_mode=none；
- ECM 三目录缺一不可（modules/find-modules/kde-modules 各管一类查找模块）。

## 实证

- verify_builds: #13796（CI passed / AI review passed / review_state approved；本机
  conan create 全绿，test_qqc2 消费者测试 27/27 QQC2 控件解析 PASS）
- 先例链：kiconthemes 6.26.0 / kirigami 6.26.0 / kconfig 6.26.0（KF_IGNORE_PLATFORM_CHECK
  + cmake 桥接 + /system/lib64 前置）、gtksourceview5 5.22.0（host 工具 Error relocating
  libc++ 遮蔽先例）

## 与现有知识的关系（查重结论）

- **E487**（Qt6LinguistTools tool_requires + DIR pin）：只覆盖单工具依赖的 DIR 定位，
  未覆盖 ECM_MODULE_PATH 传播缺失与 cmakedeps_paths 桥；
- **E451**（clang cmake_find_mode=none→只用 CMakeToolchain）：方向相反（弃用 CMakeDeps），
  本条是保留 CMakeDeps 并手写桥接文件的补法；
- **E120/E132**（LD_LIBRARY_PATH）：讲链接期/加载路径，本条是沙箱不兼容 libc++ 遮蔽
  兼容版的运行期冲突规避（host 工具 exit 127 场景）；
- KF_IGNORE_PLATFORM_CHECK / ECM_MODULE_PATH / KDE 平台清单：图谱 grep **零命中**。
- draft-review 预审建议：**create（新知）**，实测最高相似分 0.12（E217 头文件安装子目录条目，签名 0.17/关键词 0.0/类别 0.33——均低重叠，KF6/ECM 主题零覆盖）。
