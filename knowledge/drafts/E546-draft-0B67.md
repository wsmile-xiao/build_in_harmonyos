# E546 — 上游测试宏把测试与基准可执行文件装进 `share/`，纯库包必须在 `package()` 中裁剪

## 错误特征

`conan create` 打包阶段出现：

```
<name>/<ver>: package(): Packaged 1 '.1' file: PerformanceTest-1.1.1
<name>/<ver>: package(): Packaged 2 files: PerformanceTest, LICENSE
```

包内出现可执行文件：

```
<pkg>/share/osmscout/tests/<52 个测试程序>
<pkg>/share/osmscout/demos/PerformanceTest-1.1.1
```

## 触发条件

- 构建系统: cmake
- 阶段: installation（`cmake --install` / `CMake(self).install()`）
- 上游形态: 测试宏里带 `install(TARGETS <test> RUNTIME DESTINATION share/<pkg>/tests ...)`

## 根因分析

上游为了"`make install` 后仍能跑测试"，把测试夹具可执行文件一并安装：CMake 测试宏里普遍写成

```cmake
install(TARGETS ${_name}
        RUNTIME DESTINATION share/${pkg}/tests
        BUNDLE  DESTINATION share/${pkg}/tests ...)
```

基准/示例则走 `share/<pkg>/demos`。于是一个纯库包在 `cmake --install` 之后混进几十个可执行文件。在 OHOS 上这有两个后果：

1. 这些文件**不能直接运行**（未签名），对消费者毫无价值；
2. 纯库包被判定为"混装应用"，触发软件级 `commands.json` 要求（R38 的包类型判定），并与 PF9 的单包/单目录闸冲突。

## 解决方案

### 推荐方案

保留 `BUILD_TESTS=ON` 让上游套件在 `build()` 里**真实执行**（Conan 2 的 `conan create` 不调用主配方 `test()`，套件必须放 `build()`），但在 `package()` 的 `cmake.install()` 之后递归删除测试与基准目录：

```python
for sub in ("tests", "demos"):
    extra_dir = os.path.join(self.package_folder, "share", "osmscout", sub)
    if os.path.isdir(extra_dir):
        rm(self, "*", extra_dir, recursive=True)
        os.rmdir(extra_dir)
```

只保留库、头文件与运行期数据（如样式表）。

### 备选

若上游提供 `INSTALL_TESTS=OFF` 一类开关可优先用开关；没有开关时用上面的 `package()` 裁剪，避免改动上游 `CMakeLists.txt`。

### 禁止做法

- ❌ 把测试可执行文件当交付物入库或打包（`git add -f`、手工 `packaging/*.tar.gz`）。
- ❌ 为规避包类型判定而伪造软件级 `commands.json`。

## 验证

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 2>&1 | grep Packaged
find <pkg> -type f -perm -u+x      # 期望为空
```

## 关联条目

- 相似: E506（包内混入非交付物）
- 原则: P005（遵循上游风格，改动最小化）
- 实证: libosmscout 2024.06.02.1（`osmscout_test_project` 宏把 69 个测试/基准装进 `share/osmscout/tests|demos`）
