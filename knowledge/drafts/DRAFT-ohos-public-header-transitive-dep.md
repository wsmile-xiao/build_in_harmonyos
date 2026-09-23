# DRAFT: 公开头文件链的直接依赖透传（transitive_headers）

- **草稿 ID**: `DRAFT-ohos-public-header-transitive-dep`
- **触发软件**: telepathy-glib 0.24.2
- **状态**: DRAFT（待主编/AI 审核提升为 E 条目）
- **姊妹条目**: DRAFT-ohos-dbus1-pc-alias（dbus-1.pc 别名，configure 阶段）

## 问题

```
In file included from .../telepathy-glib/account.h:31:
In file included from .../telepathy-glib/connection.h:33:
In file included from .../telepathy-glib/proxy.h:29:
.../dbus-glib.h:30:10: fatal error: 'dbus/dbus-shared.h' file not found
#include <dbus/dbus-shared.h>
```

**根因**：库的**公开头文件链**会间接 include 传递依赖的头。telepathy-glib 的
公开头链 `telepathy-glib.h → proxy.h → dbus-glib.h`，而 dbus-glib.h 又
`#include <dbus/dbus-shared.h>`——最终需要 **dbus 包**的头。但配方若只把
dbus 作为 dbus-glib 的传递依赖（不直接 `requires` dbus），conan 的
`cpp_info.requires` / CMakeDeps **只透传直接依赖的头路径**，dbus 的
`include/dbus-1.0` 不会进入消费者的编译 include 路径 → 编译报错。

> 反例：若在 `cpp_info.requires` 直接引用 `dbus::dbus` 而 dbus 又不是配方直接
> 依赖，会报 `package_info(): ... 'dbus::' ... not a direct requirement of the
> recipe`。

## 方案（dbus 提升为直接依赖 + 透传头文件）

```python
# conanfile.py
def requirements(self):
    # dbus 提升为直接依赖并透传头文件（公开头链 dbus-glib.h → dbus/dbus-shared.h）
    self.requires("dbus/1.14.10", transitive_headers=True, transitive_libs=True)

def package_info(self):
    self.cpp_info.requires = ["glib::glib-2.0", "glib::gio-2.0",
                              "dbus-glib::dbus-glib", "dbus::dbus"]
```

CMakeDeps 据此把 dbus 的 `include/dbus-1.0` 透传给消费者（test_package/下游），
`dbus/dbus-shared.h` 可解析。

**判断依据**：编译报错指向的 `.h` 属于哪个包（`dbus/dbus-shared.h` → dbus 包），
沿 include 链逐层找最终提供该头的包，将其声明为直接依赖。

## 验证

telepathy-glib 0.24.2：dbus/1.14.10 声明为直接依赖（transitive_headers）+
`cpp_info.requires` 引用 `dbus::dbus` 后，test_package 编译通过；conan-verify
全门禁 PASS（G0-G5/L2/L4/L5）。

## 推广价值

适用于任何「公开头文件链经多层传递依赖到头」的库在 conan 环境——编译报错
指向的 .h 定位到提供包后，提升为直接依赖 + transitive_headers 即可。

## 相关条目

- DRAFT-ohos-dbus1-pc-alias：dbus-1.pc 别名（configure 阶段）
- DRAFT-ohos-glib-test-framework-cmake-inject：gtest/gmock include 注入（同为
  include 路径透传问题）
