# E543（草稿）— conan OHOS profile 两侧同构导致 autotools 三元组缺失

> 状态：草稿（由适配 `jday/2.4` 时产出，建议主编评估后 promote）
> 相关条目：E007、E072、E122、E205（均为 config.guess/config.sub 不识别 OHOS 三元组）

## 现象

老 autotools 项目在 conan 的 OHOS profile 下构建时，configure 阶段出现下列之一：

```
checking build system type... Invalid configuration `aarch64-linux-ohos':
  machine `aarch64-linux' not recognized
```

```
configure: error: cannot run C compiled programs.
If you meant to cross compile, use `--host'.
```

```
aarch64-binfmt-P: Could not open '/lib/ld-musl-aarch64.so.1': No such file or directory
```

## 根因

`ci/conan/profiles/ohos-aarch64` 同时用作 `-pr:h` 与 `-pr:b`，两侧 settings 完全一致，
conan 的 `cross_building()` 判定为 **False**，`AutotoolsToolchain` 因此**不注入**
`--host` / `--build`。对于随包 `config.guess` / `config.sub` 停留在 aarch64（2012）
之前的老项目，这带来两个方向的坑：

1. **什么都不传**：configure 用 `config.guess` 猜出的**构建机**三元组去配置 libtool
   与平台规则（x86 机上就是 `x86_64-unknown-linux-gnu`），编译器虽是 OHOS clang，
   但平台规则按构建机走，属于静默错配。
2. **把 `--build` 写死成目标三元组**（常见于照抄他包配方）：x86_64 交叉构建机上
   `build == host`，configure 判定为原生编译并尝试**运行**刚编出的 aarch64 产物，
   因构建机缺 `/lib/ld-musl-aarch64.so.1` 直接失败。

## 推荐做法

两个 portability 补丁 + 配方只传 `--host`：

```diff
--- a/config.sub
+++ b/config.sub
-  nto-qnx* | linux-gnu* | linux-dietlibc | ...
+  nto-qnx* | linux-gnu* | linux-ohos* | linux-dietlibc | ...
-	| arc | arm | arm[bl]e | ...
+	| aarch64 | arc | arm | arm[bl]e | ...
-	      | -mingw32* | -linux-gnu* | ...
+	      | -mingw32* | -linux-gnu* | -linux-ohos* | ...
```

```diff
--- a/config.guess
+++ b/config.guess
+    aarch64:Linux:*:*)
+	echo ${UNAME_MACHINE}-unknown-linux-gnu
+	exit 0 ;;
+    aarch64:HarmonyOS:*:* | aarch64:OHOS:*:*)
+	echo ${UNAME_MACHINE}-unknown-linux-ohos
+	exit 0 ;;
     x86_64:Linux:*:*)
```

> **`aarch64:HarmonyOS` 分支不可省**（本条最容易踩的坑，CI #57604 实测）：鸿蒙 PC 真机的
> `uname -s` 返回 **HarmonyOS**（`uname -r` = `HongMeng Kernel 1.12.0`），只加 `aarch64:Linux`
> 分支在真机上永不命中；config.guess 随后落到兜底逻辑，要往 `$TMPDIR` 写 `dummy.c` 做编译探测，
> 在 HMDFS 上 `Permission denied`，最终 `configure: error: cannot guess build type`。
> 该现象与已有条目 **E007** 同源，本条补的是它在「conan 交叉构建 + 真机 CI 双环境」下的具体形态。

```python
def generate(self):
    tc = AutotoolsToolchain(self)
    if str(self.settings.os) == "OHOS":
        # profile 两侧同构 → conan 不注入三元组，这里显式补 --host；
        # 不写死 --build，交给（已打补丁的）config.guess 探测真实构建机。
        tc.configure_args.append("--host=aarch64-linux-ohos")
    tc.generate()
```

效果（两种构建机各走正确路径，均可复现）：

| 构建机 | `config.guess` 输出 | 与 `--host` 规范化值比较 | configure 路径 |
|---|---|---|---|
| x86_64 交叉机 | `x86_64-unknown-linux-gnu` | 不等 | 交叉编译，不运行目标机产物 |
| 鸿蒙 PC 真机 | `aarch64-unknown-linux-ohos` | **相等** | 原生编译，运行期探测正常可用 |

验证方式（无真机时可用 mock `uname` 复现真机分支）：

```bash
$ cat /tmp/mock-bin/uname          # -s 返回 HarmonyOS、-m 返回 aarch64
$ PATH=/tmp/mock-bin:$PATH ./config.guess
aarch64-unknown-linux-ohos
```

## 配套踩到的两个真机限制（同一适配里一并遇到，均已有条目）

`config.guess` 修好后，真机 CI 紧接着暴露了另外两个**只在真机出现**的问题，
适配老 autotools 包时建议一次性备齐：

| 现象 | 条目 | 处置 |
|---|---|---|
| `./confstatXXXXXX/subs.sed: Permission denied`，`config.status` 生成 Makefile 失败 | E011 | config.status 的临时目录改用 `mkdir` + `umask 000`；`mktemp -d` 把权限硬编码成 0700，HMDFS 的 UID 映射下对本进程不可写，改 umask 无效，必须换掉该分支 |
| `make: jobserver mkfifo: Operation not permitted` → `No targets specified and no makefile found` | E074 / E525 | `generate()` 注入 `MAKEFLAGS=-j1`，`build()`/`package()` 显式 `-j1` |

这三处（config.guess 的 HarmonyOS 分支、config.status 的临时目录、make 并发）
都**无法在 x86_64 交叉构建机上复现**——本地 W3 会一路全绿。适配老 autotools 包时
应当在首次提交前就按此清单自查，而不是靠 CI 一轮一轮试。

## 与 E205 / E122 的边界（本条的新增点）

E205、E122 都写着「禁止用 `--build/--host` 作为 workaround」。那两条针对的是：
在**能够原生判定 ohos 的环境**里，用三元组开关去掩盖 config.sub 缺失 `linux-ohos`
的问题，并且项目含 `AC_RUN_IFELSE` 运行期探测——此时按交叉处理会让 `config.h`
取到不符实际的缓存默认值。

本条针对的是互补场景：**构建机本就与目标机不同架构**（x86_64 交叉机），而 conan
profile 两侧同构导致工具链不注入三元组。此时 `--host` 是**正确语义而非 workaround**，
且必须与 config.sub/config.guess 的补齐配合使用。

采用前的判定命令（务必执行）：

```bash
grep -c ac_fn_c_try_run configure   # 0 = 项目无运行期探测，--host 无副作用
```

实测 `jday/2.4` 该计数为 0，26 条上游用例在 qemu-aarch64 下全部通过。

## 验证

```bash
./config.sub aarch64-linux-ohos          # → aarch64-unknown-linux-ohos
./config.guess                           # → 构建机真实三元组
grep -n 'host=aarch64-linux-ohos' conanfile.py
grep -c ac_fn_c_try_run configure        # 期望 0
```

## 来源

- 适配事件：`archives/j/jday/2.4`（jday 2.4，2005 年发布，autotools + libtool 1.5.6）
- 同族先例：`archives/a/aalib/1.4p5`（写死 `--build=aarch64-linux-ohos`，在 aarch64
  原生构建机上可行，但在 x86_64 交叉构建机上会命中本条的 forbid_1）
