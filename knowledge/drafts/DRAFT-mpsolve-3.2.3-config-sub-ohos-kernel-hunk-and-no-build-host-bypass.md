# 鸿蒙三元组卡在 config.sub 的**第二道**校验；以及"一键脚本自报 ✅"与"用 --build/--host 绕过"这两个反面模式

CI build #53927（mpsolve 3.2.3，worker `OpenHarmonyPCDeveloper-CI-031`）在 configure 阶段挂掉：

```
mpsolve/3.2.3: RUN: env -u CONFIG_SHELL SHELL=/bin/sh ... sh ./configure \
    --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos ...
checking build system type... aarch64-unknown-linux-gnu
checking host system type... Invalid configuration `aarch64-unknown-linux-ohos':
                             OS `ohos' not recognized
configure: error: /bin/sh ./config.sub aarch64-unknown-linux-ohos failed
```

这一行报错背后其实藏着三件事：两道串联的校验关口、一个会自报成功的仓库脚本、
以及一条"看似能绕"的错路。

---

## 场景一：config.sub 认 `linux-ohos` 要**两道**关口同时打开

`config.sub` 对一个三元组的校验是**串行两段**，报错文案还完全不同：

```sh
# 第一道：OS 类型列表（"Now accept the basic system types"）
case $os in
    gnu* | android* | bsd* | ... | fiwix* )   # ← 缺 ohos* 就报 OS `ohos' not recognized
        ;;
    *)
        echo Invalid configuration \`"$1"\': OS \`"$os"\' not recognized 1>&2
        exit 1
esac

# 第二道：内核-OS 组合校验表
case $kernel-$os in
    linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* \
       | linux-musl* | linux-relibc* | linux-uclibc* )   # ← 缺 linux-ohos* 就报下面这条
        ;;
    ...
    *-*)
        echo "Invalid configuration \`$1': Kernel \`$kernel' not known to work with OS \`$os'." 1>&2
        exit 1
esac
```

**它们是串联的**：补好第一道只是让流程推进到第二道，并不顺带修好第二道。
实测（本包 config.sub，`timestamp='2022-01-03'`，autoconf 2.71 一代）：

```
$ sh config.sub aarch64-unknown-linux-ohos        # 只补 OS 列表
Invalid configuration `aarch64-unknown-linux-ohos': Kernel `linux' not known to work with OS `ohos'.
$ sh config.sub aarch64-unknown-linux-ohos        # 两处都补
aarch64-unknown-linux-ohos
```

为什么是这两道而不是别的？因为这一代 config.sub 的 `maybe_os` 分支已经含 `linux-*`：

```sh
*-*-*)
    maybe_os=$field2-$field3
    case $maybe_os in
        nto-qnx* | linux-* | uclinux-uclibc* | ...)   # linux-* 在此
```

4 段输入 `aarch64-unknown-linux-ohos` 走的是更前面的 `*-*-*-*` 分支直取
`basic_os=$field3-$field4 = linux-ohos`，随后 `IFS="-" read kernel os` 拆成
`kernel=linux, os=ohos` —— 正好先后撞上上面两道关口。

> **一句话判据**：补丁后必须**实跑** `sh config.sub aarch64-unknown-linux-ohos`
> （两种写法都试），看它是否原样回显。

---

## 场景二：仓库的一键脚本会**漏掉第二道**，还打印 ✅

仓库自带 `scripts/patch-autotools-ohos.pl`，其设计意图是三处：
§2.1 `ohos-linux` 映射、§2.2 OS 列表加 `ohos*`、§2.3 内核列表加 `linux-ohos*`。
但在这类 config.sub 上 §2.3 会**静默 skip**：

```perl
# §2.1 先插入（这一句会往文件里写进字符串 "basic_os=linux-ohos"）
$sc =~ s{...}{...$6\tohos-linux)\n...basic_os=linux-ohos\n...}m;

# §2.3 的守卫却是"整文件"子串测试 —— 被上一步自己写的字符串顶成真
unless ($sc =~ /linux-ohos/) {          # ← 恒为假，于是 skip
    $sc =~ s{(linux-uclibc\*[/-]?\s*)\)}{$1| linux-ohos*)};
}
```

更糟的是收尾自检用的是**同一个整文件匹配**：

```perl
$ok++ if $sc =~ /linux-ohos/;                     # 被 §2.1 插入的那句满足
printf "config.sub:  ohos-linux=%d ohos*=%d linux-ohos=%d\n", ...;
print "Score: $ok/5\n";  if ($ok >= 4) { print "✅ Patching successful.\n"; }
```

于是"漏补"与"通过"同时发生。实跑对照：

```
$ perl scripts/patch-autotools-ohos.pl a/config.guess a/config.sub
  [skip] linux-ohos already present
Score: 4/5
✅ Patching successful.
$ sh b/config.sub aarch64-unknown-linux-ohos
Invalid configuration `aarch64-unknown-linux-ohos': Kernel `linux' not known to work with OS `ohos'.
```

