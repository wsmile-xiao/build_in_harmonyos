# DRAFT-headless-broadway-execute-upstream-gui-sample — 用 broadway 后端在无显示环境真实执行上游 GUI 示例

## 现象 (What happened)

libexif-gtk 0.5.0（GTK3 控件库）适配时，上游测试入口清点结果：

```
$ grep -n '^TESTS\|check_PROGRAMS' Makefile.am tests/Makefile.am libexif-gtk/Makefile.am …
（无输出，exit 1）                      # 上游没有注册任何自动化测试
$ grep -n '^check:' Makefile
805:check: check-recursive
$ make check
Making check in m4m
make[1]: Nothing to be done for 'check'.
... （po / gtk-extensions / libexif-gtk / tests 同样 5 处）
$ echo $?
0                                     # 空跑，不是“测试通过”
$ grep -n 'noinst_PROGRAMS' tests/Makefile.am
1:noinst_PROGRAMS = test-libexif-gtk   # 唯一程序：交互式示例
```

`.travis.yml` 自述 `# There are no automated tests to run`；示例本体是
`gtk_init()` → `gtk_window_new()` → `gtk_exif_browser_new()` → `exif_data_new_from_file(argv[1])`
→ `gtk_main()`，**无断言、无退出码语义**。

直接运行（无显示环境）时：

```
$ ./tests/test-libexif-gtk original.jpg
(test-libexif-gtk:22513): Gtk-WARNING **: cannot open display:
$ echo $?
1
```

→ 看起来“上游测试根本跑不起来”，容易被写成“无测试入口”或错误的“上游无测试覆盖”。

## 根因 (Root cause)

两层原因叠加：

1. **上游形态**：GUI 库以“示例即文档”方式分发，示例是交互式程序而非断言型测试套件，
   因此 `make check` 只能空跑，示例本身也不提供 pass/fail 语义。
2. **运行环境**：CI/容器没有 `DISPLAY`（OHOS PC 也没有 X11 服务器），
   GTK 示例第一句 `gtk_init()` 就因取不到显示而告警退出 —— 这是**环境缺显示后端**，
   不等于“测试不可执行”。

GTK3 自带 **broadway** 后端（HTML5/CSS 渲染，通过 WebSocket 与 `broadwayd` 通信），
本仓 `gtk/3.24.43` 配方正是以 broadway 替代 X11/Wayland（其 conanfile 注释与
`gtk+-broadway-3.0.pc` 可证），且包内自带 `bin/broadwayd` —— 于是无显示环境也能提供显示服务。

## 解法 (Fix)

把上游示例当作**可执行的验证载体**真实跑起来，并用“存活判据 + 负向用例”补足判定能力：

```bash
# 1) 依赖运行环境（conan 生成的聚合 env：全部依赖 lib 目录进 LD_LIBRARY_PATH）
source <deps-build>/conanrun.sh

# 2) 起显示服务（gtk 包自带 broadwayd；:5 → 端口 8085）
export PATH="<gtk-pkg>/bin:$PATH"
broadwayd :5 > broadwayd.log 2>&1 &
sleep 2
export GDK_BACKEND=broadway
export BROADWAY_DISPLAY=:5

# 3) 正向用例：程序无退出码语义 → 用 “timeout 杀死前一直存活” 作为“已进入 gtk_main”的判据
timeout 8 ./tests/test-libexif-gtk <exif.jpg>      # exit 124 = PASS

# 4) 负向用例：覆盖示例显式走到的 g_error 分支（无需显示也可执行）
./tests/test-libexif-gtk                            # g_error "You need to supply exactly one file to load." → exit 133
timeout 8 ./tests/test-libexif-gtk <no-exif.jpg>    # g_error "Could not load EXIF data from '…'"        → exit 133

kill %1
```

结果如实回填到 R51 三处载体：`reports/test-report.md`（逐用例命令/退出码/日志路径）、
`test_package/MANIFEST.yml`（`upstream_tests` 声明 + `upstream_check_command`）、
`notes.md`（上游无自动化测试的结论 + 实测统计）。

## 验证 (Verification)

libexif-gtk 0.5.0 实测（HarmonyOS PC aarch64，GTK3 broadway 后端）：

| # | 用例 | 观测 | 判定 |
|---|---|---|---|
| U1 | 无参数 | `** ERROR **: You need to supply exactly one file to load.`，exit 133 | PASS（上游定义分支） |
| U2 | `original.jpg`（含 EXIF） | 进入主循环，8s 内无退出 → timeout 124 | PASS |
| U3 | `no-fnumber.jpg`（含 EXIF） | 同上 | PASS |
| U4 | `sample-author-badencoding.jpg`（含 EXIF，非法 UTF-8 作者字段） | 同上；Pango 仅告警（该样例固有） | PASS |
| U5 | `no-metadata.jpg`（**无 EXIF**，负向对照） | `** ERROR **: Could not load EXIF data from '…'`，exit 133 | PASS |

**统计：上游自动化测试 0 项；示例程序 5 个用例 5 通过 / 0 失败 / 0 跳过。**
日志：`…-logs/17-upstream-test-broadway-*.log`、`14-upstream-test-entry-*.log`。

配套的 test_package（消费者视角 6 条断言，含 1 条鸿蒙特有用例）**不替代**上述统计（R51）。

## 适用边界 (Applicability / Scope)

- 适用：上游只提供交互式 GUI 示例（`noinst_PROGRAMS` + `gtk_main()`）、无 `TESTS=`/`check_PROGRAMS`
  的 GTK/Qt 桌面库；CI/容器无 `DISPLAY`/`WAYLAND_DISPLAY`；GTK3 且显示后端为 broadway
  （或平台提供了可用的 headless 显示服务）。
- 不适用：断言型测试套件（gtest/ctest/pytest）——直接运行即可，本条的“存活判据”不必要。
- 边界：`timeout` 的“存活即通过”是**弱断言**，只能证明“加载 + 构造 + 解析 ExifData + 进入主循环”
  这条链路无崩溃；真正的字段级断言需在 test_package 里补（libexif-gtk 补了 6 条）。
  报告必须同时给出清点证据与运行证据，两者缺一不可。

## 与既有条目查重差异 (Dedup / Delta vs Existing Entries)

| 既有条目 | 差异 |
|---|---|
| `DRAFT-tigr-3.1.0-single-file-graphics-headless-compile` | 该条是**编译期**用库自带宏剔除窗口后端（`TIGR_HEADLESS`）以获得 headless **编译**；本条是**运行期**用 broadway 提供显示服务来真实**执行**上游示例 |
| `DRAFT-x11-pkgconfig-triple` | 该条处理 X11 后端库的 pkg-config 三元组依赖；本条走的是“以 broadway 替代 X11/Wayland”的相反路线 |
| `DRAFT-4800-zenity-version-teardown-segfault` | 该条是 `--version` 触发的 GTK teardown 段错误（CLI 工具），与本条的“无显示环境跑 GUI 示例”无关 |
| **本条** | 首发覆盖“上游无自动化测试 + 只有交互式 GUI 示例”时，如何**真实执行**并给出可判定判据（存活判据 + 负向用例），以及必须如实回填的三处载体 |

## 参考 (References)

- 本 PR 实证：`archives/l/libexif-gtk/0.5.0/reports/test-report.md`（本地报告，同内容摘要见 `notes.md`）
- 显示后端来源：本仓 `archives/g/gtk/3.24.43`（broadway 后端，包内 `bin/broadwayd`）
- 规则依据：R51「上游测试三步法」（清点 → 可运行环境实际运行 → PR 如实回填 N/N′/通过率）
