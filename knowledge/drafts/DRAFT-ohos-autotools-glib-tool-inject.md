# DRAFT: autotools make 变量覆盖 glib 工具（pkg-config --variable 不可靠）

- **草稿 ID**: `DRAFT-ohos-autotools-glib-tool-inject`
- **触发软件**: telepathy-glib 0.24.2
- **状态**: DRAFT（待主编/AI 审核提升为 E 条目）
- **姊妹条目**: DRAFT-ohos-glib-test-framework-cmake-inject（libayatana-common，
  CMake 场景的 COMPILE_SCHEMA_EXECUTABLE 注入——同类问题，本条目覆盖
  autotools/make 场景）

## 问题

```
make[2]: *** [Makefile:2282: _gen/genums.c] Error 127
```

**根因**：autotools 库的 configure.ac 常通过
`GLIB_MKENUMS=\`$PKG_CONFIG --variable=glib_mkenums glib-2.0\`` 获取 glib
工具（glib-mkenums/glib-genmarshal）路径——telepathy-glib 0.24.2 在 make 阶段
用它生成 `_gen/genums.c` 等枚举源。但 conan 的 **PkgConfigDeps 生成的
glib-2.0.pc 只含标准字段**（prefix/libdir/includedir），**不含
`glib_mkenums`/`glib_genmarshal` 这类自定义变量**——pkg-config 查询返回空，
configure 得到的 GLIB_MKENUMS 为空，make 执行生成规则时报
`_gen/genums.c ... Error 127`（command not found）。

> 若 build() 注入的 PKG_CONFIG_PATH 指向 glib 原始 .pc，则返回 `//bin/` 错误
> 路径（原始 .pc 的 prefix=/ 未改写，同 E135/libintl 类问题）。

## 方案（make 命令行变量覆盖 glib 工具绝对路径）

```python
# conanfile.py build()
glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
self.run("cd {}/telepathy-glib && make -j1 "
         "GLIB_MKENUMS={}/glib-mkenums "
         "GLIB_GENMARSHAL={}/glib-genmarshal "
         "GLIB_COMPILE_SCHEMAS={}/glib-compile-schemas".format(
             self.source_folder, glib_bin, glib_bin, glib_bin),
         env="conanbuild")
```

make **命令行变量**优先级最高，且不改源码/configure——一次性覆盖全部 glib
工具变量（按需；telepathy-glib 用前两个）。

**与 CMake 场景互补**：libayatana-common 用 `tc.variables[COMPILE_SCHEMA_
EXECUTABLE]` 注入（CMake 变量）；autotools 用 make 命令行变量覆盖——机制
不同、问题同族（glib 工具由 pkg-config --variable 查询在 conan 下不可靠）。

## 验证

telepathy-glib 0.24.2：make 命令行覆盖 GLIB_MKENUMS/GLIB_GENMARSHAL 后
`_gen/genums.c` 正常生成（Error 127 消失）；conan-verify 全门禁 PASS
（G0-G5/L2/L4/L5），test_package 编译链接成功。

## 推广价值

适用于任何用 `pkg-config --variable=glib_*` 查 glib 工具的 autotools 库
（telepathy-glib、其他 GLib 生态 autotools 库）在 conan PkgConfigDeps 环境。

## 相关条目

- DRAFT-ohos-glib-test-framework-cmake-inject：CMake 场景的 COMPILE_SCHEMA_
  EXECUTABLE 注入（同类问题互补）
- E135：libintl.so.8 运行时签名（prefix=/ 未改写同族）
- DRAFT-ohos-dbus1-pc-alias：pkg-config 解析问题
