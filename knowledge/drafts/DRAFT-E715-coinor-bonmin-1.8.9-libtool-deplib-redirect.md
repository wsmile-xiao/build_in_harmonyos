# DRAFT-E715 — coinor 族 autotools 在 OHOS 的四连坑与正解

> 软件：coinor-bonmin 1.8.9（同族 cbc/2.10.13、clp、coinor-ipopt 实测互证）
> 取号：`knowledge_id.py --claim` → **E715**（2026-09-24）
> 结构化条目见同名 `.kv`（`yaml.safe_load` 可回读、`prescan_pattern` 可 `re.compile`）。

## 1. 症状（四条错误签名，同一包内先后命中）

```text
libtool: link: `//lib/libCbc.la' is not a valid libtool archive
make[2]: *** [Makefile:503: libbonmin.la] Error 1
```
```text
configure: Overruling autoconf; cl does not recognise -g.
checking for COIN-OR package CoinDepend... skipped check via pkg-config, redirect to fallback
configure: error: Required package Cbc or Ipopt not available.
```
```text
./config.status[1162]: can't create ./confstatOGAdHO/out: Permission denied
config.status: creating Makefile
configure: Configuration of Bonmin successful      # rc=0，但 Makefile 一个都没生成
```
```text
Error relocating ./unitTest: _ZN5Ipopt17RegisteredOptions…: symbol not found   # exit 127
```

## 2. 根因与处置

| # | 根因 | 错误处置（已实测踩坑） | 正解 |
|---|------|------------------------|------|
| 1 | ohpcd coinor 族包以 `--prefix=/`+DESTDIR 安装，`.la` 内 `libdir='//lib'` 无效 | — | 见 ② |
| 2 | libtool 经 `-L` 解析到这些 `.la` | 照 cbc 方案 B 把 `-l*` 换**绝对 .a 路径** ⇒ libtool 把 file-arg 归档**合并进本包静态库**：`libbonmin.a` 1,718,842,488 B、成员内嵌 18 个依赖 `.a`（cbc 包 250MB 同机制） | 把**带 .la 的依赖包**的 `.a` 符号链接汇到 build 内 `dep-libs/`（只放 .a、无 .la），再把 Makefile 中这些包的 `-L` 重定向过去：`.la` 找不到、`-l` 语义保留、不合并（实测 2.8MB / 成员 62 / 嵌套 `.a`=0） |
| 3 | coin BuildTools m4 `case "$CC" in clang*) ;; cl* \| */cl* …`：**绝对路径** `/data/service/hnp/bin/clang` 含 `/cl` ⇒ 判 MSVC ⇒ `coin_cc_is_cl=true` ⇒ `--enable-pkg-config` 默认关、pkg-config 探测整体跳过 | 传绝对 CC/期望 PATH 兜底 | `CC=clang CXX=clang++` **裸名** + 显式 `--enable-pkg-config`；断言日志出现 `checking pkg-config is at least version` |
| 4 | `config.status` 的 `umask 077 && mktemp -d`（0700）在 HMDFS 落 `drwx--S---`，目录内写不进 | 采信 rc=0 继续 make | 改 `mkdir -p conftmp` + `umask 022`（E678/cbc conftmp 同款），并**断言产物真存在**（Makefile/config.h/bonmin.pc/libtool）才进 make |
| 5 | 测试运行期 `libipopt.so` 未进 `LD_LIBRARY_PATH` | — | build() 内显式注入各依赖 `lib/`；test_package 走 `env="conanrun"` |

## 3. 反静默教训（本次新踩）

`find … -exec sed -i … {} \;` 里写成 `{{}}`（Python `.format()` 习惯残留、实际用的是 `%` 格式化）
⇒ **字面量 `{{}}` 不是占位符**，sed 拿不到文件参数、rc=0 静默 no-op，`self.run` 照样绿，
下一步 libtool 才爆 `.la` 错——症状离根因隔了一层。**修法**：每个 fix 步骤后加
「残留计数断言」（`grep -lF … \| wc -l` 必须为 0，否则 rc≠0 硬停）+ 关键产物断言。

## 4. 复现（设备可执行）

```sh
# 沉淀位置：$HOME/tmp/coinor-bonmin-1.8.9/{explore-configure.log,explore-make.log,
#           explore-make4.log,explore-test2.log,cc1.log,cc2.log} + 包内 notes.md
test "$(llvm-ar t <build>/src/CbcBonmin/.libs/libbonmin.a | grep -c '\.a$')" = 0   # 好=0，坏=18
grep -c "skipped check via pkg-config, redirect to fallback" <build>/config.log     # 好=0
for f in Makefile src/Interfaces/config.h bonmin.pc libtool; do test -f "$f" || echo "MISSING $f"; done
```

## 5. 适用面

一切消费 ohpcd coinor 族**静态**依赖的 autotools/libtool 下游包；一切用绝对 CC 路径跑
coin BuildTools 生成的 configure 的配方；一切在 HMDFS 上用 autoconf 2.5x `config.status` 的包。
