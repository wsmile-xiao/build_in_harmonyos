# plink 1.07 适配笔记

## 这是哪个 plink（选型期第一结论，别再猜）

任务池条目 #9582 写的是 `plink / 1.07`，无 URL。第一直觉会去查 PuTTY 的 plink
（`putty-tools`），但 **PuTTY 最新版是 0.85，根本没有 1.x 系列**，
`https://the.earth.li/~sgtatham/putty/1.07/` 实测 404。

真正的 plink 1.07 是 **PLINK**（Harvard/BWH，Shaun Purcell），全基因组关联分析
工具集，2009-08-10 发布。判据是 Debian 源码包 `plink`：`Homepage:
http://zzz.bwh.harvard.edu/plink/`、`Section: science`、
`Build-Depends: libcrypt-dev, zlib1g-dev`、orig 归档 `plink_1.07.orig.tar.gz`
（2009-10-23）。它是 92 个 `.cpp` + 32 个 `.h` 的纯 C++ 程序，与任务池 `lang=cpp` 一致
（R47 语言预检按字节统计：cpp 2,236,574 B / c 0 B = 100% C++）。

## 编译环境

- 构建系统：makefile（上游手写单一 `Makefile`，无 configure、无 install、无 make check）
- 编译日期：2026-10-03
- 编译器：clang 15，`--target=aarch64-linux-ohos`（由 profile `ohos-aarch64-wsl` 的
  `tools.build:compiler_executables` 指定；配方只读该 conf，不硬编码任何本机路径）
- profile：`ohos-aarch64-wsl`（host/build 同 profile）
- 状态：built（`conan create` rc=0，test_package 37/37 断言通过）

## 源码获取

上游历来只公开预编译二进制（`zzz.bwh.harvard.edu/~zhou/plink/`），1.07 的源码
tarball 自 DFSG 重打包约定起**仅由 Debian 一侧长期再分发**。因此 conandata 取
Debian 官方权威镜像的 orig 归档：

```
https://deb.debian.org/debian/pool/main/p/plink/plink_1.07+dfsg.orig.tar.xz
sha256 e11a1573101ca1a930f44db02050cd27790fec055fc6abcc0ebaad59fc99a5dd
```

sha256 直接取自 **GPG 签名的 `plink_1.07+dfsg-5.dsc`** 的 `Checksums-Sha256`
字段（不是自己算完就算数），属 R39 的「权威镜像 + 可校验」。归档顶层目录
`plink-1.07-src/`，recipe 用 `strip_root=True` 剥掉。下载走 conan 的
`core.sources:download_cache`，CI 与本地同源。

## 编译步骤

```sh
make SYS=UNIX \
  CXX="<conf 里的 C++ 编译器> -isystem <zlib 的 include>" \
  LIB="-ldl -lcrypt -L<zlib 的 lib> -lz -lpthread -lm" \
  -j4
```

上游 Makefile 的关键开关与本次取值：

| 开关 | 上游默认 | 本次 | 说明 |
|---|---|---|---|
| `SYS` | `UNIX` | `UNIX` | 加 `-DUNIX`；`WIN`/`MAC`/`SOLARIS` 分支与 OHOS 无关 |
| （未设） | — | 保持静态 | `ifndef FORCE_DYNAMIC` → `CXXFLAGS += -static` |
| `WITH_R_PLUGINS` | `1` | 保持 `1` | 编 `r.cpp`/`Rconnection.cpp`（Rserve 客户端），`LIB += -ldl -lcrypt` |
| `WITH_ZLIB` | `1` | 保持 `1` | 编 `zfstream.cpp`，`LIB += -lz` |
| `WITH_LAPACK` | 空 | 保持空 | 上游默认不链 LAPACK（`LIB_LAPACK` 写死 `/usr/lib/liblapack.so.3`，链了反而依赖宿主） |

