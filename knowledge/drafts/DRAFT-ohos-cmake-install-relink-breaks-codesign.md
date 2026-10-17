# OHOS：CMake 安装期重写 rpath 使 `.codesign` 失效，制品在运行时无法加载

## 问题描述

在 OHOS PC 上，用 Conan + CMake 打出的 KF5 库，**构建树里的那份可以加载，装进
`package_folder/p/lib` 的那份却加载不了**：

```
Error loading shared library .../p/lib/libKF5CoreAddons.so.5.116.0: Permission denied
```

表现是下游库的上游测试全部卡在加载器里、根本进不到 `main()`，看起来像"沙箱不允许
执行用户态二进制"或"搜索路径不对"，实际都不是。

## 根因

CMake 默认给构建树目标写入一条 rpath（由所链接库的目录推导），并在 `install` 时把这条
rpath **重写**成安装树的值。这个"重写"是一次真正的**重新链接**。

OHOS 的 ELF 带 `.codesign` 段，签名发生在构建之后。安装期重链改变了文件内容，签名不再
匹配，加载器于是拒绝该文件。

同一份库的两个副本只差 100 字节 `.dynstr`——正是两条 rpath 字符串：

```
build tree : RUNPATH [/storage/.../qt5-q828d2380abd85/p/lib:...]
installed  : RUNPATH [/storage/.../kcored61d48b68c1fb/p/lib:/storage/.../qt5-.../p/lib]
```

这个"构建树能载、安装树不能载"的不对称，是定位问题的关键。

kcoreaddons5 尤其容易命中：它的配方为保住 KDE 的 `if(UNIX)` 源文件选择，显式设置了
`CMAKE_SYSTEM_NAME=Linux`，因此加载了完整的 Linux ELF 链接规则，rpath 才会被写入并
重写。`CMAKE_SYSTEM_NAME` 为未知的 `HarmonyOS` 时这些链接标志本就未定义，反而不会中招。

## 解决方案

在 `generate()` 中关闭 rpath，让构建树与安装树一致，CMake 便无事可改、不再重链：

```python
tc.variables["CMAKE_SKIP_RPATH"] = "ON"
```

依赖库改由 `LD_LIBRARY_PATH` 定位——**OHOS 加载器是认这个变量的**（实测：给一个无 rpath
的旧构建配上完整闭包的 `LD_LIBRARY_PATH`，它成功加载并运行）。上游测试因此需要
`_library_runtime_env()` 之类的机制把所有依赖的 `lib` 目录挂上去。

## 验证

设 `CMAKE_SKIP_RPATH=ON` 重建后：

```bash
# 1) 安装副本与构建树副本应逐字节一致
cmp -l <pkg>/b/build/Release/bin/libX.so.5.116.0 <pkg>/p/lib/libX.so.5.116.0
# 2) 安装副本应能直接加载（设备自带 python3）
python3 -c 'import ctypes;ctypes.CDLL("<pkg>/p/lib/libX.so.5")'
```

随后依赖它的上游测试才能进入 `main()` 并产出 QTest 结果。

## 三个容易走错的方向

1. **误判为搜索路径问题**，于是加 `CMAKE_BUILD_RPATH` 或定义
   `CMAKE_SHARED_LIBRARY_RUNTIME_<lang>_FLAG`。这会**加重**问题：一旦 rpath 被写入，
   安装期重写必然发生，签名必被破坏。
2. **误判为沙箱拒绝执行**。用 `patchelf` 改 rpath 做验证也是错的：改写 ELF 本身就让
   `.codesign` 失效，二进制当场被拒，实验什么也证明不了。
3. **误判为 `LD_LIBRARY_PATH` 不被接受**。注意 `Error loading shared library X`
   有两种含义——找不到 X，或找到了 X 却拒绝加载 X。只看这句话会把它当成搜索路径故障。

## 判别方法

```bash
# 两份副本的 rpath 是否不同
readelf -d <build-tree-lib> | grep -Ei 'rpath|runpath'
readelf -d <installed-lib>  | grep -Ei 'rpath|runpath'
# 是否逐字节一致
cmp -l <build-tree-lib> <installed-lib> | wc -l
# 把可疑文件复制到中性目录再加载：仍失败 => 内容问题，与路径/xattr 无关
```
