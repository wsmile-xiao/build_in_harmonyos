# libredblack 1.3 — HarmonyOS PC (aarch64) 适配笔记

- 上游：libredblack — RedBlack Balanced Tree Searching and Sorting Library
  （作者 Damian Ivereigh，Cisco）
- 官网：http://libredblack.sourceforge.net/
- 版本：1.3
- 许可证：**LGPL-2.1**（COPYING 是 LGPL v2.1；注意各家打包元数据说法不一
  —— OpenWrt 写 GPL-2.0-or-later、ALT/Mandriva 写 LGPLv2+、FreshPorts 写 GPLv2、
  Repology 写 LGPL —— **以源码自带的 COPYING 为准，本配方按 LGPL-2.1**）
- 构建系统：autotools（tarball 自带生成好的 `configure` / `Makefile.in` /
  `config.h.in`，无需 autoreconf）
- 依赖：**无**
- 包形态：纯库 —— `lib/libredblack.a`（或 `libredblack.so*`）+ `include/redblack.h`
  + man pages；**不安装可执行文件**，故不需要 commands.json（R38）
- 状态：**READY_FOR_HARMONY** —— WSL 侧完整 `conan create` 已跑通（见 §5），
  HarmonyOS 真机尚未执行

## 1. 上游测试清点（R51 三步法第 1 步）

| 项 | 值 | 依据 |
|---|---|---|
| `upstream_test_targets` | **0** | `Makefile.am` 无 `TESTS` / `check_PROGRAMS` / `check-local` |
| `upstream_test_files`   | **0** | 无 tests/ 目录 |
| `upstream_case_total`   | **0** | `example*.c` 是 `noinst_PROGRAMS` 演示程序，不含断言与期望输出 |

## 2. 平台适配点（4 个补丁）

### 2.1 config.guess：两个**独立**的缺口
上游带的是 **2001-09-04** 版 config.guess：

1. **没有 HarmonyOS 分支** → worker 上 `uname -s=HarmonyOS`，直接
   `unable to guess system type`；
2. **只有 `arm*:Linux:*:*`** —— 而 shell 通配 `arm*` 匹配的是**以 arm 开头**
   的字符串，`aarch64` 以 `aac` 开头，**不匹配**。

所以补了两处：`aarch64:Linux:*:*` 与 `*:HarmonyOS:*:*`。二者互不替代。

### 2.2 config.sub：必须改**两处**（容易只改一处而失败）
老式 config.sub 的解析分两段：

```sh
maybe_os=`echo $1 | sed 's/^\(.*\)-\([^-]*-[^-]*\)$/\2/'`
case $maybe_os in
  nto-qnx* | linux-gnu* | storm-chaos* | os2-emx* | windows32-*)
    os=-$maybe_os
    basic_machine=`echo $1 | sed 's/^\(.*\)-\([^-]*-[^-]*\)$/\1/'`
    ;;
  *)  # 否则 basic_machine 取到倒数第二个 dash 之前
```

`linux-ohos` 不在特殊列表里 → `aarch64-unknown-linux-ohos` 被拆成
`basic_machine=aarch64-unknown-linux` + `os=-ohos`，而机器名校验里 `*-*-*`
（两个 dash）直接判**不识别**：

```
$ config.sub aarch64-unknown-linux-ohos
Invalid configuration `aarch64-unknown-linux-ohos': machine `aarch64-unknown-linux' not recognized
```

**第一版我只在后面 OS 白名单加了 `-ohos*`，报错完全没变**——必须在
`maybe_os` 的特殊分支里补 `linux-ohos*`（与 `linux-gnu*` 并列），再把
`-linux-ohos*`/`-ohos*` 加进 OS 白名单。两处都改后才归一化正确：

```
$ config.sub aarch64-unknown-linux-ohos -> aarch64-unknown-linux-ohos
$ config.sub aarch64-unknown-linux-gnu  -> aarch64-unknown-linux-gnu   (回归不受影响)
$ config.guess（伪 HarmonyOS uname）      -> aarch64-unknown-linux-ohos
```

### 2.3 configure：umask 077 → 022（4 处）
老 autoconf 的临时目录创建有 4 处 `umask 077`（sed 块 2 处 + config.status 块 2 处），
HMDFS 下 077 目录不可用。与仓库既有结论 E011 一致。

### 2.4 ⭐ Makefile 写死 CFLAGS 覆盖 toolchain（本项目最有价值的发现）
`Makefile.am:24` 写死 `CFLAGS=-Wall`，它会**覆盖 Conan toolchain 导出的全部
CFLAGS**。实测编译行：

```
# 修复前（-O2/-fPIC 全丢）
gcc -DHAVE_CONFIG_H -I. -I. -Wall -c redblack.c
# 修复后
gcc -DHAVE_CONFIG_H -I. -I. -O2 -fPIC -m64 -Wall -c redblack.c
```

丢掉 `-fPIC` 会让 **shared 构建出问题**，丢掉 `-O2` 是质量问题。

修法（tarball 自带 `Makefile.in` 且不跑 autoreconf，**两份都要改**）：
- `Makefile.in`: `CFLAGS = -Wall` → `CFLAGS = @CFLAGS@ -Wall`
- `Makefile.am`: `CFLAGS=-Wall` → `AM_CFLAGS=-Wall`（automake 惯用法）

既保住上游的 `-Wall` 意图，又让 toolchain 标志生效。

## 3. rbgen：Python 2 时代的生成器

`rbgen` 由 `configure` 生成（`#!@PATH_PYTHON_PROG@`），默认 `--with-rbgen=yes`，
用途是从 `example4.rb` 生成 `example4.c`。它是 Python 2 时代产物，在本机
Python 3 下直接：

```
TabError: inconsistent use of tabs and spaces in indentation
make[1]: *** [Makefile:715: example4.c] Error 1
```

上游对它的缺失**有显式 fallback**：

```make
example4.c: example4.rb
	## Create a dummy example4.c in case rbgen isn't present
	echo 'int main() { return(0); }' > example4.c
```

所以用 `--without-rbgen` 即可得到干净、无依赖的构建，库与其余示例不受影响。
（`noinst_PROGRAMS` 里的 `example4` 是**无条件**的，只有 `.rb.c` 后缀规则在
`if USE_RBGEN` 里——这点读 Makefile.am 时容易看漏。）

## 4. 落选方案记录
- **不打补丁、直接 `--without-rbgen`**：能避开 rbgen，但 config.guess/sub 与
  Makefile CFLAGS 的问题依然存在，真机必挂。
- **让 Makefile.am 保持 `CFLAGS=`、只靠环境变量**：makefile 的赋值优先级高于
  环境变量，改了也没用——必须改文件本身。

## 5. WSL 侧完整 `conan create` 实测（clang profile）

```
libredblack/1.3: Apply patch (portability): config.guess ... (共 4 个补丁全部干净 apply)
libredblack/1.3: Package created
test package: ./test_libredblack
ok × 13  (all libredblack consumer checks passed)
```

消费者测试按 200 个键**降序**插入（红黑树最坏输入），再断言查找/最小/最大/
遍历顺序/范围查询/删除共 13 项。

## 6. 待真机验证内容（READY_FOR_HARMONY 清单）

1. `conan create`（clang 15 / aarch64-ohos）：四个补丁后 configure 能否识别
   三元组、HMDFS 下临时目录是否可用
2. `--without-rbgen` 的 fallback 路径在真机是否如预期（example4.c 打桩）
3. 消费者 13 项断言（纯数据结构逻辑，与平台无关，理论上应与 x86_64 一致）
4. 库包无 bin/ → 确认不需要 commands.json
