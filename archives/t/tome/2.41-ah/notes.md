# tome 2.41-ah OHOS 适配记录

## 任务

- 平台任务 `contrib-11215`，`tome 2.41-ah`，`taskBranch=feat/tome-2.41-ah`。
- 路径 A（普通积分赛）。

## 源码

- Debian orig：`https://deb.debian.org/debian/pool/non-free/t/tome/tome_2.41-ah~0.git.20200131.orig.tar.gz`
- `sha256 = d031a3a89cce0f379d92ddaf9d53b4aae6ee0c47b81aaf3b0d700b2ab0375385`
- 官方上游为 `github.com/tome2/tome2`，但**无 `2.41-ah` 标签**（该串为源码内版本），
  且 Debian 快照把 `vendor/` 子模块（fmt/jsoncons/pcg-cpp/bandit/CppQuickCheck）
  内容一并打包；GitHub codeload 归档不含子模块 → 采用 Debian orig。
- 注意：orig tarball 同时含 `vendor/fmt`→`fmt-4.1.0` 等**符号链接**与真实目录；
  Windows 解压会丢掉符号链接，Linux/CI 正常。

## 构建方案

上游为 CMake C++17 工程，核心是 `game`（110 个 .cc）与 `squelch` 两个静态库，
X11/GTK2/ncurses 前端由 `FIND_PACKAGE` 自动探测。配方：

```sh
cmake -DCMAKE_DISABLE_FIND_PACKAGE_X11=TRUE \
      -DCMAKE_DISABLE_FIND_PACKAGE_GTK2=TRUE \
      -DCMAKE_DISABLE_FIND_PACKAGE_Curses=TRUE \
      -DCMAKE_BUILD_TYPE=Release
cmake --build . --target harness
```

- 依赖：`boost/1.85.0`（system、filesystem）。**必须显式 `CMakeDeps(self).generate()`**，
  否则 `find_package(Boost)` 落到系统模块模式：`Boost_FOUND` 为假、`Boost_INCLUDE_DIRS`
  为空，编译期报 `boost/optional.hpp not found`（实测第一轮失败原因）。
- 补丁（`patches/`）：
  1. `0001-init1-add-cstdio.patch`——`init1.hpp` 用 `FILE` 未包含 `<cstdio>`（Debian 已有同款）。
  2. `0002-squelch-condition-add-map.patch`——`squelch/condition.cc` 缺 `<map>`（Debian FTBFS 同款）。
  3. `0003-cppquickcheck-random-shuffle-cxx17.patch`——vendored CppQuickCheck 用了 C++17 已移除的
     `std::random_shuffle`，改为 `std::shuffle(..., rng)`（`RngEngine = std::mt19937` 已在作用域内）。

## 上游测试

- `src/harness`（Bandit BDD），链接 `game`+`squelch`，无需显示。
- 运行：`harness --reporter=spec` → **Test run complete. 44 tests run. 44 succeeded.**
- `build()` 内实跑并断言输出含 `Success!`，失败即报错。

## 消费者测试

`test_package/test_tome.cpp`：包含已安装的 `flag_set.hpp`/`grid.hpp`，16 项断言
（位集合 tier/index 语义、布尔/相等/交并/count、`grid` 尺寸与元素访问）。
消费者编译需带上 Boost 头文件目录（tome 公共头 `#include <boost/...>`），
故 test_package 汇总所有依赖的 includedirs。

## 结果

- 真机 `conan create` 退出码 0。
- 上游 44/44、消费者 16/16。
- 产物：`lib/libgame.a`、`lib/libsquelch.a`、298 个 `.hpp`。
