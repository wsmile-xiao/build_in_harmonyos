# fastmod 0.1.0 适配笔记

## 编译环境
- 构建系统: CMake（上游同时提供 Makefile）
- 编译日期: 2026-09-03
- 编译器: 本地 Apple clang 21；设备验证使用 OHOS clang 15.0.4、libc++、C++17
- 目标平台: HarmonyOS HongMeng Kernel 1.12.0 aarch64，Conan profile `OHOS 6.0`
- 状态: built（设备验证通过，等待 CI 与 PR 闭环）
- 上游 tag: `v0.1.0`
- 上游 commit: `fa0c0a1624fcc9a41e36a693b12fd987cb4feedb`
- 源码归档 SHA-256: `b80e759208d6b4318caa14b1851352c69e8c7a1f7895639e3af1d86944d2973b`

## 编译步骤

1. 读取 GitHub 官方 `v0.1.0` 标签并下载官方 tarball。
2. 盘点 `CMakeLists.txt`、`tests/CMakeLists.txt` 和 `Makefile`：默认 CMake
   注册 2 个 CTest benchmark；`FASTMOD_EXHAUSTIVE_TESTS=ON` 才追加
   `cppincludetest2`，Makefile 另行构建 `unit` 和 `cppincludetest2`。
3. Conan 配方使用 `package_type="header-library"`，通过上游 CMake 安装头文件和
   CMake package metadata，`package_info()` 不声明库文件。
4. `build()` 执行 CMake configure/build 后运行
   `ctest --output-on-failure`；`test_package` 直接运行真实 API 消费者。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make -n check` 报 `No rule to make target 'check'` | 上游 Makefile 没有 `check` 目标；测试入口由 CMake/CTest 管理 | 配方按上游 CMake 测试入口执行 CTest，并在 MANIFEST 中如实声明 |
| 2 | 默认 CMake 测试不覆盖 `unit.c`/完整域穷举 | 默认 CTest 只有 2 个 benchmark；Makefile `all` 另外构建 `unit` 和 `cppincludetest2`，而 exhaustive 选项只会把后者注册为第 3 个 CTest | 单独编译并实际尝试运行两个 Makefile 程序；它们未在限定验证窗口完成，不计为通过或失败 |
| 3 | 上游 Makefile 默认编译器不可用 | Makefile 第 16、19、22 行使用 `$(CC)`/`$(CXX)`；设备默认 `cc` 不存在，`make -j1 unit cppincludetest2` 返回 2，日志含 `make: cc: No such file or directory` 和 `Error 127` | 使用设备已存在的 `/data/service/hnp/bin/clang` 与 `clang++`，执行 `make CC=clang CXX=clang++ -j1 unit cppincludetest2`，返回 0；两个可执行文件均生成 |
| 4 | `unit` 与 `cppincludetest2` 未在 120 秒内完成 | 这是源码可执行但规模极大的完整域验证，不是链接、运行时或 OHOS 特性错误：`unit` 首段进入 `testunsigned(1,8)` 后每个 divisor 遍历 `2^32` 个 dividend；`cppincludetest2` 首个调用遍历 8 个 divisor，每个遍历完整 `int32_t` 域，即 `8 × 2^32 = 34,359,738,368` 次除法/fastdiv 检查。两者无失败输出，均由 `timeout` 返回 124 | 记录为“已尝试、未完成”：`timeout 120 ./unit` 日志 60,889 字节、SHA-256 `c46abbb9b455fce16cad7fdc6284cd7baad6fb821264833c56651b6c513548f7`；`timeout 120 ./cppincludetest2` 日志为单个换行、SHA-256 `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b`。不把超时伪报为通过，也不把未观察到断言失败写成失败 |
| 5 | 探索性消费者测试的负除数 `fastmod<-5>` 失败 | 上游模板将负模板参数直接传给要求正除数的 `fastmod_s32`；不是 OHOS 特性，官方测试也不覆盖该模板用法 | 不改变上游源码；消费者测试使用文档约定的正除数模板和显式正绝对值参数 |

## 源码修改

无。上游源码未修改，`patches/` 不存在。

## 依赖版本

无外部 Conan 依赖；仅使用 OHOS profile 中的 clang 15、CMake 和 CTest。

## 验证结果

```bash
make -j1                         # 本地上游 Makefile 编译：通过
make -j1 benchmark                # 本地 benchmark 编译：通过
make -n check                     # 预检：无该目标（上游无 make check）
clang++ -std=c++11 -Wall -Wextra \
  -I /private/tmp/fastmod-v0.1.0/include \
  archives/f/fastmod/0.1.0/test_package/test.cpp \
  -o /private/tmp/fastmod-consumer-test && /private/tmp/fastmod-consumer-test
