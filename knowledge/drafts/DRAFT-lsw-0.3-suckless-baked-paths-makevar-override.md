# DRAFT-lsw-0.3-suckless-baked-paths-makevar-override

> suckless 裸 Makefile 烧死 `CC=cc` 与系统路径（`X11INC=/usr/X11R6`），且 **X11 头文件族
> 跨两个 Conan 包**（`X11/Xlib.h` 属 libx11、`X11/X.h` 属 xorgproto 协议头包）⇒
> make 命令行覆盖**聚合变量** `INCS`/`LIBS`，遍历**全部 host 依赖（含传递）**收集绝对
> `-I`/`-L`，零补丁。
> 本条为池件 `DRAFT-PKG-VER-suckless-baked-paths-makevar-override`（dmenu 5.4 实证）在
> lsw 0.3 上的认领实例，并补出池件未写明的**第三层症状**。

## 症状（三层，lsw 0.3 实测 2026-09-22）

```
# 第一、二层（同池件，dmenu 实证）
$ make
make: cc: No such file or directory          # cc 别名不存在
$ make CC=clang
fatal error: 'X11/Xlib.h' file not found     # -I/usr/X11R6/include 不存在

# 第三层 = 本条新增：只注入 libx11 一个包的 include 目录仍不够
Xlib.h:44:10: fatal error: 'X11/X.h' file not found
```

第三层的根因：`X11/Xlib.h` 内部 `#include <X11/X.h>`，而 `X.h`/`Xproto.h` 等**协议头**由
`xorgproto` 交付（OHOS 归档里 libx11/6.4.0 `requires("xorgproto/2025.1", transitive_headers=True)`
且 `cpp_info.requires = ["xorgproto::xorgproto"]`）。配方若按直觉写
`x11.cpp_info.includedirs[0]`，就只喂了 libx11 自己的目录，协议头永远找不到——
**症状从"缺 Xlib.h"变成"缺 X.h"，容易被误判成依赖未发布而去 block 依赖**。

## 修法（零补丁，配方 `build()`）

```python
incs = " ".join(f"-I{os.path.join(dep.package_folder, d)}"
                for dep in self.dependencies.host.values()
                for d in dep.cpp_info.includedirs)
libs = " ".join(f"-L{os.path.join(dep.package_folder, d)}"
                for dep in self.dependencies.host.values()
                for d in dep.cpp_info.libdirs)
self.run(f'make CC={cc} INCS="{incs}" LIBS="{libs} -lX11" lsw')
```

要点：
- 遍历 `self.dependencies.host.values()`（**含传递依赖**）而非只取直接依赖那一个包；
- `cpp_info.includedirs`/`libdirs` 是**相对** `package_folder` 的路径 ⇒ 必须 `os.path.join`
  成绝对路径再拼 `-I`/`-L`；
- 覆盖的是 `config.mk` 里的聚合变量 `INCS`/`LIBS`（上游 `INCS=-I${X11INC}`、
  `LIBS=-L${X11LIB} -lX11`），因此不必逐个改被烧死的路径变量；
- `cc` 取自 conf `tools.build:compiler_executables`（R33），不裸写硬编码；
- 上游源码零改动、零 `.patch`。

## 与"依赖未发布"的区分（防误 block）

`X11/X.h file not found` **不是** xorgproto 未发布。判别两步：
`grep -n requires archives/l/libx11/6.4.0/conanfile.py`（应见 `xorgproto` +
`transitive_headers=True`）+ `preflight_check.sh lsw/0.3` 报"所有依赖均已发布"。
两步都过了还缺头，就是**注入面不全**，属于本条机制，不要转手依赖。

## 判别与边界

- 只适用裸 Makefile/config.mk 烧路径的包；autotools/CMake 不适用（框架自己算路径）。
- 池件的 X11 双版本系坑（libxft 钉 `libx11/1.8.13` vs libxinerama 钉 `libx11/6.4.0`
  同图冲突）在 lsw 不出现：lsw 只依赖 libx11/6.4.0，无 fontconfig/Xft/Xinerama。
- lsw 上游无任何测试目标（`N_static=0`），消费者测试走无 DISPLAY 确定性错误路径
  （E471 家族，属 hit 非新增），**本 PR 的 B 承载就是这条 make 变量覆盖机制**。
