# DRAFT: 已发布 KF6 包的相对路径 DT_NEEDED 在 OHOS musl 下按 cwd 解析，须以构建树 shim 目录满足 ctest 运行

## 错误特征

```
Error loading shared library ../../bin/libKF6ConfigCore.so: (needed by .../libKF6ConfigGui.so)
Error loading shared library ../bin/libalkimia6.so: (needed by ./alkvaluetest)
Error relocating ./bin/alkvaluetest: <symbol> symbol not found
```

- 触发场景：下游包在自己的 conan 构建树里运行 ctest / conan test()，加载
  链上任何一个库（含已发布依赖包的二级库）带相对路径 NEEDED。
- 特征：LD_LIBRARY_PATH 已经包含所有依赖包的 lib/ 目录仍无效——musl 对
  带路径的 NEEDED 不查 LD_LIBRARY_PATH。

## 根因

1. kconfig 6.18.0、knewstuff 6.29.0.1 等已发布 KF6 包，其二级库
   （libKF6ConfigGui.so 链 libKF6ConfigCore.so）的 DT_NEEDED 是发布包构建
   时链接器记录的构建树相对路径（../../bin/libKF6ConfigCore.so——上游
   KDEInstallDirs 把库装 bin/ 的布局）。
2. OHOS musl 动态加载器解析含 "/" 的 NEEDED 时以**进程 cwd** 为基准，不
   走 LD_LIBRARY_PATH/RPATH。
3. 下游 ctest 的 cwd 是 build_folder（conan cmake_layout），`../../bin/`
   解析到构建树外的不存在路径 → 加载失败。
4. 下游不能修改已发布依赖包的 ELF（制品只读），只能在自身构建环境里
   "摆好"该相对路径期待的位置。

## 解决方案（shim 目录）

在测试执行前，把所有依赖包 lib/（含自身构建产物）的 lib*.so* 软链到
`build_folder/../bin/`（ctest cwd 视角下 `../../bin/` 的落点）：

```python
compatibility_bin = os.path.normpath(
    os.path.join(self.build_folder, os.pardir, "bin"))
os.makedirs(compatibility_bin, exist_ok=True)
# 收集 self.build_folder/bin + 每个 dep.package_folder/lib 的 lib*.so*
# 逐个 symlink（OSError 时 copy2 实体复制兜底）
```

test_package 场景：conan 2.29 的 test() 以 cwd=test_package 的 build
folder 运行 `./test_package`，相对 NEEDED 解析到 test_package 源目录的
`../../bin/`（即版本目录旁的 bin/）——shim 同理落在该位置。另注意 test()
阶段 conan Environment 的 vars 注入对 self.run 的裸 shell 不生效，
LD_LIBRARY_PATH/QT_QPA_PLATFORM/TZ 须直接写 os.environ。

## 与 E019/E537 的边界

- E019（LD_LIBRARY_PATH）：适用于"找不到裸 basename 库"；本场景带路径的
  NEEDED 绕过 LD_LIBRARY_PATH，E019 方案无效。
- E537（链接期 SONAME 基名化 + patchelf 清扫）：适用于**本包产物**的
  NEEDED 治理；本场景是**已发布依赖包**自带的相对 NEEDED，下游无法重写
  依赖包 ELF——shim 是唯一解。两者互补：本包产物用 E537 链接期治理，
  依赖包遗留相对 NEEDED 用本条 shim。

## 红线

- 不要试图在 package() 后 patchelf 修改依赖包的库（改不了，依赖包不在
  你的 package 里）。
- 不要把 shim 软链提交进 git（conan create 每次运行会重新生成；提交进
  PR 会触发 JC3 二进制拦截——清理 test_package/bin 再提交）。
- test() 里用 os.environ 而非 conan Environment（2.29 实测不生效）。

## 实证

- alkimia 8.2.1（PR !9350）：12 项上游测试在无 shim 时全部加载失败；
  加 shim 后 9/12 通过（3 项网络豁免），CI 构建 #43546 绿。
- 先例：knewstuff 6.29.0.1 conanfile.py `_prepare_ctest_runtime_links`。
