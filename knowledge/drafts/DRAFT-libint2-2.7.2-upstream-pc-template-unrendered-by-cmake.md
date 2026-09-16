# 上游 .pc 模板经 CMake 渲染后前缀/版本为空（pkg-config 消费者静默拿到垃圾标志）

**草稿条目**（`DRAFT-libint2-2.7.2-upstream-pc-template-unrendered-by-cmake`）
来源：libint2 2.7.2 Conan 适配（2026-09-13）。

## 现象

安装出来的 `libint2.pc` 内容是：

```ini
prefix=
exec_prefix=
libdir=
includedir=

Name:
Description: a library for the evaluation of molecular integrals of many-body operators over Gaussian functions
Version:
Libs: -L${libdir} -lint2
Cflags: -I${includedir} -I${includedir}/libint2
```

于是：

```console
$ PKG_CONFIG_PATH=<pkg>/lib/pkgconfig pkg-config --cflags --libs libint2
-I -I/libint2 -L -lint2
$ echo $?
0
```

**exit code 仍是 0** —— 失败是静默的，只有在消费者编译阶段才会以
`fatal error: 'libint2.h' file not found` 的形式暴露，排查时很容易误判为"包没装头文件"。

## 根因

上游 `libint2.pc.in` 用的是 **autotools 变量**：

```ini
prefix=@prefix@
exec_prefix=@exec_prefix@
libdir=@libdir@
includedir=@includedir@
Name: @PACKAGE_NAME@
Version: @PACKAGE_VERSION@
Cflags: -I${includedir} -I${includedir}/libint2 @CPPFLAGS@
```

但本归档使用的是上游 Release 的 exported library，构建走 **CMake**：
`CMakeLists.txt` 只做 `configure_file(libint2.pc.in ${PROJECT_BINARY_DIR}/libint2.pc @ONLY)`，
而 CMake 侧并没有定义 `prefix`/`libdir`/`PACKAGE_VERSION` 这些变量，
**未定义的 `@var@` 占位符被替换成空串**，于是 .pc 全空（autotools 路径下由 autoconf 提供这些变量，所以上游自己没暴露这个问题）。

## 推荐方案：package() 里用 `${pcfiledir}` 重写

```python
pc_path = os.path.join(self.package_folder, "lib", "pkgconfig", "libint2.pc")
pc_content = (
    "prefix=${pcfiledir}/../..\n"
    "exec_prefix=${prefix}\n"
    "libdir=${prefix}/lib\n"
    "includedir=${prefix}/include\n"
    "\n"
    "Name: libint2\n"
    "Version: 2.7.2\n"
    "Libs: -L${libdir} -lint2\n"
    "Cflags: -I${includedir} -I${includedir}/libint2\n"
)
save(self, pc_path, pc_content)
```

要点：

- `${pcfiledir}` 由 pkg-config/pkgconf 自身展开（实测 pkg-config 0.29.2 支持），
  因此**不写死任何构建机或 conan 缓存路径**，包可重定位；
- 不改上游源码，也不依赖 autotools；
- 消费契约要有回归守卫：用 `pkg-config --cflags/--libs` 的返回值真实编译并运行一个消费者
  （本归档的做法见 `archives/l/libint2/2.7.2/test_package/test_pkgconfig.c` + `conanfile.py::test()`）。

修复后实测：

```console
$ PKG_CONFIG_PATH=<pkg>/lib/pkgconfig pkg-config --cflags --libs libint2
-I<pkg>/include -I<pkg>/include/libint2 -L<pkg>/lib -lint2
$ clang -std=c11 $(pkg-config --cflags libint2) test_pkgconfig.c -o t $(pkg-config --libs libint2) && ./t
[PASS] pkg-config consumer: C API 可用 (need_memory_eri(1) = 14133)
```

## 回退方案

不修 .pc，让消费者改用 CMake config（`find_package(... CONFIG)`）或手工 `-I/-L`。
可行，但等于放弃 pkg-config 契约，必须在 notes 中如实标注"该契约未打通"。

## 禁忌

- **不要**把构建机绝对路径写进 .pc（`prefix=/storage/...`、`prefix=.../.conan2/p/...`）：包不可重定位，换个缓存即失效。
- **不要**删掉 .pc 或不装它："上游本来提供 pkg-config 元数据"这件事被抹掉，缺陷只是被藏起来。

## 关联

- E247：静态 C API 归档的 pkg-config `Libs.private` 不完整（同类"上游 .pc 元数据缺陷"，
  但根因不同：E247 是字段缺失，本条是模板占位符未渲染）。
- 可复用判据：凡是"上游同时有 autotools + CMake 两条安装路径"的库，都要实际跑一次
  `pkg-config --cflags --libs` 看输出里有没有空路径。
