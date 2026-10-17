# xz 5.8.1 — 适配交付笔记（平台任务 #7343）

> 档案创建时间: 2026-09-21
> 认领人: Zmaomao　　分支: `feat/xz-5.8.1`　　平台任务 id: 7343
> 构建系统: autotools (configure + make)　　SDK: OHOS SDK v7.0 / clang 15.0.4
> 上游: https://github.com/tukaani-project/xz/releases/download/v5.8.1/xz-5.8.1.tar.gz
> sha256: `507825b599356c10dca1cd720c9d0d0c9d5400b9de300af00e4d1ea150795543`

## 一、任务背景

平台任务 #7343 要求适配 xz 5.8.1。制品仓已有同族 5.4.5 / 5.6.2 / 5.8.3 /
5.8.3.1 / 5.8.3.2，**唯独没有 5.8.1**（已用 `conan list 'xz/*' -r=ohpcd` 复核，
L0j/R37 通过）。本目录以 `archives/x/xz/5.8.3` 的配方为基底，按新版本重建。

## 二、源码与校验

| 项 | 值 |
|---|---|
| 官方 URL | `https://github.com/tukaani-project/xz/releases/download/v5.8.1/xz-5.8.1.tar.gz` |
| 大小 | 2,587,189 字节 |
| sha256 | `507825b599356c10dca1cd720c9d0d0c9d5400b9de300af00e4d1ea150795543` |
| 确认方式 | **3 条独立通路分别下载后逐字节比对一致**（ghproxy.net / gh-proxy.com / 本地落盘件），与 `scripts/ohos/resolve-sha256.sh` 的多源口径一致 |

`conandata.yml` 只写**上游官方源**（R39/PF7：不手写镜像前缀，镜像回退由 CI 自动处理）。

## 三、OHOS 适配点

| # | 问题 | 根因 | 处置 |
|---|---|---|---|
| 1 | `configure` 认不出 HarmonyOS | `build-aux/config.guess` 无 HarmonyOS 分支 | `patches/0001-build-aux-config.guess.patch`：新增 `*:HarmonyOS:*:*` → `<machine>-unknown-linux-ohos`。**已实测该补丁可原样套用到 5.8.1**（`patch -p1 --dry-run` 通过）。`config.sub` 5.8.1 已内置 `ohos*` / `linux-ohos*`，无需补丁 |
| 2 | `config.status` 建临时目录失败 | OHOS 上 `mktemp -d` 造出 `drwx--S---` 的坏权限（E011） | `generate()` 里放一个**同名 mktemp wrapper**（`exit 1`），迫使 autoconf 的 `AS_TMPDIR` 走 `mkdir` 回退路径 |
| 3 | 上游脚本（xzdiff/xzgrep/xzless）装出来是坏的 | OHOS 无 `/bin/sh` | `--disable-scripts`：不装脚本，同时不注册 `test_scripts.sh` |
| 4 | **交叉编译时上游测试全挂** | 测试/CLI 都是 **libtool** 驱动链接。libtool 会把裸 `-static` 当成自家参数消费掉、不转发给编译器 → 程序实际是**动态**的（`readelf` 可见 `INTERP = /lib/ld-musl-aarch64.so.1`）。而 OHOS SDK **不随附**设备端加载器，本机 QEMU/binfmt 跑不起来 → `make check` 18 项全 FAIL（`Could not open '/lib/ld-musl-aarch64.so.1'`） | 交叉编译时改用 libtool 的 **`-all-static`**（正确转发，程序变真静态）。**仅 `cross_building` 时启用**，设备端原生构建保持上游默认，与已发布的 xz/5.8.3 一致 |
| 5 | `test_package` 在交叉编译下链接失败 | 原生写法直接调 `clang`（=宿主 x86-64 编译器）去链 aarch64 的 `liblzma.a` → `skipping incompatible .../liblzma.a` | `cross_building` 时改取 profile 里配置的交叉编译器（`tools.build:compiler_executables.c`）并加 `-static`；设备端原生构建仍走系统 `clang`，命令与 5.8.3 一致 |

> 第 4/5 条是本任务相较 5.8.3 目录**唯一的配方差异**，目的都是让"上游测试 + 消费者测试"
> 能在本机**真实执行**（而不是"看起来成功"）。设备端构建路径未改。

## 四、上游测试口径（不编造，逐个可查）

