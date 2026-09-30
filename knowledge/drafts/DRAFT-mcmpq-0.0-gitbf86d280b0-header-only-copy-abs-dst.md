# DRAFT — header-only 库 package() 中 copy() 的相对 dst 落到 build 目录，test_package 报 include 不存在（mcmpq 0.0-gitbf86d280b0）

**来源事件:** mcmpq 0.0-gitbf86d280b0 适配（pc7-44, 2026-09-28）
**状态:** 草稿（待 promote 审核）
**对应 .kv:** `DRAFT-mcmpq-0.0-gitbf86d280b0-header-only-copy-abs-dst.kv`

## 问题

header-only Conan 2 配方在 `package()` 中用 `conan.tools.files.copy()` 复制头文件时，
若 dst 使用相对路径（如 `dst="include"`），产物会落到 **build 目录**（`build-release/include`）
而非 **package 目录**（`p/include`），导致 test_package 消费者 CMake 报：

```
CMake Error in CMakeLists.txt:
  Imported target "mcmpq::mcmpq" includes non-existent path
  "/storage/.../.conan2/p/b/mcmpqXXX/p/include"
  in its INTERFACE_INCLUDE_DIRECTORIES.
```

conan create 的 test_package 阶段失败（`cmake.configure()` Error 1），
但上游库本身编译没有任何问题——错误只在消费者侧暴露。

## 根因

Conan 2 的 `conan.tools.files.copy()` 在 `package()` 阶段执行时，相对 dst
基于**当前工作目录（build 目录）**解析，而不是 package 目录。于是头文件被复制到
`<build_folder>/include`，而 `cpp_info.includedirs` 默认指向 `<package_folder>/include`
（实际不存在），CMakeDeps 生成的 Imported target 就引用了不存在的路径。

## 方案（已验证）

`package()` 中所有 copy() 的 dst 显式使用绝对路径：

```python
import os
from conan.tools.files import copy

def package(self):
    copy(self, "mcmpq.h", src=self.source_folder,
         dst=os.path.join(self.package_folder, "include"))
    copy(self, "LICENSE*", src=self.source_folder,
         dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
```

修复后 conan create + test_package 消费者编译、链接、运行全部通过（100% passed）。

## 与既有知识的关系

- `similar_to: [E498]` — E498 是 headerless 库（故意不装公开头文件）需清空
  `cpp_info.includedirs` 以消除同一 CMake 症状（`Imported target ... non-existent path`）；
  本候选是 header-only 库**装了头文件但落错目录**，根因是 copy() 相对 dst 解析，
  方案是绝对 dst 实装头文件，二者根因与方案均不同，仅症状重叠。
- 边界反例: E498 的"清空 includedirs"方案对本候选不适用——mcmpq 有真实公开头文件 API，
  清空 metadata 会让下游丢失 include 路径；本候选的"绝对 dst"方案对 E498 的 headerless
  场景无意义（无头文件可复制）。

## 适用范围

所有在 `package()` 中用 `conan.tools.files.copy()` 复制头文件/资源的 header-only
或数据型 Conan 2 配方；对任何库类型（header-only / 普通库安装头文件）都适用。