**两个上游默认值都原样保留，没有为了「好编」而裁剪功能**：R 插件和 zlib 支持都在产物里，
`libcrypt` 也真的链了。

### 为什么 CXX/LIB 走命令行而不改 Makefile

上游 Makefile 只对 `CXXFLAGS` 做 `+=`，**没有 `CPPFLAGS`/`LDFLAGS` 钩子**。而 make 的
命令行变量会覆盖 Makefile 内的赋值——如果为了塞 zlib 路径而命令行传 `CXXFLAGS=...`，
Makefile 内部的 `-O3 -I. -DUNIX -static -DWITH_R_PLUGINS -DWITH_ZLIB` 会**全部失效**。
所以 zlib 的 include 路径并进 `CXX`、lib 路径并进 `LIB`，上游每一个开关的判定都原样生效。
（`jamnntpd` 1.3 是同一手法：`make ... CC="clang -D__LINUX__ ..."`。）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `sets.cpp:771:37: error: redefinition of 'i' with a different type: 'vector<Individual*>::iterator' vs 'int'` | `Set::profileTestScore()` 里 `for (int i=0; ...)` 的 `i` 仍在作用域内，后面又声明 `vector<Individual*>::iterator i`；2009 年的 gcc 3.x 之前接受，现代 clang/gcc 按 C++ 作用域规则判**硬错误**。同型问题另见 `elf.cpp`（`map<int,int>::iterator i`）与 `idhelp.cpp`（`set<IDField*>::iterator j`） | `patches/0001-nested-iterator-shadowing.patch`：只把迭代器变量改名 `i→i_iter`/`j→j_iter`。算法、控制流、输出零变化。沿用 Debian `debian/patches/gcc-4.7.patch`（Bug-Closed: bugs.debian.org/667325，2012-04-22，已转发上游） |
| 2 | 打了补丁但 `make` 仍报同一个错 | `apply_conandata_patches()` 写在 `build()` 里，而 Conan 是「先 `source()` → 再把源码复制进 build 目录 → 最后 `build()`」：补丁落在导出树 `p/<rid>/s/src`，`make` 编的是**未打补丁的副本** `p/b/<pid>/b/src` | 把 `apply_conandata_patches()` 挪进 `source()`。这是 Conan 2 里唯一正确的位置（`jpegoptim`/`jailkit` 等仓内配方同此） |
| 3 | `layout()` 写 `basic_layout` 也修不好问题 2 | `folders.source`/`folders.build` 同名不等于同一物理目录——前者仍在 `p/<rid>/s` 下 | 显式 `folders.source = "src"` / `folders.build = "src"`，并让 `make` 跑在 `self.build_folder`（即已打好补丁的副本） |
| 4 | 补丁被 Conan 静默跳过（`Apply patch` 有日志但源文件没变） | 手写 unified diff 时**描述段末尾缺一个换行**，`cat` 把散文最后一行和 `--- a/sets.cpp` 粘成一行（`byte-identical.--- a/sets.cpp`），GNU patch 能容错，Conan 的解析器直接当无事发生 | 本包 `patches/0001` 的 diff 段由 `diff -u --label a/<f> --label b/<f>` 生成（描述头单独写文件，拼接时补足结尾换行），生成后校验每个文件的 `^--- ` 与 `^+++ ` 都成对存在 |
| 5 | `self.settings.threads` 不存在 | Conan 2 没有 `settings.threads`（那是 Conan 1.x） | 改用 `self.conf.get("tools.build:jobs")`，缺省回退 `os.cpu_count()`，并**上限 4**：PLINK 有 `elf.cpp`/`model.cpp`/`sets.cpp` 三个超大 TU，`-O3` 下单进程可达数百 MB，32 核机器无脑 `-j32` 会把内存小的 CI worker OOM 掉 |
| 6 | 担心 `-static` 在 CI worker 上没有 `libc.a` | — | 本地实测 DevEco SDK 的 NDK sysroot（`native/sysroot/usr/lib/aarch64-linux-ohos/`）**有** `libc.a`（11MB），产物 `file` 确认为 `statically linked`。CI worker 的 sysroot 未在本环境实测，若那边缺 `libc.a`，把 Makefile 的 `FORCE_DYNAMIC=1` 打开即可改为动态链接（Debian 打包正是这么做的） |
| 7 | `-lcrypt` / `-ldl` 会不会 `cannot find -lcrypt` | glibc 2.28 起把 `crypt()` 挪出了 libc，Debian 才需要 `libcrypt-dev` | OHOS/musl 侧 `crypt`/`dlopen` **本来就在 `libc.a` 里**，sysroot 里的 `libcrypt.a`、`libdl.a` 是 8 字节的空壳归档（只为满足 `-l` 解析）。实测链接通过，无需引入 libcrypt 包 |
| 8 | 系统 zlib 只有 `libz.so` 没有 `libz.a`，而上游默认要静态链接 | OHOS NDK 的 zlib 仅共享库 | 制品仓的 `zlib/1.3.1` 提供 `libz.a`，作 `self.requires("zlib/1.3.1")` 注入。W0 已用 `conan download "zlib/1.3.1" -r=ohpcd --only-recipe` 确认已发布 |

