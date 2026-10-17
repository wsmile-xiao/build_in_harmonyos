# tome

`tome` 是 roguelike 游戏 **Tales of Middle Earth**（Angband/Moria 衍生版）。
本适配打包其**平台无关的游戏引擎核心**：CMake 目标 `game` 与 `squelch`
（静态库），以及全部公共 C++ 头文件；三个显示前端（X11 / GTK2 / ncurses）
只是薄驱动层，通过 `CMAKE_DISABLE_FIND_PACKAGE_*` 关闭后即可完全无头构建。

## 适配要点

- **上游无 `option()`**：前端靠 `FIND_PACKAGE(X11/GTK2/Curses)` 自动探测；禁用三者即得无头引擎 + 测试。
- **强制依赖 Boost（system、filesystem）**；`fmt`/`jsoncons`/`pcg-cpp`/`bandit`/`CppQuickCheck` 均已随快照的 `vendor/` 提供（头文件为主）。
- 补丁 3 个：`<cstdio>`、`<map>` 两处缺失头，以及 vendored CppQuickCheck 的 `std::random_shuffle`（C++17 已移除）改为 `std::shuffle(rng)`。
- 源码取自 Debian 同版本 orig tarball：官方 GitHub 无 `2.41-ah` 标签，且 Debian 快照把 `vendor/` 子模块内容一并打包（含符号链接）。

## 上游测试

`src/harness` 是上游 Bandit 测试套件，仅链接无头核心，`harness --reporter=spec`
输出 `Test run complete. 44 tests run. 44 succeeded.`（即 44 项）。

## 消费者测试

`test_package/test_tome.cpp`：对已安装头文件 `flag_set<>` / `grid<>` 做 16 项断言。

## 产物

| 路径 | 说明 |
|---|---|
| `lib/libgame.a` | 游戏引擎核心 |
| `lib/libsquelch.a` | squelch（物品筛选规则）库 |
| `include/*.hpp`、`include/tome/**` | 公共 C++ 头文件（298 个） |

## 参考资料

- 上游：<https://github.com/tome2/tome2>
