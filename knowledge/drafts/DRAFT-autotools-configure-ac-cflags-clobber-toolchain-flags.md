# configure.ac 无条件覆盖 CFLAGS/CXXFLAGS 会丢弃工具链注入的旗标

> 草稿 · 来源 pipexec 2.6.2 适配（补丁 0002）· 待审核 promote
> 配套 .kv: `knowledge/drafts/DRAFT-autotools-configure-ac-cflags-clobber-toolchain-flags.kv`

## 一句话

有些 autotools 上游在 `configure.ac`（及其生成的 `configure`）**末尾**硬编码
`CFLAGS="..."` / `CXXFLAGS="..."`。这类**赋值不是追加而是覆盖**，会把 Conan
`AutotoolsToolchain` 注入的 `--target=aarch64-linux-ohos`、`--sysroot=...`、`-fPIC`、
`-O*` 全部丢掉。修法是改成追加式赋值（`CFLAGS="$CFLAGS ..."`），而不是在配方里
再加一份 `extra_cflags`——那份同样会被覆盖。

## 现象与判据

命中判据（configure 与 configure.ac 两处都要看）：

```sh
grep -nE '^(C|CXX)FLAGS=' configure configure.ac
# 右值不以 $CFLAGS / $CXXFLAGS 自身开头 → 就是覆盖式赋值
```

pipexec 2.6.2 的实例：

```sh
# configure.ac（生成的 configure 里同样有一份）
CFLAGS="-std=c99 ${COMMON_FLAGS}"
CXXFLAGS="-std=c++11 ${COMMON_FLAGS}"
```

复现实验（本机实测有效）：

```sh
CFLAGS="-O0 -DPIPEXEC_USER_CFLAGS_SEEN=1" ./configure --prefix=/tmp/x
grep -n '^CFLAGS = ' Makefile
# 修复前：CFLAGS = -std=c99 -Wall -Wextra -Werror -O3     ← 外部标记消失（被覆盖）
# 修复后：CFLAGS = -O0 -DPIPEXEC_USER_CFLAGS_SEEN=1 -std=c99 -Wall -Wextra -Werror -O3
```

## 为什么在 OHOS 上尤其要当心

后果按平台分两类，第二类是真正的陷阱：

- **交叉编译（x86_64 宿主 → aarch64 目标）**：clang 失去 `--target/--sysroot`，
  会编出宿主架构产物，或在找 `stdint.h` / `crt*.o` 时直接失败；`-fPIC` 丢失还会让
  共享库链接报 relocation。
- **OHOS 原生构建（宿主即 aarch64）**：设备上的 hnp clang 默认目标已正确，
  `--target` 丢掉**不致命**。于是这个缺陷在原生真机 CI 上可能长期报绿，却在换代码
  路径/交叉构建时突然炸——属**潜伏缺陷**，不能因这一轮绿了就忽略。

## 修法

对 `configure.ac` **和**生成的 `configure` 两处都做最小补丁（两条独立文本；只改
configure.ac 只影响将来重生成的 configure）：

```diff
-CFLAGS="-std=c99 ${COMMON_FLAGS}"
+CFLAGS="$CFLAGS -std=c99 ${COMMON_FLAGS}"
-CXXFLAGS="-std=c++11 ${COMMON_FLAGS}"
+CXXFLAGS="$CXXFLAGS -std=c++11 ${COMMON_FLAGS}"
```

补丁类型 `portability`。仓内同型先例：`archives/l/libnova/0.16`（补丁名
`respect-user-cflags`）、`archives/a/agg`、`archives/l/libagg`（上游用中间变量时，
改成 `CFLAGS="$CFLAGS $temp_CFLAGS"`）。

## 不要这样做（无效处方）

- **在配方里加 `tc.extra_cflags.append(...)` 去对冲**：`extra_cflags` 最终也拼进
  同一个 `CFLAGS` 环境变量，被 configure 末尾的 `CFLAGS=` 覆盖后照样丢，编译命令行
  里根本看不到，反而误导排查。
- **用 `tc.configure_args` 传 `CFLAGS=...`**：老 autoconf（如 2.13 世代）会把不以
  `-` 开头的位置参数当 host 三元组处理并报错（见
  `DRAFT-sntop-1.4.3-autoconf213-configure-rejects-host-args-env-var-channel`）。

正解只有一个：**让上游的赋值不再覆盖用户值**。

## 与既有条目的关系

- `E075`（环境变量陷阱）、`E384`（自写 configure 的变量覆盖）：同属"configure 与
  环境变量交互"，但都未覆盖"**无条件赋值覆盖 toolchain 注入旗标**"这一具体机制。
- 已检索 `knowledge/drafts/`（2094 条）与正式图谱：`respect.*cflags` / `丢失.*fPIC` /
  `CFLAGS 被覆盖` 等判据均 0 命中；只有 `DRAFT-heatshrink`、`DRAFT-genann` 讲
  **Makefile 层**的 `make CFLAGS=...` 命令行覆盖（另一层机制），不重复。

## 复用清单

1. `grep -nE '^(C|CXX)FLAGS=' configure configure.ac` —— 一眼判是否覆盖式。
2. 用 marker 实测（`CFLAGS="-DMARK=1" ./configure && grep '^CFLAGS = ' Makefile`）
   确认旗标是否真的丢，别凭读代码下结论。
3. 两处都打追加式补丁；不要用 extra_cflags / configure_args 对冲。
4. 把"本机绿"和"真机绿"分开看：原生 OHOS 会掩盖这个缺陷，交叉场景才是判据。
