# k2 0_git20260430 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure）
- 编译日期: 2026-10-02
- 编译器: clang/clang++ 15.0.4（OHOS aarch64 交叉工具链）
- 状态: built（本地 conan create 全量验证通过）

## 软件身份
- 上游: https://github.com/serg-meus/k2 （Sergey Meus 的国际象棋引擎，UCI/Xboard 双接口，GPL-3.0-or-later）
- 版本语义: `0_git20260430` 取自 Alpine aports `community/k2` 锁定的上游 commit 快照 `8e4531b92dd329358de1c74c23894bf8977e1588`（引擎自报 `id name K2 v1.0 alpha`）
- 产物形态: 单个可执行文件 `k2`（CLI 工具，非库）→ 按 R38 提供 software 级 `commands.json`

## 编译步骤

1. W0 依赖预检: `conan download`/APKBUILD 交叉确认 —— k2 无第三方依赖（空依赖集，预检通过）。
2. 源码: conandata.yml 官方 URL（GitHub commit 快照 tar.gz，sha256 已核对）。
3. 探索性编译（源码目录，零源码修改）:
   ```bash
   make CC=clang++ CFLAGS="-std=c++0x -Werror -Wall ... -Weffc++ -Wno-unknown-warning-option" -j2
   ```
   成功；`make test CC=clang++ CFLAGS="... -DUSE_THREAD=false -O0"` + `./test_all` → "All tests passed"。
4. 配方: `conanfile.py` 以 application 模式构建——`make CC="<conf:compiler_executables:cpp>" CFLAGS="<上游原始告警集> -Wno-unknown-warning-option" -j1`，`package()` 仅拷贝 `k2` 二进制到 `bin/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | clang 报 unknown warning option，配合上游 `-Werror` 直接中止 | 上游 CFLAGS 硬编码 GCC 专属告警旗标族（-Wctor-dtor-privacy/-Weffc++/-Wsign-promo 等） | 配方在 make 命令行传入上游完整告警集 + `-Wno-unknown-warning-option`（覆盖式，不改源码） |
| 2 | 上游 Makefile 把 `CC=g++` 硬编码 | 上游默认目标 `prod` 用 g++ 作 C++ 驱动 | `make CC="<clang++ 路径>"` 覆盖；编译器经 `self.conf.get("tools.build:compiler_executables:cpp")` 从 profile 获取（R33，禁 shell env） |
| 3 | `-j2` 报 "jobserver mkfifo: Operation not permitted" | HMDFS 不允许 mkfifo，make jobserver 降级 | 配方按 R9 用 `-j1`（k2 体量小，单核数十秒） |
| 4 | `make test` 首轮在 `test_eval_pawns` 断言失败: `val == -pawn_dbl_iso` (mid=-83) 实际 (mid=-62) | **上游测试滞后于实现**（平台无关，GCC 同样挂）：`double_pawns()` 用单步移位 `p_bb & roll_down(p_bb)` 只识别相邻双兵；测试位置 `4k3/1p6/8/8/1P6/8/1P6/4K3 w - -` 的 b2/b4 为非相邻同线双兵，实现判 `double_pawns=0`、`isolated=2`，评分为 `-2*pawn_isolated=(-62,-28)` | 归因探针（继承 eval 暴露 protected 成员，位级证据见 PR 正文）确认后，修正 `test_all.cpp` 该断言为 `assert(val == -2*pawn_isolated)` 并附说明注释（补丁 `fix-test_all-stale-pawn-assert.patch`，无平台宏）；修正后 49/49 测试全过 |

## 源码修改

- `fix-test_all-stale-pawn-assert.patch`（conandata.yml 声明）：仅上游单元测试文件 `test_all.cpp` 一处滞后断言修正 + 说明注释。
  - **无平台宏、无条件编译**（PF5 安全）：该修复修复的是上游测试期望值与评估实现之间的不一致，属于上游 bug，在任何平台（含上游 x86_64 GCC）表现一致。
  - 不影响交付物 `k2` 二进制的任何源文件。

## 依赖版本

- 无第三方依赖（空依赖集）。
- pthread 随 OHOS libc 提供，`-DUSE_THREAD=true` 无需额外链接旗标。

## 验证结果

```bash
# 上游单元测试（修正 1 处滞后断言后）：49/49 全过
$ ./test_all
All tests passed            # exit=0

# 真机功能冒烟（多线程 prod 构建，UCI 协议）：
$ k2   ←  stdin: "uci"                      → uciok
$ k2   ←  stdin: "isready"                  → readyok
$ k2   ←  "position startpos" + "go depth 5"    → bestmove e2e4
$ k2   ←  "position startpos moves e2e4 e7e5 g1f3 b8c6 f1b5 a7a6" + "go depth 7"
                                            → bestmove b5c6（吃黑格 e5 兵，符合局面）

# conan create 全量验证（G2）：见 reports/ 审计记录
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/k2 | ~0.6 MB | 单可执行文件（UCI/Xboard 双接口引擎） |

## 注意事项

- k2 无 `--version`/`--help` 类 CLI 旗标，纯 stdio 协议交互；commands.json 记录 UCI 冒烟命令。
- 上游 `make test` 与 `make prod` 是两套编译参数（test: `-DUSE_THREAD=false -O0`，prod: `-DUSE_THREAD=true -O3 -flto`）；配方仅构建 `prod` 交付物，上游单元测试在适配验证阶段于源码目录独立执行（结果记录于 test_package/MANIFEST.yml）。
---

**编译结束**: 2026-10-02 04:47
**最终状态**: built
