# slgsl：`uname -s` = HarmonyOS 击穿旧 autotools 脚本 + slsh 测试环境

> 配套结构化条目：`DRAFT-slgsl-config-guess-harmonyos-umask-and-slsh-rc.kv`

## 现象（4 个连续失败）

```
config.guess: unable to guess system type
configure: error: cannot guess build type; you must specify one
./config.status: line 603: ./confbtQOpl/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
prepend_to_slang_load_path is undefined
```

## 坑 1：设备 `uname -s` 返回 **HarmonyOS**（不是 Linux）

```sh
$ uname -s -m
HarmonyOS aarch64
```

2018 版 `config.guess` 的分派是 `Linux|GNU|GNU/*)`，遇到 `HarmonyOS` 直接
"unable to guess"。

**关键**：不能只把 `HarmonyOS` 塞进那个 case —— 该分支内部会**编译一段
`dummy.c` 探针**来判断 libc 类型，而设备上 `/tmp` 只读、`mktemp -d` 受
restrictive umask 限制，探针必然失败，最后仍报 guess 失败。

正确做法是**直接判定并 exit**：

```sh
case "$UNAME_SYSTEM" in
HarmonyOS)
    case "$UNAME_MACHINE" in
        aarch64|arm64) GUESS=aarch64-unknown-linux-ohos ;;
        *)             GUESS="$UNAME_MACHINE-unknown-linux-ohos" ;;
    esac
    echo "$GUESS"
    exit ;;
Linux|GNU|GNU/*)
    ...
```

## 坑 2：旧版 `config.sub` 必须**三处齐改**

| # | 位置 | 漏改后果 |
|---|------|----------|
| 1 | `maybe_os` 列表加 `linux-ohos*` | `aarch64-unknown-linux-ohos` 不被识别为 KERNEL-OS |
| 2 | OS 合法性列表加 `-linux-ohos*` | 被判为非法系统 |
| 3 | 在通用 `-linux*)` **之前**加 `-linux-ohos*) os=-linux-ohos ;;` | 被改写成 **`linux-gnu-ohos`** |

实测对比：

```
修复前: config.sub aarch64-unknown-linux-ohos → aarch64-unknown-linux-gnu-ohos
修复后:                                       → aarch64-unknown-linux-ohos
```

## 坑 3：`configure` 的 `umask 077` 临时目录（hmdfs）

```sh
# configure 生成
{
  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
  test -d "$tmp"
} || { tmp=./conf$$-$RANDOM; (umask 077 && mkdir "$tmp"); } || as_fn_error ...
```

hmdfs 下 `umask 077` 建出的目录**属主是本会话却不可写**（且同会话 `chmod`
是空操作，实测无效），于是 `config.status` 无法创建其 awk 辅助脚本：

```
./config.status: line 603: ./confbtQOpl/subs1.awk: Permission denied
```

改 `umask 022` 即可（SDL / inn2 同款补丁）。

## 坑 4：必须源码内构建

上游 `configure` 有显式检查：

```sh
cd $srcdir
if test "`pwd`" != "$CONFIG_DIR"; then
  as_fn_error ... "This software does not support configuring from another directory."
fi
```

→ 配方 `layout()` 设 `self.folders.build = "."`。

## 坑 5：slsh 跑上游测试需要三个环境变量

上游 `src/Makefile` 的 `check` 目标遍历 `src/tests/test_*.sl` 用 `slsh` 执行，
而每个测试脚本首行是：

```slang
prepend_to_slang_load_path (".");
set_import_module_path (".:" + get_import_module_path ());
```

`prepend_to_slang_load_path()` **仅由 slang 包的 `etc/slsh.rc` 定义**。
slsh 通过 `SLSH_CONF_DIR` 找 `slsh.rc`，而 `slsh.rc` 自身又执行
`prepend_to_slang_load_path (getenv (SLSH_PATH_ENV))` —— 所以缺任一都失败：

```
prepend_to_slang_load_path is undefined
```

配方据此设置：

```python
SLSH_CONF_DIR     = <slang>/etc
SLSH_PATH         = <slang>/share/slsh  (+ <pkg>/share/slsh/local-packages)
SLANG_MODULE_PATH = <pkg>/lib/slang/v2/modules   # 编译模块的 dlopen 路径
```

其中 `SLANG_MODULE_PATH` 是为**消费/运行**编译出的 `*-module.so` 所需
（否则 `Error linking to gsl-module.so: ... No such file or directory`）。

## 验证结果

- 上游：`make check` 通过（6 个测试：import/err/fft/interp/integ/rand）
- 消费者：`sample mean 0.017475 over 1000 draws`、
  `c = 2.99792e+08 m/s` → `SLGSL-CONSUMER-OK`

## 通用教训

1. **HarmonyOS 主机的 `uname -s` 不是 Linux** —— 任何自带旧
   `config.guess`/`config.sub` 的 autotools 包都要按上述方式补，
   且 config.guess 要"直接判定"而非"并入 Linux 分支"。
2. `CMAKE_*`/autotools 在 hmdfs 上的 `umask 077` 坑是**系统性**的，
   凡 configure 都要预备。
3. 依赖解释器动态加载模块的项目（S-Lang/Python/Tcl…），
   运行环境变量（`SLANG_MODULE_PATH` 等）必须由 `package_info()` 为
   消费者铺好，否则包"构建成功但用不了"。
