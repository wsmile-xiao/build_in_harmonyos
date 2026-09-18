# leg 0.1.18 适配笔记

## 上游身份（先核验，后适配）

任务标题写的是 `leg / 0.1.18`，但公开上游里**没有名为 leg 的独立项目**。核验过程：

| 候选 | 结论 | 证据 |
|------|------|------|
| `piumarta.com/software/peg/` | **真身** | 项目页自称 “peg/leg — recursive-descent parser generators for C”，一个源码树同时产出 `peg` 与 `leg`；版本表 0.1.1 … 0.1.17(2016-07-14) → **0.1.18(2016-07-22)** → 0.1.19(2023-03-06) |
| SourceForge `leg.sourceforge.net` | 无关同名项目 | 301/302 后落到 `sourceforge.net/projects/leg/`，实为 “LEG — The Linux Encoder Gui”（视频转码 GUI），无版本号，与 PEG 无关 |
| Debian 包 `leg` | 不存在 | `packages.debian.org` 按名检索无 `leg` 包；解析器生成器在 Debian 里叫 **`peg`**，版本 `0.1.18-1`，其 filelist 明确同时含 `/usr/bin/peg` 与 `/usr/bin/leg` |

所以：**leg 是 peg 项目自带的姊妹命令，版本号 0.1.18 来自 peg 的版本序列**，
不存在 `leg-0.1.18.tar.gz`。发行版惯例（Debian/Alpine/Homebrew “aka leg”）都是
包名 `peg`、命令别名 `leg`。本任务按竞赛任务名用 `leg` 作为包名，源码取上游唯一
的 `peg-0.1.18.tar.gz`。

同一个上游在仓库中已有 `peg/0.1.19`（archives/p/peg，已合入并发布到 ohpcd）。
两者**同源不同版本**，`conan list leg/* -r ohpcd` 返回空，不构成 L0j 版本冲突。

## 源码

- URL：`https://www.piumarta.com/software/peg/peg-0.1.18.tar.gz`
- SHA-256：`20193bdd673fc7487a38937e297fff08aa73751b633a086ac28c3b34890f9084`
- 大小：57,776 字节
- 备源（逐字节相同、sha256 一致）：`https://deb.debian.org/debian/pool/main/p/peg/peg_0.1.18.orig.tar.gz`
- 许可：`LICENSE.txt`，MIT（首行 `Copyright (c) 2007-2013, Ian Piumarta`）
- 语言：纯 C（`src/compile.c`、`src/tree.c`、`src/peg.c`、`src/leg.c`），无 C++

## 构建

- 裸 Makefile，无 configure/autotools/CMake。target：`all`(=peg leg)、`check`、
  `test`、`install`、`clean`、`new`。
- 配方用 `basic_layout` + `VirtualBuildEnv`，以
  `make CC=<tools.build:compiler_executables.c> -j1` 构建。
- **不需要 bootstrap**：`src/peg.peg-c` 与 `src/leg.c` 是随包发布的预生成文件，
  默认构建直接编译它们；只有 `make check`/`make new` 才会调用生成器重新生成。
- 两个已知坑：
  1. OHOS 下 make 必须 `-j1`（jobserver fifo 创建失败，仅非并行模式被容忍）；
  2. 上游 `install` 内部硬编码 `strip`，且用非标准 `ROOT`+`PREFIX`（不是
     `DESTDIR`）→ 配方不调用 `make install`，改在 `package()` 里 copy
     `bin/peg`、`bin/leg` 与 `src/peg.1`。

## 上游测试（精确清点，R51）

`conanfile.py::build()` 中真实执行两个上游 target，二者都是**断言**（失败即
`conan create` 失败）：

| target | 用例数 | 内容 |
|--------|--------|------|
| `make check` | 2 | `check-peg`、`check-leg`：用刚构建的生成器重新生成 `src/peg.peg-c`、`src/leg.c`，与发行包内预生成文件 `diff` |
| `make test` | 11 | `examples/`：生成 C → 编译 → 喂输入 → 与 `.ref` 参考输出 `diff` |

`examples/` 11 项（`examples/Makefile: EXAMPLES = ...`）：
`test`、`rule`、`accept`、`dc`、`dcv`、`localpeg`（走 peg），
`wc`、`calc`、`basic`、`localleg`、`erract`（走 leg）。

