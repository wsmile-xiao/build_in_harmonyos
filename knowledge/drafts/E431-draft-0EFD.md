# E431 — `AutotoolsDeps` 把 shared 依赖注入 autoconf 运行期探测，报 `cannot run C compiled programs`

## 错误特征
configure 在很早期就中止，而编译器本身工作正常：

```
checking whether the C compiler works... yes
checking for C compiler default output file name... a.out
checking whether we are cross compiling... configure: error: in `<build dir>':
configure: error: cannot run C compiled programs.
If you meant to cross compile, use `--host'.
```
手工执行被探测的 `conftest` 会看到真实原因：
```
Error loading shared library libcurl.so: (needed by ./conftest)
Error relocating ./conftest: curl_easy_strerror: symbol not found
```

## 触发条件
- 构建系统: autotools（conan2 `AutotoolsDeps`）
- 阶段: configure（交叉编译判定 / 任何 `AC_RUN_IFELSE`）
- 前提: 依赖集合里存在 **shared** 库（ohpcd 的 `curl/*` 只发布 `libcurl.so`）

## 根因分析
`AutotoolsDeps` 会把**全部**依赖的 `-I/-L/-l` 注入 `CPPFLAGS/LDFLAGS/LIBS`，autoconf 的
交叉编译判定用同一个环境链接 `conftest` 并**真的运行**它。构建阶段没有 `VirtualRunEnv`，
`LD_LIBRARY_PATH` 不含依赖 libdir，动态 loader 解析失败 → configure 判定"不能运行目标程序"
→ 认为是交叉编译且未给 `--host`，直接 error。

## 推荐方案
1. 不要为了"方便"加 `AutotoolsDeps`：`PkgConfigDeps` 产出的 `.pc` 已带 `-I/-L/-l`，
   `PKG_CHECK_MODULES`/`AC_CHECK_LIB` 按需取用即可（且不会污染与依赖无关的探测）。
2. 在 `build()` 内把依赖 libdir 导出到 `LD_LIBRARY_PATH`，兜住确实需要运行的探测：
```python
os.environ["LD_LIBRARY_PATH"] = os.path.pathsep.join(
    self._dep_libdirs() + [os.environ.get("LD_LIBRARY_PATH", "")])
```

## 验证
构建日志出现 `checking whether we are cross compiling... no`，并继续到依赖探测阶段。

## 影响范围
所有 autotools 配方 + 含 shared 依赖包的场景（鸿蒙侧 curl、Qt、KDE 框架等大量 .so）。