## 上游测试账本

- `N_static = 0`：核对归档 129 个文件，PLINK 1.07 **没有任何测试注册入口**——无
  `configure`、无 `ctest`/`add_test`、无 `make check` 目标。它是 2009 年的分析工具，
  上游从来只发「下载即用」的二进制 + 文档。
- **不靠推断收口**：`build()` 真实跑了一次 `make check`（`ignore_errors=True`），
  conan 日志逐字留下
  `make: *** No rule to make target 'check'.  Stop.`。`N_registered = 0`、
  `N_executed = 0`（上游侧），未执行分类 = 0（不存在可执行项，不是「跳过了 N 个」）。
- `N_consumer = 37`：见下节，全部真实执行并通过。

## 消费者测试设计（补全的测试用例）

上游没测试，所以测试是**从零补**的，用上游自带的 `test.ped`/`test.map`
（6 样本 2 SNP，随包发布到 `share/plink/`），7 组共 37 项断言：

| 组 | 内容 | 断言数 |
|---|---|---|
| T1 | **鸿蒙特有**：读 ELF 头断言 `EI_CLASS=ELF64`、`e_machine=EM_AARCH64(183)`；再真实执行二进制 | 6 |
| T2 | `--freq` 等位基因频率：表头 schema、2 行 SNP、snp1 MAF=0.3333 / NCHROBS=12、snp2 MAF=0.4167 | 8 |
| T3 | `--assoc` 病例-对照关联：表头 schema、2 行、snp1 CHISQ=1.5 / P=0.2207、snp2 CHISQ=3.086 / P=0.07898 | 8 |
| T4 | `--make-bed` 二进制转换：`.bed` magic `0x6c 0x1b 0x01`（SNP-major）、`.bim` 两行与源 `.map` 逐字段一致、`.fam` 6 样本 | 5 |
| T5 | 往返读回：`--bfile plink --freq` 读回 BED，断言 MAF 与 PED 路径**完全相同** | 3 |
| T6 | 错误处理：1.07 不支持的 `--summarize`、不存在的数据集，均须非零退出且 stderr 给出可定位 ERROR | 4 |
| T7 | 声明依赖真实生效：从产物二进制里匹配 zlib inflate/deflate 版本横幅（实测 1.3.1 / 1.3.1） | 3 |

三个设计要点：

1. **按表头名取列，不写死列号**。第一版把 CHISQ/P 写成下标 6/7，被测试自己逮到
   （实际是 7/8，`A2` 占着 6）；改成 `{name: index}` 映射后，同类错误不可能再静默发生。
