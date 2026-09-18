# Conan 打包 autotools 库：安装布局与 pkg-config 前缀失真

> 知识草稿（与 libart-lgpl 2.3.21 归档适配 PR 一同交付）。
> 来源：libart-lgpl 2.3.21 适配，`conan create`（ohos-aarch64 profile, clang 15）rc=0，
> 上游 demo 程序 6/6、test_package 消费者断言 20/20 真机通过。
> 载体：libart_lgpl（GNOME libart 的 LGPL 分支，autotools + libtool 2.2.6，
> 安装 `include/libart-2.0/libart_lgpl/*.h` + `lib/libart_lgpl_2.so*` + `libart-2.0.pc`）。

## 问题现象

适配完成后第一次跑 test_package 时，CMake **配置阶段**即失败（不是编译或链接）：

```
CMake Error in CMakeLists.txt:
  Imported target "libart-lgpl::libart-lgpl" includes non-existent path

    ".../p/b/libara9609a2f6f09b/p/include/libart_lgpl"

  in its INTERFACE_INCLUDE_DIRECTORIES.
```

把 includedirs 改对之后，包内又发现另一个失真：`lib/pkgconfig/libart-2.0.pc` 里

```
prefix=/
exec_prefix=${prefix}
libdir=${prefix}/lib
includedir=${prefix}/include

Cflags: -I${includedir}/libart-2.0     # 展开为 -I/include/libart-2.0
Libs:   -L${libdir} -lart_lgpl_2       # 展开为 -L/lib
```

也就是说：**同一个包，CMake 消费者因为 cpp_info 错配而在配置阶段失败，pkg-config
消费者则会静默拿到系统路径**（`/include`、`/lib`），在 OHOS 设备上表现为“明明装了库却
找不到头/链接到系统里别的东西”。

对照实验（判断依据，不要靠推理）：同一份上游源码在 x86_64 Linux 上用原生
`./configure --prefix=<dir> && make install` 安装后，`.pc` 是**正确**的：

```
$ PKG_CONFIG_PATH=<dir>/lib/pkgconfig pkg-config --cflags --libs libart-2.0
-I<dir>/include/libart-2.0 -L<dir>/lib -lart_lgpl_2
```

只有经 Conan（`--prefix=/` + `DESTDIR`）安装才会变成 `prefix=/`。这条对照能把
“上游 `.pc.in` 写错”与“Conan 安装前缀失真”两种可能区分开。

## 根因

两类失真同源：都没有以“**安装后的实际布局**”为准反推 `cpp_info` 与 `.pc`。

1. **`.pc` 的 prefix 失真**。Conan 的 Autotools 流程以 `--prefix=/` 配置、再
   `make install DESTDIR=<package_folder>`。上游 `libart-2.0.pc.in` 的 `@prefix@`
   在配置阶段就被写成 `/`，安装只是把文件复制进包目录，内容不会改。于是 `.pc` 里所有
   路径都指向根目录。
2. **`cpp_info.includedirs` 与实际布局不符**。上游 autotools 常把公共头放在
   `include/<api-name>/<libname>/`，libart 实测是
   `include/libart-2.0/libart_lgpl/`（`--includedir` 被上游追加了 `libart-2.0`）。
   若配方按直觉写 `includedirs=["include","include/libart_lgpl"]`，CMakeDeps 会把不存在
   的目录写进 `INTERFACE_INCLUDE_DIRECTORIES`；CMake 对**不存在的** include 目录是硬
   错误（不是一个警告），所以在 `find_package` 之后立刻 `CMake Generate step failed`。

## 为什么容易漏

- 只写“直接调用编译器 + `-I<dep.includedirs>`”的消费者测试**不会**触发问题 2：
  `-I` 指向不存在的目录只是被忽略。只有走 **CMakeDeps `find_package` + target_link_libraries**
  的 test_package 才会把 `INTERFACE_INCLUDE_DIRECTORIES` 校验起来。
- 问题 1 更隐蔽：`conan create` 全程 rc=0，上游程序与消费者断言也全绿，因为 CMakeDeps
  用的是 `cpp_info` 而不是 `.pc`。只有显式 `pkg-config --cflags/--libs` 才会暴露。

## 修复

以“安装后实测”为准反推：

