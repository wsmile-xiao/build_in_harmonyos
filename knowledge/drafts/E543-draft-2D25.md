# E543 草稿：OHOS CMake 无 sysroot → ECM FindInotify 静默失败

## 现象

baloo 6.28.0 conan create（BUILD_TESTING=ON）configure 全绿，但 build() 里的
ctest 报 "No tests were found!!!"；CMakeCache 中 Inotify_INCLUDE_DIRS 为空，
FeatureSummary 显示 "Inotify ... not been found"。

## 根因

- OHOS clang 包装器自带隐式 sysroot（编译 sys/inotify.h 成功），但 conan
  CMakeToolchain 对 os=OHOS 不设置 CMAKE_SYSROOT/CMAKE_FIND_ROOT_PATH。
- ECM FindInotify 用 find_path(sys/inotify.h) 探测，默认搜索路径不含 SDK
  sysroot → Inotify_FOUND=FALSE。
- 上游用 BUILD_KINOTIFY 门控 file/tools/autotests/tests 四个子目录 → 全部
  静默不构建，测试树零注册。

## 修复

conan_cmakedeps_paths.cmake 注入 SDK sysroot usr 前缀（glob 探测，版本无关）：

```cmake
list(PREPEND CMAKE_PREFIX_PATH "<sysroot>/usr")
list(PREPEND CMAKE_INCLUDE_PATH "<sysroot>/usr/include")
```

修复后 Inotify_FOUND=TRUE、BUILD_KINOTIFY=TRUE，33 项上游 ctest 注册并执行
（baloo 6.28.0 实测）。

## 判别要点

- 编译能过但 ctest "No tests were found"：查 CMakeCache 的 Inotify_INCLUDE_DIRS
  / <Feature>_FOUND。
- KDE 包的 "optional 依赖未找到" 经常是门控（BUILD_KINOTIFY/BUILD_XXX），
  后果是整棵子树（含测试）不构建，不是简单降级。
