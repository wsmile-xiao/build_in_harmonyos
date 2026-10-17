# DRAFT-libayatana-cpp-info-requires-implicit-component — 无显式 components 的依赖包在 cpp_info.requires 中须用「包名::包名」引用

> **Contributor**: OHC-Agent | **Status**: DRAFT | **Updated**: 2026-09-18
> **Severity**: 🟡 medium | **Category**: conan / packaging / cmake / recipe

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条目增量（差异化） |
|---------|---------|--------|----------------------|
| **E499** | 正式 | cpp_info.requires 只能引用**直接依赖**的组件（引用间接依赖报 not a direct requirement） | 非本题——那是**依赖层级**限制；本条是**组件命名语法**（无 components 包的正确引用形式） |
| **DRAFT-cpp-rotor-0.35...** | 草稿 | Boost 裁剪版配方**缺失某些组件** → 换完整版 | 非本题——那是**组件确实不存在**需换包；本条是**组件存在（隐式）但引用名写错** |

## Scope（何时用）

写 conanfile.py 的 `package_info()`，且依赖图中存在**未定义 `cpp_info.components`** 的包（只有顶层 cpp_info，如 ayatana-ido 的 `cmake_target_name=/cmake_file_name=/pkg_config_name=` 属性，无 components 声明）时，在 `self.cpp_info.requires` 中引用该包：

- 错误写法 1：`"ayatana-ido::ayatana-ido3-0.4"`（用依赖的 **CMake target 名**冒充组件名）
- 错误写法 2：`"ayatana-ido"`（裸包名，被解析为**当前包内部组件**）

## Symptom

```text
ERROR: Component 'ayatana-ido::ayatana-ido3-0.4' not found in 'ayatana-ido' package requirement
ERROR: package_info(): There are '(cpp_info/components).requires' to other internal components that are not defined: ['ayatana-ido']
```

第一条在 test_package 的 CMakeDeps generate 阶段报；第二条在 package_info() 校验阶段报。

## Root Cause

Conan 2 中 `cpp_info.requires` 条目指向依赖包的 **Conan 组件**（`cpp_info.components` 的 key）。对未显式声明 components 的包，Conan 为其生成**隐式组件 = 包名**。三条规则：

1. 组件名 ≠ CMake target 名：ayatana-ido 的 `cmake_target_name` 是 `ayatana-ido3::ayatana-ido3-0.4`（CMake 命名空间），不是 Conan 组件名；
2. 裸包名在 cpp_info.requires 中按**当前包内部组件**解析；
3. 隐式组件名 = 包名本身（`ayatana-ido::ayatana-ido`）。

## Solution

```python
def package_info(self):
    ...
    self.cpp_info.requires = [
        "glib::glib-2.0", "glib::gmodule-2.0", "glib::gio-2.0",  # 有显式 components → 组件名
        "gtk::gtk",                                              # 有显式 components → 组件名
        "ayatana-ido::ayatana-ido",                              # 无显式 components → 包名::包名
    ]
```

## Verification

- 复现：conan-verify G2 在 test_package CMakeDeps 阶段报 `Component 'ayatana-ido::ayatana-ido3-0.4' not found`
- 修复后：conan-verify 全门禁 PASS（G0-G4 + L2/L4/L5），test_package 编译链接运行均成功

## 适用/不适用边界

- **适用**：Conan 2 配方 package_info 引用无显式 components 的单组件依赖包
- **不适用**：引用有显式 components 的包（用「包名::组件名」）；需要跳过 cpp_info.requires 的场景（用 fallback：仅 requirements() 声明）