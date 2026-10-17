# DRAFT — 裸 Makefile 库静态归档无 lib 前缀 → CMakeDeps "Library not found in package"（offbrand-lib 1.0.0）

## 问题

纯 Makefile C 库（无 configure、无 install 目标）适配 OHOS 时，conan-verify G2
在 test_package 的 CMake configure 阶段失败：

```
cmakedeps_macros.cmake:81 (message):
  Library 'offbrand' not found in package.  If 'offbrand' is a system
  library, declare it with 'cpp_info.system_libs'
```

## 根因

上游 Makefile 用 `ARFLAGS = rvs` 直接生成静态归档 `bin/offbrand.a` —— **归档名
无 `lib` 前缀**。Conan 2 的 CMakeDeps 生成消费者 target 时按 `lib<name>.a` 约定
在包内 `lib/` 目录查找静态库，找不到 `liboffbrand.a`，`conan_package_library_targets`
即报 "Library not found in package"。即使 `package()` 已用 `keep_path=False`
正确把归档落盘到 `lib/`，只要文件名缺 lib 前缀，CMakeDeps 仍无法解析。

（若 copy pattern 还带了 `bin/` 目录前缀，则落盘成 `lib/bin/offbrand.a`，是
DRAFT-list-0.4.1/E097 已记录的路径嵌套问题；本条目专指**文件名缺 lib 前缀**这一面。）

## 方案

`package()` 中把归档重命名为 `lib<name>.a`（name 与 `cpp_info.libs` 中的库名一致）：

```python
import os
from conan.tools.files import copy

def package(self):
    src = self.source_folder
    pkg_lib = os.path.join(self.package_folder, "lib")
    copy(self, "offbrand.a", os.path.join(src, "bin"), pkg_lib, keep_path=False)
    os.rename(os.path.join(pkg_lib, "offbrand.a"),
              os.path.join(pkg_lib, "liboffbrand.a"))

def package_info(self):
    self.cpp_info.libs = ["offbrand"]
```

要点：
- 头文件复制同样用 `keep_path=False` 精确 join（`src/include` → `pkg/include`、
  `src/include/private` → `pkg/include/private`），避免 `include/include/` 嵌套。
- 改 `cpp_info.libs` 名称**不能**替代文件改名：CMakeDeps 以磁盘文件名为准。

## 验证

- offbrand-lib 1.0.0：修复后 conan-verify 全门禁（G1-G4、L2/L4/L5）PASS；
  `conan create` 干净构建成功，test_package 2/2 测试通过
  （消费者 `test_offbrand-lib` + 鸿蒙专项 `test_ohos`）。
- 修复前后磁盘证据：`find package_folder -name '*.a'` 由
  `lib/offbrand.a` → `lib/liboffbrand.a`。

## 适用边界

- 适用于：无 configure/无 install 目标、构建产物为无 lib 前缀 `.a` 的裸 Makefile C 库。
- 不适用于：上游已产出 `lib<name>.a`（无需改名）；CMake 目标 `PREFIX ""` 场景见
  DRAFT-libsnd-0.1.1；库契约建模（package_type/options）见 E221；copy 路径嵌套见
  DRAFT-list-0.4.1 / E097。
- 反例：若库同为系统同名库或需 shared 形态，仍按 R26/E221 规则处理，改名不解决
  链接/隔离问题。

## 相关条目

similar_to: DRAFT-list-0.4.1-conan-copy-libdir-cmakedeps、DRAFT-libsnd-0.1.1-prefix-empty-cppinfo-libs、E221
caused_by: 上游 Makefile ARFLAGS 产出无 lib 前缀归档 + 无 install 目标
prerequisite_of: 后续裸 Makefile 库的 CMakeDeps 消费者链接