上游测试**强依赖生成器自身**（每条都要执行 `../peg` / `../leg`），且生成的解析器
也要被执行，所以是在目标机（OHOS aarch64）真机执行，不能改为 host 预跑。

### 与 peg/0.1.19 的关键差异

`archives/p/peg/0.1.19/conanfile.py` 里 `make check` 只能 `ignore_errors=True`：
0.1.19 的预生成文件与源码不自洽（`src/peg.peg-c` 仍是 0.1.18 生成、`src/leg.c`
与 `leg.leg` 不一致）。**0.1.18 没有这个问题** —— 本机实测两条自举 diff 均无
输出、退出码 0，因此这里把 `make check` 作为真断言执行。

## 本机验证边界（WSL，**不是** Harmony 结论）

在 WSL Ubuntu x86_64 上以 `gcc` 做过一次完整原生验证，用于确认配方与测试脚本
本身正确：

| 步骤 | 命令 | 结果 |
|------|------|------|
| 构建 | `make CC=gcc -j1` | 退出码 0，产出 `peg`、`leg` |
| 版本 | `./peg -V` / `./leg -V` | `peg version 0.1.18` / `leg version 0.1.18` |
| 自举 | `make CC=gcc check` | 退出码 0，两条 `diff` 无差异 |
| examples | `make CC=gcc test` | 退出码 0，11 个用例全部 diff 干净 |
| 消费者脚本 | `bash test_package/test.sh`（PATH 指向构建产物） | 退出码 0，`peg/leg consumer test passed` |

**该结果只能记为 `WSL_NATIVE_PASS`（Ubuntu x86_64 + gcc）**，不代表 OHOS
aarch64 通过。OHOS 真机 `conan create` 尚未执行（本轮禁止启动 Harmony 编译）。

另做了一次**仅编译**的 OHOS 交叉检查（WSL 内的 OHOS SDK clang，不接触 Harmony PC）：

```
make CC=<ohos-sdk>/native/llvm/bin/aarch64-unknown-linux-ohos-clang -j1
```

退出码 0，产出 `peg`、`leg` 两个 `ELF 64-bit LSB pie executable, ARM aarch64,
dynamically linked, interpreter /lib/ld-musl-aarch64.so.1`。
**记为 `WSL_CROSS_COMPILE_ONLY`（只证明能编译链接，未在 OHOS 上执行）**，
`make check`/`make test` 需要在目标机跑，本机无法执行 aarch64 OHOS 二进制。

## 待办的已知风险（留给 Harmony 阶段）

1. OHOS 上 `make test` 会编译并运行 examples 的生成解析器；链接由 OHOS clang
   包装器自动签名（否则 XPM 会拒绝执行）。若出现 rc=126，先查签名而不是改上游。
2. `examples/Makefile` 用 `$(CC)`，配方已把 OHOS C 编译器透传进去；若某个
   example 自行调用裸 `cc`，需在 Harmony 阶段确认。
3. 上游只发行 `peg.1`，没有 `leg.1`；本包不伪造 `leg.1`。

## 与仓库内既有分支的关系（重要，尚未处理）

上游仓库已存在另一个贡献者的分支 `refs/heads/feat/leg-0.1.18`
（commit `5153a068b6`，作者 werly，2026-09-14），其中已有一份 leg 0.1.18 适配
（同样取 peg-0.1.18.tar.gz，URL/sha256 正确）。该分支**当前没有对应的 open PR**，
也未合入 main。本 worktree 的 `feat/leg-0.1.18` 是从 `upstream/main` 新建的独立
提交线，因此：

- 它与那个分支同名但内容不同，**推送时必须先与用户确认**（直接 push 会覆盖他人提交）；
- 是否复用他人的成果、还是提交本配方，属于需要人工决策的问题，本笔记只记录事实。

## 可复用知识候选

- “任务名 ≠ 上游项目名”：`leg` 实为 `peg` 项目里的第二个命令，版本号来自 peg 的
  版本序列；同类还有发行版二进制包名（`liborcania` = 上游 `orcania`）的别名现象。
  核验方法是查上游项目页/tarball 清单与 filelist，而不是信任务清单里的名字。
- 同一个上游在不同版本上 `make check` 的可断言性可能相反（0.1.18 可断言、
  0.1.19 只能 ignore_errors），不能把某个版本的处理方式照搬到相邻版本。