2. **`--noweb` 必带**。1.07 默认联网做版本检查（`Web-based version check`），无网环境下
   会先卡一下再打 `failed connection`；显式关掉，测试才可离线复现。
3. **断言 `--help` 而不是 `--version` 的退出码**。实测 `--version` 打完横幅后会继续走
   参数解析并以 **rc=1** 退出（上游行为），只有 `--help` 是 rc=0。用错断言会得到一条
   永远红的假失败。

### L1e 反向破坏测试（证明非空壳）

把包改坏三次，每次都要求测试**非零退出**，改回后仍须 37/37 通过：

| 破坏方式 | 测试 rc | 结论 |
|---|---|---|
| 删掉 `bin/plink` | 1 | 检出 |
| `bin/plink` 截断成 1KB 全零 | 1 | 检出 |
| 删掉 `share/plink/test.ped` | 1 | 检出 |
| （对照）原包 | 0，37/37 | 通过 |

完整输出可用下述命令复现（`reports/` 被仓库 `.gitignore` 排除，属每次重生成的临时产物，故不入库）：

```sh
# 把包改坏一次，测试必须非零退出（T116：不要用管道吞退出码）
P=$(conan cache path plink/1.07:<package-id>)
rm -rf /tmp/l1e && cp -r "$P" /tmp/l1e && rm -f /tmp/l1e/bin/plink
python3 test_package/test_plink.py /tmp/l1e ; echo "rc=$?"   # 期望 rc=1
```

## 验证结果

本地（2026-10-03，profile `ohos-aarch64-wsl`）：

- `conan create archives/p/plink/1.07 --name=plink --version=1.07
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing` → **rc=0**
- test_package：**37 项断言，37 通过，0 失败**
- 产物 `file`：`ELF 64-bit LSB executable, ARM aarch64, statically linked`
- 实跑：`plink --file test --freq` / `--assoc` / `--make-bed` / `--bfile` 往返全部 rc=0，
  输出与上游文档给出的数值一致
- CI 同源门禁 `CI_BRANCH=feat/plink-1.07 CONAN_PROFILE=ohos-aarch64-wsl
  CI_PACKAGES="archives/p/plink/1.07" zsh ci/conan/build_and_test.sh` → **rc=0**，
  逐阶段结论见下节

## 门禁结论（本地 CI 同源脚本实测，2026-10-03）

| 阶段 | 结论 | 关键证据 |
|---|---|---|
| G0 知识图谱完整性 | pass | 542 entries |
| G0e 根目录白名单 | pass | — |
| L0i 依赖已发布 (R36) | pass | `dependency in registry: zlib/1.3.1` |
| L0j 版本冲突 (R37) | pass | `version not in registry yet (first publish)` |
| L0k commands.json (R38) | pass | `commands.json valid (type=tool)` |
| L0m 目录结构 (R39) | pass | — |
| L0n 分支名 (R40) | pass | `branch 'feat/plink-1.07' matches 'plink-1.07' exactly` |
| KC 知识图谱质量 | pass | KC1-KC5 全过 |
| JC 杂项文件 | pass | `no junk files detected`（JC1-JC6） |
| conan create | pass | `plink/1.07 — conan create passed` |
| L1 上游测试 + test_package | pass | L1a/L1b/L1c 三项 ok |
| L1e 反向破坏 (R34) | pass | `[sabotage] bin/ moved away` → `test genuinely depends on plink` |
| L2 smoke | pass | `plink --help OK` |
| L4 补丁危险函数扫描 | pass | `patches clean` |
| L5 产物基线 | pass | `bin/ has content` |

> 注：`L1c` 显示 `make check` 已在构建阶段真实执行（`upstream tests executed`），
> 其结论就是上文「上游 0 个测试、仅有 `No rule to make target 'check'`」这一事实，
> 不是「跳过」。

**编译结束**: 2026-10-03
**最终状态**: built