# 本地消费者 API 编译运行：通过（11 个显式 API 检查，`-DNDEBUG` 下仍执行）

远端设备使用仓库 profile 的绝对路径执行，避免 Conan 将同名缓存 profile 当作输入：

```bash
conan create "$HOME/ws/wt-fastmod-0.1.0/archives/f/fastmod/0.1.0" \
  --user=ohpcd --channel=stable \
  -pr:h="$HOME/ws/wt-fastmod-0.1.0/ci/conan/profiles/ohos-aarch64" \
  -pr:b="$HOME/ws/wt-fastmod-0.1.0/ci/conan/profiles/ohos-aarch64" \
  --build=missing
```

- 远端源码构建与安装：通过；生成 header-only 包及 CMake target `fastmod::fastmod`。
- 默认上游 CTest：2/2 通过（`moddivnbenchmark`、`modnbenchmark`），0 失败。
- Conan `test_package`：1/1 通过，真实执行 `test_fastmod`，11 个显式 API 检查全部通过。
- 上游测试入口逐项统计：默认 CTest 2 个（`moddivnbenchmark`、`modnbenchmark`）均通过；
  `FASTMOD_EXHAUSTIVE_TESTS=ON` 的第 3 个 CTest（`cppincludetest2`）已编译并尝试运行，
  120 秒后返回 124；Makefile `all` 的 `unit` 也已编译并尝试运行，120 秒后返回 124。
  两项均为“已尝试、未完成”，不是失败，也不计入通过数。
- 设备 Makefile 复核：默认 `make -j1 unit cppincludetest2` 因 `cc` 缺失返回 2；使用
  `make CC=clang CXX=clang++ -j1 unit cppincludetest2` 返回 0。构建日志为
  `$HOME/tmp/fastmod-0.1.0/upstream-make-build-clang.log`。
- `unit` 实跑日志：`$HOME/tmp/fastmod-0.1.0-unit-run.log`，120 秒返回 124，
  60,889 个进度点对应已进入的 divisor 循环；`cppincludetest2` 实跑日志：
  `$HOME/tmp/fastmod-0.1.0-cppincludetest2-run.log`，120 秒返回 124，首个源码调用
  即 8 个高位 divisor × `2^32` 个 dividend，输出尚未到达其每 10,000 个 divisor 的进度点。
- 设备完整日志：`$HOME/tmp/fastmod-0.1.0/conan-create-audit-fix.log`。
- 该日志 SHA-256：`1ee7cfad6f83f935183307689010cba790a7dc71c3dce4bb4817afe4a8e38d97`。
```

## 注意事项

- `ctest -N` 的目标数不等于断言数；PR 测试表分别记录 2 个默认上游 CTest
  目标、0 个默认运行的 exhaustive 目标和 1 个消费者测试目标。
- 版本目录外存在官方仓库已有的 `archives/l/libXext` 与
  `archives/l/libxext` 大小写碰撞；fastmod 实际构建输入不读取该范围，按工作区
  规则作为无关例外保留。

本次远端构建对应提交：`63c5ededf4012888ddda6a177c65776b7479154d`。
本次 Makefile 测试复核使用设备端任务目录 `$HOME/tmp/fastmod-0.1.0-make.Almqjj`，
源码来自 Conan `source` 缓存；上游 Makefile SHA-256 为
`fb58d2f9f4f83c7fa8a05614384a018326ddff1e6c94398a305f2ea5145d081e`，
`unit.c` SHA-256 为 `b7266e61ff605361558616e5d6bd1de8b4ba5151f93b56278f631b6740002ee0`，
`cppincludetest2.cpp` SHA-256 为
`ee52a93aa965c3361a2b786ad6d28a100f4c64542853a1bd9c16f6902b84cfe4`。
