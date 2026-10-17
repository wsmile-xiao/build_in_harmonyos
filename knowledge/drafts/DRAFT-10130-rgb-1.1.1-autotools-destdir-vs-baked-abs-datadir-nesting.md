# DRAFT-10130-rgb-1.1.1: `Autotools.install()` 的 `--destdir` 与「烤进二进制的绝对运行时路径」互相打架

## 症状

`conan create` 走到 test_package 时，包内按规范路径找不到数据文件：

```
FAIL: packaged default database missing: <CONAN_HOME>/p/b/rgbXXXXXX/p/share/X11/rgb.txt
```

而被测程序自己在无参运行时报的是：

```
showrgb: unable to open rgb database "/share/X11/rgb"
```

即：**程序找的绝对路径**与**数据实际安装的位置**不一致；把 `--with-*-dir` 改成
包内绝对路径后，`make install` 又把文件装到了 `<pkg>/<pkg>/share/X11/rgb.txt`
这种**重复嵌套**的位置，规范路径下依旧找不到。

## 根因

Conan 的 `Autotools.install()` 用 `--destdir=<package_folder>` 安装。autotools 的
`DESTDIR` 语义是「把 `$DESTDIR` 前缀拼到每一个安装目录上」，因此：

- configure 期给出的 `--prefix`、以及任何**显式绝对**的 `--with-xxx-dir=<abs>`，
  在 `make install` 时都会变成 `<package_folder>/<abs>`；
- 而编译期烤进二进制的字符串（这里是 `RGB_DB="$(db_dir)/$(db_file)"`）用的
  **就是那个绝对 `<abs>`**，不带 `package_folder` 前缀。

两条路径规则不一致 ⇒ 只要「需要把运行时绝对路径烤进产物」和「用 conan 的
destdir 安装」同时成立，数据文件就必然装到嵌套目录里，程序按烤入路径找不到它。

## 最小复现

任何 autotools 包，只要它的 Makefile 里存在
`<x>dir = $(某绝对目录)` + `<x>_DATA = ...`，并且配方为了让运行时默认值正确而把该
目录设成 `self.package_folder` 下的绝对路径：

```
--prefix=/                      # 或任意
--with-<x>-dir=<package_folder>/share/<pkgdata>/<file>
make install DESTDIR=<package_folder>
# 结果：文件落在 <package_folder>/<package_folder>/share/<pkgdata>/<file>.txt
# 期望：  <package_folder>/share/<pkgdata>/<file>.txt
```

## 已试过的失败方案

1. **只设 `--prefix`，不显式给 `--with-*-dir`**：安装位置正确，但编译期烤入的
   绝对路径跟着 `--prefix`（build-driver 用 `--prefix=/`）变成 `/share/X11/rgb`，
   运行时仍然找不到 ⇒ test 依然 FAIL。
2. **给 `--with-*-dir` 传相对路径**：`AC_SUBST` 后 `RGB_DB` 变成相对串，
   程序在任意 cwd 下运行仍找不到库。

## 最终方案

保留「烤入包内绝对路径」（因为 `self.package_folder` 在 `generate()` 阶段已可知，
且运行时确实需要绝对串），并在 `package()` 安装之后**把数据文件归位**：

- 在 `package_folder` 内递归找该数据文件的实际落点；
- `shutil.move` 到规范路径（`<pkg>/share/X11/rgb.txt`）；
- 删除 `--destdir` 叠加产生的重复绝对路径壳目录（只在本包目录树内操作）；
- 归位失败要显式 `output.error`，不允许静默产出「装不到默认数据」的包。

## 适用边界

- **适用**：conan recipe 用 `Autotools.install()`（即 destdir  staged install），
  且上游 Makefile 把某个安装目录同时用于「数据落点」和「编译期默认路径宏」。
  xorg 系 `--with-*-dir` / `-*-datadir` 类开关是典型场景。
- **不适用**：
  - 纯 `--prefix` 驱动、没有第二套绝对路径注入的包（不会叠加）；
  - CMake 系（`CMakeToolchain` 走 `CMAKE_INSTALL_PREFIX` 直接指向 package_folder，
    不用 DESTDIR，语义不同）；
  - 若上游支持运行时环境变量/相对可定位数据目录，**优先用那个**而不是烤绝对路径，
    就不需要归位。
- 更干净的替代（若上游允许）：把 `--with-*-dir` 设成 `<package_folder>/...` 的同时
  用 `DESTDIR=""` 直装（不走 staging）。本包未采用，因为会绕过 conan 的打包隔离约定。
