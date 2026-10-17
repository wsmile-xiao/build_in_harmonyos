# DRAFT-mlv-smile-1.47-suckless-baked-paths-makevar-override

## 一句话
裸 Makefile 时代的包把 `CC=gcc` 等工具链变量写死在 Makefile 内部；OHOS 无 gcc，
唯一无侵入的注入通道是 make 命令行变量赋值（优先级高于 Makefile 赋值、经 MAKEFLAGS
自动传播到递归子 make）。

## 症状
`make[1]: gcc: No such file or directory`（或 `cc:`），第一条编译规则即失败；
make rc=2。

## 根因
上游 Makefile：`CC=gcc` + `C_FLAG=$(OPT) -I...` + 递归 `(cd sub && $(MAKE) all)`。
工具链假设 = 构建机自带 gcc；OHOS 只有 clang。

## 最小复现与修法（mlv-smile 1.47，A 机 2026-09-25）
- 未覆盖：`make` → 首个 `.c` 编译即 gcc 缺失。
- 覆盖：`make CC=<ohos clang>` → 编译/链接全部走通（x-smile 等 5 工具产出）。
- 递归传播：顶层命令行变量经 MAKEFLAGS 自动下传，无需逐层 -e 或改写。
- 配方落点：`self.run(f'make -j2 CC="{cc}"', cwd=src)`，cc 取自 profile 的
  tools.build:compiler_executables。

## 边界
- 子 Makefile 若使用 `override CC = ...` 指令则命令行失效 ⇒ 需转补丁（未见先例）。
- 旗标类硬编码（-ansi 等）若 clang 不兼容，同法经 OPT/C_FLAG 变量覆盖。
- SigStat 类"顺序依赖 all 目标"（先构建依赖 obj 树再链接）对 -j 不安全 ⇒ 分目录、
  依赖填充阶段串行（mlv-smile 实测并行链接早于 model.o 产出即失败）。

## 证据
- `~/tmp/uc2/z35-smile/create-r1.log`（gcc 缺失 → 覆盖后全绿 + 消费者 3/3 PASS）
- 泳道先例：dmenu 5.4（DS-33）；本例为其在 autotools-free 递归 Makefile 场景的第二例
