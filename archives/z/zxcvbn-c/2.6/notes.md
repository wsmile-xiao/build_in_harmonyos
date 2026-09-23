# zxcvbn-c 2.6 HarmonyOS 适配笔记

## 任务信息

- Issue：待补。当前项目和会话上下文未找到明确编号。
- 分支：`feat/zxcvbn-c-2.6`
- Worktree：`D:\harmonyos\worktrees\zxcvbn-c`
- 上游：`https://github.com/tsyrogit/zxcvbn-c`，标签 `v2.6`

## W0 依赖检查

- `conan search zxcvbn-c/* -r=ohpcd` 未发现已发布的同名配方。
- 上游 CMake/源码只依赖 C/C++ 编译器和数学库；没有需要拆分的 Conan 依赖。
- `libm` 在 Linux/OHOS 上作为系统库由 `package_info()` 声明。

## 源码与构建系统

- 同时存在 CMake 和自定义 Makefile；本配方采用 CMake。
- CMake 在构建时编译 `dict-generate.cpp`，生成 `dict-src.h`、`dict-crc.h` 和 `zxcvbn.dict`。
- 上游没有 `install()` 规则，配方从 CMake build 目录复制 `zxcvbn.h` 与所选静态/共享库。
- `cmake --build --target test` 覆盖内部键盘数据检查、C/C++ 内嵌/文件词典测试，以及静态/共享库消费者。
- 上游项目版本字段为 `0`，不作为 Conan 包版本来源；包版本按任务要求固定为 `2.6`。

## OHOS 补丁

- `0001-ohos-libm-optional.patch`：OHOS 没有可由 CMake `find_library(m)` 找到的独立 `libm` 文件；找不到时将 `LIBM` 置空，使用系统 C runtime 提供数学符号。
- 真机并行构建会因上游对多个目标重复声明同名 `dict-src.h`/`dict-crc.h` 生成规则而竞态写文件，导致 clang 读取半写入头文件并报 `source file is not valid UTF-8`/退出 139；配方固定使用 `-j1`。
- 上游 `test` 自定义目标无参数运行测试程序，其中 `test-file` 等会从 stdin 读取密码，Conan 非交互 stdin 会使其挂起。配方改为显式执行同一组 7 个测试程序，其中 6 个传入 `-t testcases.txt`，避免交互等待。
- `test-shlib` 运行时需要从构建目录加载 `libzxcvbn.so`；配方仅为该测试显式加入构建目录 `LD_LIBRARY_PATH`，静态库测试不注入运行时路径。

## 本机验证

- 已下载并校验源码包：SHA256 `11e39f6776f9c82c68b2acb94336e32697d4ab6cdb4ac16f9583ccbdd735113a`。
- 已完成源码清单、CMake/Makefile 分析和 Conan 配方静态审阅。
- Windows 本机缺少 `cmake`/OHOS clang，且 MinGW C++ 标准库缺少 `bits/stl_iterator.h`；真机已完成源码下载、CMake 配置和单线程完整上游构建验证；显式 `-t` 测试正在按更新配方重跑。

## 下一步真机 / shadow CI

```sh
CI_PACKAGES="archives/z/zxcvbn-c/2.6" zsh ci/conan/build_and_test.sh
```

真机隔离 runner 中使用项目 OHOS profile/settings，并单独设置 `TMPDIR=$RUN_DIR/tmp`；建议先执行：

```sh
conan create archives/z/zxcvbn-c/2.6 --user=ohpcd --channel=stable \
  -pr:h="$HOME/.conan2/profiles/ohos" -pr:b="$HOME/.conan2/profiles/ohos" \
  --build=missing
```

重点观察：词典生成器能否在 OHOS 上执行、共享库测试的运行时库搜索路径、以及 7 个显式非交互上游测试目标。真机单包已完成；issue 编号和最终 PR 信息仍待补。

本轮隔离 job `zxcvbn-c-2.6-20260914` 中，首次并行 `conan create` 在 `cmake.build()` 阶段失败；随后对同一构建目录执行 `cmake --build build/Release -- -j1`，静态/共享库及 7 个上游测试目标全部构建成功。更新配方改用显式非交互测试后，真机 `conan create` 退出码为 0，7 个上游测试、打包和 `test_package` 消费者测试均通过。Issue 编号仍待补。
