# E-entry 草稿文档 — CMake POST_BUILD 以裸命令名运行产物在 POSIX sh 下 Error 127

配套: `DRAFT-cmake-postbuild-run-artifact-posix-sh-127.kv`
触发任务: boost-ext-ut 2.3.1（PR #8569，archives/b/boost-ext-ut/2.3.1）

## 症状（稳定错误签名）

```
[ 21%] Linking CXX executable boost_ut_runner
Running boost_ut_runner
/bin/sh: boost_ut_runner: inaccessible or not found
make[2]: *** [example/CMakeFiles/boost_ut_runner.dir/build.make:102: example/boost_ut_runner] Error 127
```

识别特征：`Linking CXX executable` 之后紧跟 `Running <target>`，然后 127。

## 根因

上游 CMake 以 option（默认 ON，如 boost-ext-ut 的 `BOOST_UT_ENABLE_RUN_AFTER_BUILD`）
在 `add_custom_command(... POST_BUILD ...)` 中执行刚链接好的可执行文件，`COMMAND`
写**裸命令名**（无 `./` 前缀）。POSIX sh 不在 PATH 中搜索当前目录，Linux/OHOS 必然
Error 127；**Windows cmd 会搜索 cwd，上游 Windows CI 不触发**——这就是默认值能存活、
问题只在 Linux 侧爆发的原因。

## 方案

配方 `generate()` 将该 option 显式设为 OFF/NO，对齐上游全部 CI 工作流
（boost-ext-ut 的 linux/macos/windows/emscripten/install 六个 workflow 均传
`-DBOOST_UT_ENABLE_RUN_AFTER_BUILD=NO`），测试改经 `add_test` 由
`cmake.test()`/ctest 执行。**不要**为绕过而改用 `./<target>` 跑 POST_BUILD
（偏离上游 CI 口径、语义也不同）。

修复验证：conan create 后上游 ctest 4/4 通过（`100% tests passed, 0 failed out of 4`）。

## 适用范围 / 反例 / 解除条件

- 适用：所有在 `POST_BUILD`/custom command 中以裸名或相对路径运行构建产物的
  CMake 项目（常见于测试框架库：boost-ext/ut、doctest 类单头框架的示例自跑）。
- 反例：`COMMAND ./<target>`（显式相对路径）不会触发；`COMMAND $<TARGET_FILE:t>`
  也不会。是"裸命令名"这一种写法的问题。
- 解除条件：上游把默认值改为 OFF 或修正 COMMAND 写法后，配方可跟随上游。
