# CMakeDeps 对传递依赖序列化空 includedirs：在 package_info 显式传播

> 状态：本地路径 B 草稿，需人工审核后才可提升为正式知识条目。

## 现象

包装包 B（依赖 A）自身 conan create 构建成功，但它的 test_package 编译时在
#include 一个 A 的头文件处报 fatal error: file not found；此时 conan graph 完整、
find_package(B CONFIG REQUIRED) 成功、CMake 目标链 B::B -> B_DEPS_TARGET -> A::A
全部存在。

## 根因（implot 0.8 × imgui 1.92.2b 实测）

本仓 OHOS conan 2.29.1 的 CMakeDeps 生成器：

- 直接依赖：数据文件 INCLUDE_DIRS_RELEASE 填充 ${PACKAGE_FOLDER}/include；
- 传递依赖：同变量序列化为空（LIB_DIRS_RELEASE 仍填充 /lib）。

于是消费者通过 implot::implot 编译时拿不到 imgui 头文件路径，而链接期
INTERFACE_LINK_LIBRARIES imgui::imgui 是好的，错误被推迟到编译阶段，难排查。

诊断命令（无需跑完整 create）：

    conan install --requires=implot/0.8 -g CMakeDeps
    grep INCLUDE_DIRS imgui-release-*.cmake   # 传递：空；直接：/include

## 推荐方案

包装包 package_info() 显式传播依赖 include 目录，同时保留 cpp_info.requires
做链接传播：

    def package_info(self):
        self.cpp_info.libs = ["implot"]
        self.cpp_info.requires = ["imgui::imgui"]
        imgui_dep = self.dependencies["imgui"]
        self.cpp_info.includedirs.extend(imgui_dep.cpp_info.includedirs)

替代方案（仅测试包可接受）：test_package conanfile 额外直接 requires 该依赖，
使它变成直接依赖；缺点是把依赖版本泄漏进测试包。

## 禁止策略

- 禁止把依赖头文件拷进自己的包（双份维护、版本漂移）。
- 禁止硬编码 /storage/.../p/<hash>/include 之类缓存路径。
- 禁止用 CPATH/LD_LIBRARY_PATH 全局注入绕过。

## 适用边界

- 适用于本工具链（conan 2.29.1）上所有多级 CMakeDeps 依赖图；上游修复该序列化
  行为后应回归验证并解除本方案。
- 仅 CMakeDeps 受影响；Autotools/Meson 的 pkg-config 传播走另一条链。

## 与现有知识库的关系

- E216（CMakeDeps GLOB 分号回退）、E217（install 子目录头文件）、E221（cpp_info
  公共契约）、E321（header-only Conan2 迁移）均未覆盖"传递依赖 includedirs 空、
  直接依赖正常"这一不对称行为，查重未命中。
