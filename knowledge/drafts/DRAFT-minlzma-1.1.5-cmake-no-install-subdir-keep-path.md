# DRAFT-minlzma-1.1.5-cmake-no-install-subdir-keep-path：CMake 无 install 规则时的 package() 子目录收集

> Contributor: pc4-37 | Status: Draft | Updated: 2026-09-23
> Source: minlzma 1.1.5 适配（Path B 知识库扩展）；触发场景：`conan-verify` G2 test_package 阶段
> 对应：`knowledge/drafts/DRAFT-minlzma-1.1.5-cmake-no-install-subdir-keep-path.kv`

## 现象

`conan create` 主包构建成功，但 test_package 的 CMake configure 报错：

```text
Conan: Target declared 'minlzma::minlzma'
CMake Error at .../cmakedeps_macros.cmake:81 (message):
  Library 'minlzlib' not found in package.
```

## 根因

上游 `minlzlib/CMakeLists.txt` 用 `add_subdirectory` 构建，产物在 build 目录的
`minlzlib/` 子目录（`build/.../minlzlib/libminlzlib.a`）；且**上游工程没有任何
install() 规则**（`grep -rn "install(" CMakeLists.txt` 为空），`cmake.install()`
不产出任何东西。配方 package() 若从 `self.build_folder` 根目录 `copy("*.a", ...)`，
保留相对路径后产物落在 `lib/minlzlib/libminlzlib.a`，而 CMakeDeps 按
`cpp_info.libdirs=["lib"]` 在 `lib/` **根目录**找库 → 找不到。

**陷阱**：库在包里"存在但不在地上"——不是缺产物，是路径层级错位。

## 修复（已验证）

```python
def package(self):
    lib_dir = os.path.join(self.package_folder, "lib")
    bin_dir = os.path.join(self.package_folder, "bin")
    copy(self, "minlzma.h", src=self.source_folder,
         dst=os.path.join(self.package_folder, "include"))
    # 上游产物在 build 子目录：显式源子目录 + keep_path=False 平铺
    copy(self, "*.a", src=os.path.join(self.build_folder, "minlzlib"),
         dst=lib_dir, keep_path=False)
    copy(self, "*.so*", src=os.path.join(self.build_folder, "minlzlib"),
         dst=lib_dir, keep_path=False)
    copy(self, "minlzdec", src=os.path.join(self.build_folder, "minlzdec"),
         dst=bin_dir, keep_path=False)
```

验证证据：修复后 conan-verify G1-G5 全 PASS；test_package CTest 2/2
（test_minlzma 消费者 + test_ohos 鸿蒙专项）通过；独立消费者程序编译链接运行 OK。

## 适用边界

- 适用：上游无 install() 规则、产物落在 build 子目录的 CMake 库。
- 反例：上游有 install() 规则的库，优先 `cmake.install()`，不需要手动 copy。
- 判断标准：`grep -rn "install(" <src>/CMakeLists.txt` 为空 + `find build -name '*.a'`
  确认产物子目录位置。

## 验证结果

| 项目 | 结果 |
|---|---|
| 修复后 conan-verify | G1-G5 全 PASS ✅ |
| test_package CTest | 2/2 通过 ✅ |
| 独立消费者 | 编译链接运行 OK ✅ |