**失效模式值得单记**：*守卫/自检用整文件子串，而被检查的那个分片早被同脚本的
前序步骤改过* —— 这类脚本的"自证成功"是结构性的，不是偶然。凡是"一键补丁脚本"
都该用**产物实跑**兜底，而不是读它自己的计分。

本包的处理：手写 `patches/0002-config.sub-ohos.patch`，把脚本的三处意图补齐
（`ohos-linux` 映射 + OS 列表 `ohos*` + **内核列表 `linux-ohos*`**），
并逐条 `patch -p1 --dry-run` 验证后再落地。

---

## 场景三：`--build/--host` 既不合规、也**省不掉补丁**

旧配方写的是：

```python
"--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos"
```

看起来是"直接告诉 configure 我要什么"，实际上有三个连锁后果：

1. **它并不省事。** `configure` 依然会调用 `config.sub` 去规范化 `--host` ——
   这正是 #53927 失败的那一行。也就是说：想用这个法子，`config.sub` 的两道关口
   照样得补，一点没少。
2. **它把 configure 骗进交叉编译分支。** build ≠ host ⇒
   `cross_compiling=yes` ⇒ `AC_RUN_IFELSE` 一类**运行时探测被整体跳过**，
   退回保守默认值写进 `config.h`（E007 已写明这一后果）。设备上随后会出现
   "编译通过但功能对不上"的软故障，归因成本远高于一次 configure 失败。
3. **`--build=aarch64-unknown-linux-gnu` 本身就是假话**：构建机不是 gnu 三元组的
   机器，它是鸿蒙。P-AUTOTOOLS-001 把这条列为铁律（禁用 `--build/--host` 绕过）。

正解是**让 configure 自己猜**：补好 `config.guess`（HarmonyOS 分支 → 输出
`${MACHINE}-unknown-linux-ohos`）与 `config.sub`（两道关口），配方里那对三元组整个删掉。

```python
self._my_configure_args = (
    f"--prefix={self.package_folder} "
    "--disable-ui --disable-graphical-debugger --disable-documentation "
    "--disable-examples --disable-tcmalloc"
).split()          # 没有 --build / --host
```

---

## 场景四：宿主侧就能把这条链路跑通（不必等 CI）

OHOS 设备不是必需的：**把 `uname` 换成桩**，就能在 x86_64 上复现整条三元组链路。

```sh
mkdir fakebin
cat > fakebin/uname <<'EOF'
#!/bin/sh
case "$1" in
  -s) echo HarmonyOS ;;  -m) echo aarch64 ;;
  -r) echo 5.0.0 ;;      -v) echo 1 ;;
  *)  echo HarmonyOS ;;
esac
EOF
chmod +x fakebin/uname
PATH="$PWD/fakebin:$PATH"
```

实测（本包，补丁已应用）：

```
$ sh ./config.guess
aarch64-unknown-linux-ohos
$ GMP_CFLAGS=... sh ./configure --prefix=... --disable-ui --disable-documentation ...
checking build system type... aarch64-unknown-linux-ohos
checking host system type... aarch64-unknown-linux-ohos      # host == build，原生构建
$ make -j4        ; echo $?   → 0
$ make -C src check -j1 ; echo $?   → 0
  # TOTAL: 16 / # PASS: 16 / # FAIL: 0 / # SKIP: 0
```

这一步还顺手把"libtool 会不会不认这个新 host_os"的疑虑消掉了：`LT_INIT` 在
host=`aarch64-unknown-linux-ohos` 下正常工作、`config.status` 正常生成
（libtool 的 `linux*` 分支通配 `linux-ohos`，语义上也正确 —— 鸿蒙是 linux 内核）。

> CI 仍然必需（要验 OHOS 侧的 clang / HMDFS / check 框架），但"三元组认不认"
> 这一类问题**在本地就能结案**，不该占一轮 CI。

---

## 推广：三条

1. **"补丁脚本说成功"不是判据，产物实跑才是。** 守卫与自检若都用整文件子串、
   而分片被同脚本前序步骤改过，脚本就会稳定地"漏补并报 ✅"。
   `sh <config.sub> aarch64-unknown-linux-ohos` 一行就能证伪。
2. **平台补丁是"两处/多道关口"的常客。** 认一个三元组往往要同时改 OS 列表与
   内核-OS 校验表（还有映射表）；报错文案不同、串联生效 —— 只修一处会在下一处
   以另一种措辞再失败。改完必须把**所有会被调用的输入形态**各跑一遍。
3. **`--build/--host` 不是"快速通道"，是"把问题从编译期推迟到运行期"。**
   它既不合法（P-AUTOTOOLS-001），也不省事（config.sub 照样要补），
   代价却是 `config.h` 失真。正确做法永远是：补 `config.guess`/`config.sub`，
   让 configure 自己猜出与 build 相同的 host。
