# DRAFT-libsavitar-4.4.1-installed-relative-include-vendored-header — 安装后公共头相对 include 指向内嵌子工程头断链

> 草稿知识项 — 上游公共头用相对 include 引用内嵌子工程头（如
> `#include "../pugixml/src/pugixml.hpp"`），安装到 include/<Lib>/ 后
> 相对路径断链 → 配方 package() 必须把子工程头复制到包内相对位置。
> 来源：libsavitar 4.4.1 适配（task libsavitar-4.4.1-r01-pc2-37，
> 2026-09-27）
> 同 stem 配对：`knowledge/drafts/DRAFT-libsavitar-4.4.1-installed-relative-include-vendored-header.kv`

## 问题（现象 / error_signature）

`conan create` 的 test_package 消费者编译报：

```
In file included from .../test.cpp:3:
.../include/Savitar/ThreeMFParser.h:24:10: fatal error:
  '../pugixml/src/pugixml.hpp' file not found
  #include "../pugixml/src/pugixml.hpp"
          ^~~~~~~~~~~~~~~~~~~~~~~~~~~~
```

## 根因（root_cause）

1. 上游 `src/ThreeMFParser.h` 用相对路径引用顶层内嵌子工程头：
   `#include "../pugixml/src/pugixml.hpp"`（pugixml 随源码树位于
   libSavitar-4.4.1/pugixml/src/）。源码树内 `src/` 的 `../pugixml/...`
   能解析。
2. 父库 `install(TARGETS Savitar ... PUBLIC_HEADER DESTINATION
   ${CMAKE_INSTALL_INCLUDEDIR}/Savitar)` 把公共头安装到
   `include/Savitar/` 子目录。安装后该相对 include 解析为
   `include/Savitar/../pugixml/src/pugixml.hpp` =
   `include/pugixml/src/pugixml.hpp`，但该位置没有文件。
3. 子工程 pugixml 自身的 install 规则默认把头平铺到 include/
   （`include/pugixml.hpp`），与父库头期望的 `include/pugixml/src/`
   子目录布局不一致 → 消费者编译断链。

## 方案（solution）

在配方 `package()` 中把子工程公共头复制到上游相对 include 期望的
包内位置（pugiconfig.hpp 必须同目录，pugixml.hpp 对它是同目录
相对包含）：

```python
from conan.tools.files import copy

def package(self):
    CMake(self).install()
    copy(self, "pugixml.hpp",
         src=os.path.join(self.source_folder, "pugixml", "src"),
         dst=os.path.join(self.package_folder, "include", "pugixml", "src"))
    copy(self, "pugiconfig.hpp",
         src=os.path.join(self.source_folder, "pugixml", "src"),
         dst=os.path.join(self.package_folder, "include", "pugixml", "src"))
```

不修改上游源码（符合补丁最小化），只在打包阶段补齐布局。

## 验证（verification）

`conan create` 后 test_package 消费者编译不再报
`'../pugixml/src/pugixml.hpp' file not found`；包内
`include/pugixml/src/pugixml.hpp` 存在，`include/Savitar/` 下公共头
的相对 include 可正常解析。

本库实测：补丁后 G2 PASS，test_package 输出 "parse OK / serialize OK"。

## 适用边界（applicability）

公共头用相对路径（`../xxx/src/xxx.hpp`）引用内嵌 vendored 子工程头，
且 install 把公共头装入 include/<Lib>/ 子目录的 CMake 库配方。

## 反例与限制（counterexample / limitations）

若上游 install 规则本身把子工程头安装到与相对路径一致的位置（或公共头
改为 `<pugixml.hpp>` 形式并声明子工程 includedir），则不需要 package()
复制。复制的是固定文件名清单；子工程头较多或命名可变时建议遍历复制以
保持相对结构。