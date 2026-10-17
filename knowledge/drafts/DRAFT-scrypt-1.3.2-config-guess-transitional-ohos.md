# DRAFT-scrypt-1.3.2-config-guess-transitional-ohos — 2016-2018 transitional config.guess/config.sub 的 OHOS 补丁

## 现象 (What happened)

对 scrypt 1.3.2（捆绑 2018-08-29 版 GNU config 脚本，位于 config.aux/）
做 OHOS PC 原生构建时：

1. 未打补丁：`sh config.aux/config.guess` 报 `unable to guess system type`
   退出 1；`./configure` 报 `cannot guess build type`。
2. 按知识库 E007 运行官方工具
   `scripts/patch-autotools-ohos.pl config.aux/config.guess config.aux/config.sub`：
   自检 **cg=1 sub=0**（config.guess 命中并插入 HarmonyOS 分支，config.sub
   三处全部跳过），但**真机验证 `sh config.guess` 依然失败**：
   `unable to guess system type`。

## 根因 (Root cause)

2016-2018 过渡格式（transitional）脚本介于新旧两代之间，官方 perl 工具
两头都锚不准：

| 脚本 | 工具锚点 | transitional 脚本实际情况 | 结果 |
|------|---------|--------------------------|------|
| config.guess | `*:NetBSD:*:*` case 前插入块 | 能命中，但插入块仅 `GUESS=${MACHINE}-unknown-linux-ohos` 赋值，**缺 `echo "$GUESS"` 与 `exit 0`** | 赋值后落入默认路径 → 仍报 unable to guess |
| config.sub ① | `android-linux)` 三行块（要求 `basic_os=linux-android`） | 块存在但用 `os=linux-android`（2016 前字段名） | 正则不匹配，跳过 |
| config.sub ② | OS 列表 `gnu* | android*` 后加 ohos* | 2018 版该列表是 `midipix* | mingw32* | linux-gnu* | linux-android*` 连续行 | 不匹配，跳过 |
| config.sub ③ | `linux-uclibc*` 结尾括号加 `| linux-ohos*` | 2018 版内核列表与 OS 列表合并写法不同 | 不匹配，跳过 |

本机实测（HarmonyOS aarch64, clang 15）：手工补齐后 config.guess 输出
`aarch64-unknown-linux-ohos`，config.sub 双向接受（原串与
`aarch64-unknown-linux-gnu-ohos` 规范化形式均 OK），configure 通过。

## 解法 (Fix)

手工 portability 补丁（本 PR `archives/s/scrypt/1.3.2/patches/`）：

1. **config.guess**：HarmonyOS 分支补 `echo "$GUESS"` 与 `exit 0`（工具插入的
   代码只有赋值，缺输出与退出）。
2. **config.sub 三处**：
   - `android-linux)` 块后新增 `ohos-linux)` 块：
     `basic_machine=$field1-unknown` + `os=linux-ohos`；
   - OS 类型列表（`midipix* | mingw32* | mingw64* | linux-gnu* |
     linux-android*` 行）追加 `| ohos*`；
   - 同一列表行追加 `| linux-ohos*`（2018 版 OS 与内核列表合并在同一行，
     与 E564 的双列表情况不同）。

## 验证 (Verification)

```bash
sh config.aux/config.guess                          # → aarch64-unknown-linux-ohos
sh config.aux/config.sub aarch64-unknown-linux-ohos        # 原样接受
sh config.aux/config.sub aarch64-unknown-linux-gnu-ohos    # 规范化形式也接受
./configure 2>&1 | tail -3                          # build system 判定通过
```

## 适用边界 (Scope)

捆绑 2016-2018 transitional config.guess/config.sub（config.guess 用 `GUESS=`
赋值、config.sub 的 `android-linux)` 块用 `os=` 而非 `basic_os=`）的 autotools
包。判别命令：`grep -c '^GUESS=' config.guess` > 0 且
`grep -c 'os=linux-android' config.sub` > 0。

## 与既有知识的关系

- similar_to: **DRAFT-E564**（2012-2015 旧式换锚点；本条目是 2016-2018
  过渡格式：android-linux 块存在但字段名不同、config.guess 分支缺 echo/exit）
- E007 覆盖新式脚本（perl 工具可直接打）；本条目覆盖过渡格式（工具部分成功
  即损坏，必须手工补）。