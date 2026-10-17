# tina 0.1.14 知识召回报告

> 来源：build_in_harmonyos upstream/main 知识库（2026-09-19 同步，commit 8f56191952）。
> 召回目的：动手适配前复用已有结论，减少重复踩坑。

## 1. 目标库画像

- **tina**：个人事务管理器（personal information manager），curses 界面 + 短文本条目分类。
- 上游：https://devel.ringlet.net/misc/tina/ ，源码 https://gitlab.com/tina-mgr/tina-mgr
- 构建系统：autotools（configure.ac + Makefile.am），`AC_CHECK_LIB(curses, initscr)`
- C 源码约 1653 行，依赖极小：仅 curses。
- 测试入口：无 C 侧测试（Makefile.am 无 `TESTS`/`check_PROGRAMS`）；上游测试全在 Python 侧（tests/python/unit + tox pytest）。

## 2. 依赖拓扑（W0 结论）

```
目标库 C：tina/0.1.14
└── 依赖库 A：ncurses（curses，initscr）
```

- `conan search ncurses -r ohpcd` → Recipe not found（2026-09-19，匿名）
- `conan download tina/0.1.14 --only-recipe -r ohpcd` → Recipe 'tina' not found
- **结论**：tina 不在 ohpcd；ncurses 已在仓库内适配（archives/n/ncurses/6.5，conan create PASS），
  tina 配方 `requires ncurses/6.5` 即可消费。

## 3. 命中知识条目

| 编号 | 命中理由 | 结论（已读全 kv+doc） |
|---|---|---|
| **E277** | ncurses 未发布 ohpcd + 无配方 | vendored-to-staging：build() 内 configure ncurses 静态库 install 到 staging，主库 -I/-L 指向 staging |
| **E033** | curses/musl 宽字符 | musl 下 ncurses 宽字符接口（cchar_t/setcchar）需 `_XOPEN_SOURCE_EXTENDED -D_XOPEN_SOURCE=600` |
| **E028** | ncurses 系统库冲突 | 静态链接 + 静态 install 可规避；conan package 仅装 .a + 头文件 + man，不覆盖系统 .so |
| **OHOS 沙箱 umask** | config.status 临时目录 077 不可写 | configure 内 `umask 077` → `umask 022`（tina 配方 source() 内 inline patch） |

## 4. 非条目知识（operations / 归档 / requirements）

- `knowledge/operations/ohos-adaptation-patterns.md`：无 ncurses 专项段落。
- 同库归档：archives/t/ 无 tina 目录（首次适配）。
- `knowledge/requirements/`：R001/R002 与 ncurses 无关。
- **同类案例**：E277 正文点名 tmate/libssh+msgpack+ncurses 为典型——tina 属同类（curses 终端类工具）。

## 5. 横向 PR 检索

目标仓库已合并 PR 中无 tina / ncurses 适配记录（archives 无目录，git log 无相关 commit）。
**记录：未找到可复用 PR，需自建。**

## 6. 适配路线（基于召回）

1. **ncurses（依赖）**：仓库已有 archives/n/ncurses/6.5，conan create PASS（2026-09-19 验证），
   tina 配方直接 `requires ncurses/6.5` 消费。
2. **tina 本体**：autotools 交叉编译，`AC_CHECK_LIB(curses, initscr)` 需通过
   - `-I<ncurses_include> -L<ncurses_lib>` 注入 CPPFLAGS/LDFLAGS（generate() 内 Environment）
   - `libcurses.a` 符号链接桥接（configure 探测 -lcurses，ncurses 提供 libncursesw.a）
3. **测试**：上游 C 侧无自动化测试入口 → test_package 交叉编译仅验证 bin/tina 产物存在；
   上游 Python 单测（tests/python/unit + tox）在 OHOS 目标环境无 Python 运行时，不执行。
4. **平台风险**：curses 终端程序在 OHOS aarch64 musl 上运行模型未知（无 ptrace 需求，风险低）；
   /tmp 只读（已知环境坑，用 $HOME/tmp）。

## 7. 待办挂接

- 任务 #7：tina 本体适配（target-library-adaptation 模板）— 已完成（conan create PASS）
- 任务 #9：积分赛事 PR 提交