```sh
# 1) 让包落地后看真实布局（不要靠猜）
find <pkg> -maxdepth 3 -type d | sort
#   <pkg>/include
#   <pkg>/include/libart-2.0
#   <pkg>/include/libart-2.0/libart_lgpl   <- 头在这里
#   <pkg>/lib
#   <pkg>/lib/pkgconfig
```

```python
# 2) package_info(): 按真实布局写 includedirs
self.cpp_info.libs = ["art_lgpl_2"]
self.cpp_info.includedirs = ["include", "include/libart-2.0"]
self.cpp_info.set_property("pkg_config_name", "libart-2.0")

# 3) package(): 幂等重写 .pc 的前缀，使 pkg-config 消费者拿到包内路径
pkg_config = os.path.join(self.package_folder, "lib", "pkgconfig", "libart-2.0.pc")
if os.path.isfile(pkg_config):
    replace_in_file(self, pkg_config, "prefix=/", "prefix=" + self.package_folder)
    replace_in_file(self, pkg_config, "exec_prefix=${prefix}",
                    "exec_prefix=" + self.package_folder)
    replace_in_file(self, pkg_config, "libdir=${prefix}/lib",
                    "libdir=" + os.path.join(self.package_folder, "lib"))
    replace_in_file(self, pkg_config, "includedir=${prefix}/include",
                    "includedir=" + os.path.join(self.package_folder, "include"))
```

```cmake
# 4) test_package 必须真的走一遍 CMakeDeps，才能把 includedirs 错配挡在配置阶段
find_package(libart-lgpl CONFIG REQUIRED)
target_link_libraries(libart_lgpl_consumer PRIVATE libart-lgpl::libart-lgpl)
```

## 验证

```sh
PKG_CONFIG_PATH=<pkg>/lib/pkgconfig pkg-config --cflags --libs libart-2.0
# 期望：-I<pkg>/include/libart-2.0 … -L<pkg>/lib -lart_lgpl_2
# 而不是 -I/include/libart-2.0 -L/lib

conan create archives/l/libart-lgpl/2.3.21 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 期望：test_package 的 CMake configure 通过，ctest 1/1、消费者断言 20/20
```

## 适用边界

- 适用于所有上游自带 `.pc.in` 的 Conan autotools/CMake 配方，尤其在 OHOS 上会被其他
  项目以 pkg-config 消费时。
- 头文件装在 `include/<name>` 子目录（GNOME 系、libart、部分 Debian 库很常见）而配方
  按默认 `include` 猜测的库，都会命中问题 2。
- 若上游 `.pc` 里的 `prefix` 是 `@prefix@` 但 Conan 配方本来就用
  `--prefix=<package_folder>`（未走 DESTDIR 语义），则不一定会失真；判断依据始终是
  **安装后 `cat` 出来看**，不要按预期推断。

## 相关

- 与 `DRAFT-5851`（Conan CMakeDeps 生成的 `conan_cmakedeps_paths.cmake` 缺
  `CMAKE_PREFIX_PATH`、`PkgConfigDeps` 丢 `.pc` 自定义变量）同属“Conan 生成物与实际
  布局不符”一族；本条针对包内 `.pc` 前缀与 `cpp_info.includedirs` 失真，两者的
  现象与修法都不同，可互相引用。

## 附：不要在上游 PR 中携带 `config.sub`/`config.guess` 全文

同一个仓库的 libart-lgpl 2.3.21 PR 最初把 OHOS 感知的 `config.sub`（2364 行）与
`config.guess`（1818 行）作为文件放入 `patches/`，结果平台 AI 检视直接**跳过**：

```
⚠️ 本次变更过大（7 个可审文件、4513 行，预估需 4 轮分片审查），已超出 AI 代码评审的
处理范围，本次跳过。建议拆分为更小的 PR 以获得有效评审。
```

AI 检视跳过 = 评审门禁拿不到“无 P0/P1”的结论。正确做法是**最小补丁**：给上游自带的
`config.sub` 加一个 17 行的早退分支（见 `archives/a/a52dec/0.7.4`）：

```sh
+# aarch64 and HarmonyOS were introduced after this bundled config.sub.
+case $1 in
+  aarch64-*-linux* | aarch64-*-ohos* | aarch64-linux-ohos)
+    echo "$1"
+    exit 0
+    ;;
+esac
```

配合显式 `--build`/`--host`（不执行 `config.guess`），效果与替换整个脚本相同，而 PR
的可审规模下降了 99%。
