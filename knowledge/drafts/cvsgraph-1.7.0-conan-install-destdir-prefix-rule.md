# cvsgraph 1.7.0 — conan install() 自动 DESTDIR：手动 configure 必须 --prefix=/

## 现象

包构建成功（make install 无报错），但 conan 包根目录长这样：

```
<package_folder>/
  storage/          ← 整个 /storage/Users/.../p/bin 都嵌在这里
  conaninfo.txt
  conanmanifest.txt
```

没有 `bin/`。test_package 找二进制报 `inaccessible or not found`。

## 根因

本仓库使用的 OHOS conan（2.29.1 适配版）与上游 conan 2 行为不同（读
`conan/tools/gnu/autotools.py` 源码实证）：

1. `AutotoolsToolchain.__init__` 默认 `prefix="/"`（上游 conan 默认是
   package_folder）
2. `Autotools.install()` 若参数中无 `DESTDIR=`，自动插入
   `DESTDIR=<package_folder>`（autotools.py L111-112）

我的配方绕过 `autotools.configure()` 手动调 configure（OHOS 需要显式
`/system/bin/sh`），当时传了 `--prefix=<package_folder 绝对路径>` →
make install 变成 `DESTDIR=<pkg>` + `prefix=<pkg 绝对>` 双叠 →
文件落进 `<pkg>/storage/Users/.../p/bin`。

fcrackzip 配方里 `--prefix=/` + `${prefix}/bin` 的写法正是对该行为的
正确适配（此前照抄只知其然，现已知其所以然）。

## 修复

手动调 configure 一律：

```python
self.run(f'... /system/bin/sh "{conf}" --prefix=/', env="conanbuild")
```

让 conan 的自动 DESTDIR 完成落位（`<pkg>/bin`、`<pkg>/share/...`）。

## 判别与信号

- 判别环境：读设备/CI 上 conan 的 `tools/gnu/autotools.py` install() 是否
  注入 DESTDIR，`autotoolstoolchain.py` 默认 prefix 是否为 "/"
- 特征信号：打包后包根出现 `storage/` 目录 = 此坑
- 用 `autotools.configure()` 默认路径的配方天然安全（tc 默认 prefix=/）
