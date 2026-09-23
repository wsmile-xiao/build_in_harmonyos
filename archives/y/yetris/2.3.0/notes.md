# yetris 2.3.0 适配笔记

## 编译环境
- 构建系统: makefile（上游自带 GNU Makefile，无 cmake/configure）
- 编译日期: 2026-09-20
- 编译器: clang/clang++（profile tools.build:compiler_executables，/data/service/hnp/bin）
- 状态: built

## 编译步骤

conan create 内 build() 执行（全部经 conanbuild env）：

```bash
cd src && make -j1 \
  CC=<profile c> CXX=<profile cpp> \
  CFLAGS_PLATFORM="-I<ncurses>/include -Wno-narrowing" \
  LDFLAGS="-L<ncurses>/lib -lncursesw"
```

上游链接行 `$(CXX) $(OBJECTS) $(COMMANDER_OBJS) -o bin/$(EXE) $(LIBSDIR) $(LDFLAGS)`，
`-L` 与 `-lncursesw` 经 LDFLAGS 进入链接（对象在先，顺序正确）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make 报 `/home/runner/work/ohos-make/.../clang++: not found` | ohpcd hnp make 二进制内置 CI worker 路径的默认 CXX；上游 Makefile 未定义 CC/CXX | 命令行显式传 CC/CXX（取 profile tools.build:compiler_executables） |
| 2 | `libncurses` 链接目标不存在 | ohpcd ncurses 包只提供宽字符构建 libncursesw.a | LDFLAGS 全量覆盖：`-L<pkg>/lib -lncursesw`（免去补丁） |
| 3 | PieceDefinitions.cpp 聚合初始化 `{-2,-3}` 收窄报错 | clang 把 C++11 narrowing 当 error（gcc 仅告警） | CFLAGS_PLATFORM 追加 `-Wno-narrowing`（无源码补丁） |

## 上游测试清点（R51 / 五维账本）

- N_static = **0**：tag 2.3.0 的 Makefile 目标仅 all/run/install/uninstall/clean/dist/doc/docclean，
  无 test/check 目标、无 tests/ 目录、无 CTest/CUnit/check 接线（清点证据：
  `grep -nE '^(test|check)' Makefile` 无匹配）。
- N_consumer = 1（test_package/test_yetris.c：可编译消费者程序，校验二进制存在且可执行 +
  `--version` 打印 "yetris v2.3.0" + `--help` 打印 usage 且列出 `--version`；由 CMake 构建、
  conanfile.py test() 经 self.run() 真实执行。CI L0c 要求 test_package 含可编译测试源，
  原 PR 仅有 inline 断言 → 本提交补 test_yetris.c/CMakeLists.txt 并删除残留 out.txt）。

## 源码修改

无补丁、无源码修改（构建差异全部通过 make 命令行变量覆盖实现）。

## 依赖版本

- ncurses/6.6（ohpcd 制品仓，宽字符静态构建 libncursesw.a）

## 验证结果

```bash
conan create ... -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing
# G2 通过；test_package 消费者测试通过（test_yetris.c 真实执行：--help/--version 输出断言 + 退出码）
```

## 注意事项

- yetris 为全屏 ncurses TUI 游戏，运行需 TERM；消费者测试仅覆盖 CLI 契约
  （--help/--version），不启动游戏画面。
- commander（deps/commander）为上游捆绑的命令行解析单文件库，非系统依赖。
- 任务名"cmake"标注与实际不符：上游 2.3.0 tag 无 CMakeLists，构建系统为 makefile。
---

**编译结束**: 2026-09-20 18:13
**最终状态**: built
