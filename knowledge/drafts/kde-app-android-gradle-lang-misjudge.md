# lang-preflight 按 gradle 文件名误判 KDE/Qt 应用为 java

> Draft: `DRAFT-KDE-APP-ANDROID-GRADLE-LANG-MISJUDGE`
> Stem: `kde-app-android-gradle-lang-misjudge` — pairs with the same-stem `.kv`

## 错误特征

`lang-preflight`（R47）输出终态 `env_unsupported`，判定依据是
`detected_language: mixed`，且详情里 language 统计为 java + cpp：

```
[fail] lang-preflight: detected_language=mixed (java/cpp)
-> 终态 env_unsupported (java 工具链不在支持矩阵)
```

而该包（kirigami-gallery 26.04.0，KDE Release Service 应用）实际是
**纯 C++17 + QML** 项目，构建系统为根级 `CMakeLists.txt`
（`cmake_minimum_required(3.16)` + `project(kirigami2gallery)`），
`conan create` 在 C++ 工具链下全绿通过。

## 根因

`lang_detect.py` 的 `_manifest_scan` 按**文件名**递归匹配构建系统标志文件，
且 gradle 判定优先于 CMake。KDE Release Service 与 KDE/Qt 生态的 GUI 应用
源码包里普遍携带 `src/android/build.gradle`——这是 **ECM 的
`ecm_add_android_apk()` 使用的 APK 打包辅助文件**（Qt for Android 产物，
`if(ANDROID)` 分支独占，桌面/通用平台路径完全不引用它）。
它不是项目的构建系统，但命中了 java/gradle 的 manifest 文件名规则，
于是与真实构建系统（根级 CMakeLists.txt）的 cpp 统计并存 → `mixed` →
被当成了 java 项目 → 终态 `env_unsupported`。

## 影响范围

- 所有携带 `src/android/build.gradle` 的 KDE Release Service 应用
  （26.04 滚动发布源码包普遍包含该文件）。
- 任何"以文件名扫描为准"的语言预检逻辑遇到**辅助性构建文件**的场景。
- 后果形态：AI 被误导终止适配（env_unsupported），或为迎合检测器
  删除/改名源码文件——后者会伪造证据，违反 R8/R10 口径。

## 推荐方案

**方法**: `evidence-over-detector-snapshot`

1. **复核证据链**：读根级构建定义（CMakeLists.txt/meson.build/configure.ac），
   统计源码主体语言（`find` + 按扩展名分类，辅助脚本不算主体）；
   确认 `build.gradle` 所在目录是否为 android/ 打包辅助目录、
   是否被 `if(ANDROID)` 守卫。
2. **不要修改源码迎合检测器**：删除 build.gradle 或加注释骗过文件名扫描
   都属于伪造证据；预检误判按本条模式记录即可。
3. **notes.md 如实记录**误判分析（工具行为、目录语义、证据链），
   任务照常按真实语言（C++）继续。
4. **终态上报用真实状态**：`result` 报真实结果（必要时 `--force` 覆盖
   误判阶段写入的占位终态），终态与 conan-verify/本地 CI 证据一致。

## 验证命令

```bash
# 1) 真实构建系统与语言主体
head -5 <src>/CMakeLists.txt                      # cmake_minimum_required + project(...)
find <src> -maxdepth 2 -name "build.gradle"       # 定位 android 辅助目录
grep -rn "android" <src>/CMakeLists.txt | head    # ecm_add_android_apk 是否被 if(ANDROID) 守卫

# 2) 语言主体统计（辅助脚本不算主体）
find <src> -name "*.cpp" -o -name "*.qml" | wc -l
find <src> -name "*.java" | wc -l                 # 0

# 3) C++ 工具链全绿即证伪 java 判定
conan create <archive_dir> -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

## 取证记录

- 包: kirigami-gallery 26.04.0（`archives/k/kirigami-gallery/26.04.0`）
- 逐字证据: `notes.md` §3（lang-preflight 误判记录）、
  `reports/conan-verify-report.md`（G2 PASS，C++ 工具链全绿）
