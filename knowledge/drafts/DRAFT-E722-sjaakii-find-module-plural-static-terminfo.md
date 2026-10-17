# DRAFT-E722 — CMake 自带 Find 模块的单复数变量错配与静态 readline 的 terminfo 并链

- 任务: sjaakii 1.4.1（任务卡 10659，feat/sjaakii-1.4.1）
- 门禁: G2 conan create（configure + link）
- 状态: DRAFT（E722 已取号占位，待评审晋升）

## 现象

1. **configure**: `#include <readline/readline.h>: No such file or directory`（HAVE_READLINE 分支）。
2. **link**: `undefined reference to 'tgetent' / 'tgetflag' / 'tgoto' / 'tputs'`（以及 `BC`/`PC`/`UP` terminfo 变量）。

两条在常规 Linux 发行版开发机上都不可复现（系统前缀掩盖 + 动态链接掩盖）。

## 根因（两缺陷叠加）

| # | 缺陷 | 系统前缀下的表现 | 非系统前缀/静态下的表现 |
|---|------|------------------|------------------------|
| 1 | `FindReadline.cmake` 只 `set(READLINE_INCLUDE_DIR ...)`（单数），消费方 `CMakeLists` 用 `${READLINE_INCLUDE_DIRS}`（复数） | `/usr/include` 恒可达，空值无害 | conan 包目录 include 丢失 → 找不到头 |
| 2 | `libreadline.a` 未定义 terminfo 后端符号，在 ncurses 里 | 动态链接由 libreadline.so 的 DT_NEEDED 自动带上 | 静态库必须显式并链 ncurses |

`nm` 实证：
```bash
nm -u .../readl*/p/lib/libreadline.a | grep -E 'tgetent|tgoto|tputs'   # U tgetent U tgoto U tputs ...
nm -g --defined-only .../ncur*/p/lib/libncursesw.a | grep ' T tgetent' # HAS tgetent
```

## 修法（sjaakii 补丁 0001+0002）

```cmake
# FindReadline.cmake — 对齐消费方变量名
set(READLINE_INCLUDE_DIRS ${READLINE_INCLUDE_DIR})

# CMakeLists.txt — 静态 readline 并链 terminfo 后端（顺序：readline 在前 ncurses 在后）
find_package(Readline)
if (READLINE_FOUND)
   target_link_libraries("sjaakii" ${READLINE_LIBRARY})
   find_library(NCURSES_LIBRARY NAMES ncursesw ncurses)
   if (NCURSES_LIBRARY)
      target_link_libraries("sjaakii" ${NCURSES_LIBRARY})
   endif()
   ...
```

conan toolchain 已把依赖包目录前置进 `CMAKE_LIBRARY_PATH`/`CMAKE_INCLUDE_PATH`，
`find_library`/`find_path` 直接命中，无需手写绝对路径。

## 验证

```bash
nm -g --defined-only "$(conan cache path ncurses/6.6 | sed 's|/e$|/p|')/lib/libncursesw.a" | grep ' T tgetent'
printf 'test movegen\nquit\n' | sjaakii   # → Ok.（链接与运行双通过）
```

## 禁则

- 禁改静态链接顺序或加 `--as-needed` 剪枝（readline→ncurses 顺序敏感）。
- 禁写死 `/usr/include/readline` 之类系统前缀（worker 上无系统 readline，必假绿失败）。

## 关联

- 相似: E321（CMake 4.x policy，同属"上游 CMake 元老项目在现代工具链下的配置期断裂"族）
- 先例: fcl-0001-libm-optional-on-musl（find_library 落空守卫，同补丁内一并处理 M_LIB）