`tests/Makefile.am` 的 `TESTS` 变量（上游默认形态）：

```
TESTS 基础 17 = 12 个 C 测试二进制
                （test_check / test_hardware / test_stream_flags / test_filter_flags /
                  test_filter_str / test_block_header / test_index / test_index_hash /
                  test_bcj_exact_size / test_memlimit / test_lzip_decoder / test_vli）
              + test_files.sh + test_suffix.sh
              + test_compress_generated_{abc,random,text}
COND_MICROLZMA（configure.ac:305 默认 enable_microlzma=yes）  + test_microlzma
COND_SCRIPTS  （configure.ac:529 默认 enable_scripts=yes）    + test_scripts.sh
```

- **上游默认注册 N = 19**
- 本适配用 `--disable-scripts` → COND_SCRIPTS 关闭 → **实际注册并运行 18 项**
- 豁免 1 项：`test_scripts.sh`（OHOS 无 `/bin/sh`，平台限制）

## 五、本地实测结果（★ 全部为真实执行，非推断）

在本机 WSL（x86-64）用 `scripts/ohos/build-xz.sh` 执行
`conan create . -pr:h=conan-profile-ohos-aarch64.local -pr:b=conan-profile-linux-x86_64.local`：

```
conan create exit=0

上游 make check（tests/test-suite.log 权威汇总）
  # TOTAL: 18
  # PASS:  18        ← 100%
  # FAIL:  0
  # ERROR: 0

test_package 消费者测试（conan create 日志原文）
  RUN: /home/.../env/ohos-cc -static -o test_xz test_xz.c -I... -L... -llzma
  RUN: ./test_xz
       Compressed 74 bytes to 132 bytes
       Decompressed 74 bytes — round-trip OK
       liblzma version: 5.8.1
  RUN: python3 '.../test_xz.py' '.../p/bin'
       OK: xz 5.8.1 CLI round-trip ok (compress/decompress)
```

产物架构与可执行性（`readelf` / 直接执行，走 binfmt+QEMU）：

| 产物 | 结果 |
|---|---|
| `lib/liblzma.a` | `Class: ELF64` / `Machine: AArch64` ✅ |
| `bin/xz` `bin/xzdec` `bin/lzmadec` `bin/lzmainfo` | `Machine: AArch64`，静态链接（`INTERP` 段数 0） |
| `bin/xz --version` | `xz (XZ Utils) 5.8.1` / `liblzma 5.8.1`，退出码 0 ✅ |
| 200 KB 随机数据 CLI 往返 | 压缩 200,080 字节 → 解压后 `sha256` 与原文**逐字节一致** ✅ |

## 六、局限（如实说明）

1. `--disable-scripts` 使 `test_scripts.sh` 不运行 → 报告口径为 **18/18**，不是 19/19；
   该用例只验证 xzdiff/xzgrep 等 shell 脚本，与 liblzma/xz 本体无关。
2. 本机是**交叉编译 + QEMU** 执行，与官方 CI 的**设备端原生编译**不等价；
   OHOS 特有行为（HMDFS 语义、ELF 签名等）本地无法覆盖，**本地层不替代 CI**。
3. 5.8.1 不含 CVE-2026-34743 修复（该修复随 5.8.3 引入）；本任务按平台要求适配该版本，
   未改动上游源码语义。
4. `lib/` 下只有 `liblzma.a`（无 `.so`）——与制品仓已发布的 xz/5.8.3 包一致
   （已下载 5.8.3 制品逐项对比确认）。

## 七、复用知识

- **E007**：`config.guess` 不识别 OHOS → 补 `*:HarmonyOS:*:*` 分支
- **E011**：`mktemp -d` 权限缺陷 → mktemp wrapper 走 `mkdir` 回退
- **新增（本轮）**：**libtool 会吞掉裸 `-static`**——交叉编译时若要让程序真正静态链接，
  必须用 libtool 的 `-all-static`；判据是 `readelf -l <bin> | grep INTERP`
  （有 `INTERP` 即仍是动态）。这条同样解释了为什么"配方里明明写了 -static，
  产物却还是动态"。
- **新增（本轮）**：`test_package` 若写死 `clang`，在交叉编译下会调用宿主编译器导致
  `skipping incompatible ... .a`；应按 `cross_building` 取 profile 的交叉编译器。
