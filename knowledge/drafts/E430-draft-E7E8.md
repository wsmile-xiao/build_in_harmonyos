# E430 — `Autotools.install()` 的 DESTDIR 与绝对 prefix 拼接，产物埋进 `<pkg>/storage/...`

## 错误特征
`conan create` 全程无报错，但 test_package 与消费者找不到可执行文件：

```
======== Testing the package: Executing test ========
RUN: pianod -v
/system/bin/sh: pianod: inaccessible or not found
```
包目录里却是这样一层深坑：
```
.conan2/p/b/<pkg>/p/storage/Users/currentUser/.conan2/p/b/<pkg>/b/build-release/prefix/bin/pianod
```

## 触发条件
- 构建系统: autotools（conan2 `Autotools.install()`）
- 阶段: packaging → consumer runtime
- 前提: `generate()` 里把 `--prefix` 配成构建树/宿主机的**绝对路径**

## 根因分析
`Autotools.install()` 以 `destination or self.package_folder` 作为 `DESTDIR`。
automake 的安装路径计算是字面拼接 `$(DESTDIR)$(bindir)`，而 `bindir` 来自展开后的绝对
`prefix`。于是 `DESTDIR=<pkg>` + `prefix=<abs build path>` 直接串成
`<pkg><abs path>/bin`，包内标准 `bindir` 为空，`cpp_info.bindirs=["bin"]` 自然找不到东西。

## 推荐方案
`--prefix=/`，让 DESTDIR 展开成扁平的 `<pkg>/bin`、`<pkg>/share`：

```python
tc.configure_args.append("--prefix=/")   # 依赖注入仍留在 self.build_folder 内（R49）
```
代价是编译期固化的 datadir 类宏（如 pianod2 的 `DEFAULT_WWWDIR`）会变成 `//share/...` 而不可用，
需要在 `package_info()` 里用 `runenv_info.define_path(...)` 把包内真实路径交给消费者，
或由程序自身的命令行参数指定。

## 验证
`conan create` 后 `find <package_folder>/bin -type f` 必须命中目标可执行文件。

## 影响范围
所有使用 `Autotools.install()` 的 autotools 配方（application 与 library 皆然）。
