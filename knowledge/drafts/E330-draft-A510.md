# E330 — CMake 未知平台（HarmonyOS）共享库无 SONAME

## 现象

包内工具二进制（bin/iio_info）执行时报：

```
Error loading shared library ../libiio.so: (needed by .../bin/iio_info)
Error relocating .../bin/iio_info: iio_context_get_name: symbol not found
```

`readelf -d bin/iio_info` 的 DT_NEEDED 是构建树相对路径 `../libiio.so` 而非
裸库名；`readelf -d lib/libiio.so` 无 SONAME 条目。

## 根因

CMake 遇到未识别的 `CMAKE_SYSTEM_NAME`（HarmonyOS 在当前 CMake 版本无
`Platform/HarmonyOS` 模块，会打印 "System is unknown to cmake"）时，不为共享
库定义 SONAME flag（`CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 为空）。链接器因此在
libXXX.so 里不写 SONAME；链接同仓库工具时 lld 把链接命令行上的构建树路径
（`../libiio.so`，来自 CMake 的 `libdir` 相对布局）直接记进 DT_NEEDED。安装
到 `bin/ + lib/` 目录后，该相对路径不再有效，musl 加载器找不到库，且因
DT_NEEDED 路径含斜杠，LD_LIBRARY_PATH 也不参与解析 → 全部符号重定位失败。

## 处方

`conanfile.py` 的 `generate()`：

```python
tc.extra_sharedlinkflags.append("-Wl,-soname,libiio.so")
```

（包内仅一个共享库时可直接用 unversioned 名。）重建后：

```
readelf -d lib/libiio.so | grep SONAME     # → Library soname: [libiio.so]
readelf -d bin/iio_info | grep NEEDED      # → Shared library: [libiio.so]
```

工具即可由 LD_LIBRARY_PATH=<pkg>/lib 正常加载。

## 关联

- E120/E132：OHOS SDK lld 自身依赖 libxml2.so.16 的加载问题（另一条链路上的
  libxml2 陷阱，注意区分：本条是产物库无 SONAME，E120 是链接器自身的运行时依赖）。
- 反向陷阱：不要用 GNU ld（`-fuse-ld=.../bin/ld`）绕 E120——GNU ld 链接的 ELF
  缺 `.note.ohos.ident`，会被 OHOS 沙箱内核加载器直接拒绝（Permission denied），
  libiio 0.25 适配实测验证（PR #8323 notes.md 问题 2）。

## 来源

libiio 0.25 适配（PR #8323，2026-09-05，零 patch + 显式 SONAME 注入，CI 全绿）。
