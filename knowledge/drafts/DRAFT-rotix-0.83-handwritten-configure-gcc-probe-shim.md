# Draft: 手写 configure 按"名字"探测编译器并中止（axel 系）—— PATH gcc shim 满足探测 + make CC= 钉真实编译器

> Source event: `rotix/0.83` 首次适配（2026-09-27，本机 OHOS clang 交叉编译 + 真机 shadow CI r1 一次通过）。
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## 问题

一批 2000 年代 C 工具的 `./configure` 是**手写 POSIX shell**（rotix 的 configure 由
Wilmer van der Gaast 为 axel 所写，README 内含致谢，axel 系工具共用此风格）。它不探测
库、不生成 config.h，只做一件事：按**可执行文件名字**探测编译器并写出 `Makefile.settings`：

```sh
if type gcc > /dev/null 2> /dev/null; then
	echo "CC=gcc" >> Makefile.settings;
elif type cc > /dev/null 2> /dev/null; then
	echo "CC=cc" >> Makefile.settings;
else
	echo 'Cannot find a C compiler, aborting.'
	exit 1;
fi
```

OHOS PC 环境只有 clang（无 gcc/cc），configure 在**生成 Makefile.settings 之前**就退出：

```text
Cannot find a C compiler, aborting.        # configure exit 1
```

关键点：这类 Makefile 本身用 `$(CC)`，`make CC=clang` 是有效的——但**根本走不到 make**：
configure 先中止。命令行覆盖救不了探测阶段。

## 与既有条目的边界（查重声明）

| 既有条目 | 场景 | 与本条的差异 |
|---|---|---|
| DRAFT-cnrbtree-0.3-makefile-recipe-gcc-hardcode | Makefile **配方体**内字面 `gcc`，无 CC 变量、无 configure | 本条有 configure 探测阶段，Makefile 反而支持 CC= |
| DRAFT-cohomcalg-0.32-makefile-gxx-override | Makefile 声明 CC 变量，无探测 | 同上，无 configure 中止问题 |
| DRAFT-ffc.h-26.07.01-makefile-uname-gcc-hardcode | Makefile 内 uname 平台宏 + 配方体硬编码 gcc | 无 configure |
| E384（configure-documented-env-override） | 手写 configure 探测**第三方库**（pkg-config/-lssl）不读 conan 环境 | 本条探测的是**编译器本身** |
| E264（*-config helper shim） | 依赖的 *-config 助手脚本 shim | 对象不同（依赖助手 vs 编译器探测） |
| E672 草稿（kmc） | 捆绑 zlib 子 configure 出现同款 "Checking for gcc... aborting" 症状 | 仅作复合条目内的附带记录，未沉淀通用模式 |

知识库（index.tsv 540 条 + drafts）中**没有**"configure 编译器存在性探测中止 → PATH shim"
的专门条目；axel 系 configure 与其衍生（含第三方捆绑子项目）复用面广，值得独立沉淀。

## 根因

上游把"编译器是否存在"实现为"**编译器的名字**是否存在"（`type gcc`/`type cc`）。
OHOS 供给的是 clang，名字对不上 ≠ 能力缺失。修复方向是**供给一个满足探测的环境**，
而不是改上游探测逻辑：在 build 目录写一个 `gcc` shim（`exec "<target-clang>" "$@"`）
前置到 PATH，探测命中后 configure 照常写出 `CC=gcc`；再用 `make CC="<真实编译器>"`
把实际编译钉到 profile 指定的 clang（双保险：即使后续步骤丢失 PATH 前置，编译器也正确）。

## 修复（Conan 配方，不动上游源码）

```python
# build() 内（R33：编译器取自 profile conf，绝不裸用 shell 变量）
compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
cc = compilers.get("c", "clang") if compilers else "clang"
config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

shim_dir = os.path.join(self.build_folder, "build-bin")
os.makedirs(shim_dir, exist_ok=True)
with open(os.path.join(shim_dir, "gcc"), "w", newline="\n") as h:
    h.write(f'#!{config_shell}\nexec "{cc}" "$@"\n')
os.chmod(os.path.join(shim_dir, "gcc"), 0o755)
os.environ["PATH"] = shim_dir + os.pathsep + os.environ.get("PATH", "")

self.run(f'{config_shell} ./configure --prefix="{prefix}" ...', cwd=self.source_folder)
self.run(f'make CC="{cc}" ... -j1', cwd=self.source_folder)   # E392：必须 cwd=source_folder
```

## 同族陷阱②：`STRIP=0` 被当命令执行

同一 configure 家族找不到 `strip` 时写 `STRIP=0`（本意"禁用剥离"），而 Makefile 里是
`ifdef STRIP` + `$(STRIP) rotix`——已定义就执行，于是变成运行命令 **`0`**：

```text
make: 0: No such file or directory   # 或 command not found
```

修复：`make ... STRIP=true` 中和（`true` 任何环境都有、成功返回、无副作用）。真机 r1
构建日志中链接行后的 `true rotix` 即该中和生效的直接证据。

## 同族陷阱③：`case $(uname -s)` 无 HarmonyOS 分支（简述，另见 E007/E160）

axel 系 configure 枚举 FreeBSD/OpenBSD/Darwin/SunOS/CYGWIN/Linux...，真机 `uname -s`
返回 `HarmonyOS` 落入 `*` 默认分支（日志：`Compiling for: HarmonyOS` +
`WARNING: This architecture is not tested!`）。平台识别补丁方案见 E007/E160（autotools
config.guess/sub）；本条的增量提醒是：**默认分支可能静默写入"降级兼容宏"**——rotix 默认
分支写 `NO_GETOPT_LONG=1`，而 OHOS sysroot 的 getopt.h 实际**有** `getopt_long`（rotix
本身无长选项，降级无害，实测 13/13 通过留证后接受）。适配此类 configure 时应审计默认
分支写了什么宏、是否在静默关闭目标平台实际支持的能力。

## 验证

```sh
# 本机两态实测（无 OHOS 环境也可复现 ①）：
sh ./configure --i18n=0 --strip=0            # -> exit 1, Cannot find a C compiler, aborting.
PATH=/path/to/shimdir:$PATH sh ./configure ... # -> exit 0, Makefile.settings 出现 CC=gcc / STRIP=0

# 真机 shadow CI（rotix/0.83 r1，2026-09-27）：
# conan create 成功（configure 识别 HarmonyOS、NO_GETOPT_LONG=1 回退编译、
# make CC=<target clang> STRIP=true、链接后 true rotix），test_package 13/13，exit 0
```

## 禁忌

- 不改上游 configure 的探测逻辑（shim 是环境供给，保持上游语义、零源码补丁）；
- 不把 gcc shim 写进共享前缀或任何系统 PATH 目录（只放 `self.build_folder` 私有目录，R26/E524）；
- configure 已探测中止的场景，只加 `make CC=` 不加 shim = 无效（走不到 make）；
- shim 不做"名字换成 cc"以外的事（不注入 flags，编译器与参数一律来自 Conan profile，R33）。

## 关系

- similar_to: DRAFT-cnrbtree-0.3-makefile-recipe-gcc-hardcode, DRAFT-cohomcalg-0.32-makefile-gxx-override, DRAFT-ffc.h-26.07.01-makefile-uname-gcc-hardcode
- complement: E007/E160（平台识别补丁）、E384（手写 configure 库探测）、E392（raw makefile 配方三要素：filename / compiler_executables dict / cwd）
