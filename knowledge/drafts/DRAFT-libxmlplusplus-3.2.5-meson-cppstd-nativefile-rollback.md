# DRAFT — MesonToolchain 用 profile 的 cppstd=17 覆盖项目 meson.build 声明默认（c++11），需 tc.cpp_std 显式回退

- 触发实例：libxmlplusplus 3.2.5（libxml++ 3.x 线，Meson 构建）第一轮适配
- 状态：草稿（路径 B 知识库扩展，随 libxmlplusplus 3.2.5 PR 交付）

## 问题

上游 libxml++ 3.2.5 的 meson.build 声明：

```meson
project('libxml++', 'cpp',
  version: '3.2.5',
  default_options: [
    'cpp_std=c++11',
    ...
  ],
)
```

但 OHOS 共享 profile `compiler.cppstd=17` 使 Conan `MesonToolchain` 生成的
`conan_meson_native.ini` 在 `[built-in options]` 写入 `cpp_std='c++17'`。
native file 的 built-in options 优先级高于 meson.build 的 default_options，
项目声明的 C++11 被静默覆盖为 C++17。

对 C++11 时代代码（如 libxml++ 2.x 头文件使用 `std::auto_ptr`，C++17 已移除）
直接编译失败；即使能编译（3.x 无 auto_ptr），编译标准也与项目声明不一致，
属于隐性偏差。共享 profile 不能为单库修改（影响全局）。

## 根因

`MesonToolchain` 的 cpp_std 取自 `settings.compiler.cppstd`（共享 profile = 17），
写入 native file `[built-in options]`，优先级高于 `meson.build` 的 `default_options`。

## 方案

在 `generate()` 中创建 MesonToolchain 后显式回退：

```python
tc = MesonToolchain(self)
tc.cpp_std = "c++11"   # 与上游 meson.build 声明一致，覆盖 profile cppstd=17
tc.generate()
```

该通道仅影响 MesonToolchain（native file built-in options）；
AutotoolsToolchain / CMakeToolchain 无此覆盖行为，无需处理。

## 验证

- libxmlplusplus 3.2.5 `conan create`（G2）PASS：meson setup 按 c++11 配置并编译通过。
- conan-verify G0-G4 + L2/L4/L5 全 PASS。
- 与既有参考配方一致：libxmlpp 2.42.3、glibmm/2.66.9 同款 `tc.cpp_std` 回退。

## 适用边界 / 反例

- 适用：MesonToolchain 且上游 meson.build 显式声明较低 cpp_std 的项目。
- 不适用：上游未声明 cpp_std，或声明 c++17 及以上（profile 17 无覆盖差异）；
  autotools/cmake 构建（无 native file built-in options 覆盖）。

## 查重

- exact_duplicate=false；与 E293（旧 C++ 代码 cppstd=17 编译错误，走 toolchain-flag
  标志通道）、E130（把 c++11 改 c++17，方向相反）、E538 draft（pangomm cxx17 profile，
  主题为 shared/options 冲突与包 ID）均为部分重叠，机制（native file built-in options
  覆盖）无既有条目。
- similar_to=E293, E130, E538；caused_by=无；prerequisite_of=无；conflicts_with=无。
