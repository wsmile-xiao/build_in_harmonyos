# open-jtalk 1.11 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，in-tree）
- 编译日期: 2026-09-13
- 编译器: clang / clang++ (OHOS SDK 15.0.4)，conan profile `ci/conan/profiles/ohos-aarch64`
- 设备: HarmonyOS PC aarch64（native 构建，非交叉）
- 状态: built

## 编译步骤

1. `conan create archives/o/open-jtalk/1.11 -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>`
2. `source()`：下载 open_jtalk-1.11.tar.gz，并按 `conandata.yml` 的 `private_sources`
   把 hts_engine_API-1.10.tar.gz 解到 `<source>/_deps/hts_engine_API`。
3. `build()`：
   - `apply_conandata_patches` 打 open_jtalk 的 0001/0002；
   - `_apply_private_patches()` 用 `patch()` 把同一份 config.guess/config.sub 锚点补丁
     （两个 tarball 的该两文件字节相同）加 hts_engine 专用补丁打到
     `<source>/_deps/hts_engine_API`；
   - `_pin_autotools_timestamps()` 把两棵树的 autotools 输入统一到同一历史时间戳；
   - 在 `<build>/_hts_engine/build` 中 out-of-tree 配置并安装 hts_engine_API 到
     `<build>/_hts_engine/prefix`；
   - 在源码树内（`build_folder == source_folder`）配置 open_jtalk，
     `--with-hts-engine-header-path/-library-path` 指向上面的私有 prefix，
     然后 `make -j1`、`make check -j1`。
4. `package()`：`make install`（DESTDIR=package_folder）装出 `bin/open_jtalk` 与 `dic/`，
   另附 `licenses/COPYING`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | out-of-tree（VPATH）构建报 `No rule to make target '<src>/text2mecab/libtext2mecab.a'` | `bin/Makefile.am` 的 `open_jtalk_LDADD` 用 `@top_srcdir@` 绝对路径引用各子目录静态库，而 automake 把 `.a` 产在 build dir | `layout()` 固定 `build_folder == source_folder`（`basic_layout(src_folder=".", build_folder=".")`），in-tree 构建 |
| 2 | 2013 版 config.guess 在 HarmonyOS 上 `unable to guess system type`；config.sub 报 `Invalid configuration 'aarch64-unknown-linux-ohos': system 'ohos' not recognized` | tarball 自带旧式（无 `GUESS=` 变量）2013 版 config.guess/config.sub，两者都不认识 `uname -s` = HarmonyOS | 按 E564 用手工最小锚点补丁（0001，共 2 文件 3 处）：config.guess 在 `aarch64:Linux:*:*)` 前插入 `aarch64:HarmonyOS:*:*)` 运行时分支直接 `echo ${UNAME_MACHINE}-unknown-linux-ohos`；config.sub 补 `linux-ohos*` 双锚点（maybe_os 行 + basic os 列表行）。E007 的 `patch-autotools-ohos.pl` 锚点取自 2023 版脚本，对本包旧式脚本不适用 |
| 3 | （改用锚点补丁后不再出现）早期整文件替换 2023 版 config.guess 时，脚本自身 `umask 077` 临时目录写 `dummy.c` 失败 | 整文件替换版会在 case 匹配前先编译探测程序；锚点分支在 case 阶段即命中并 `exit`，不再触发该路径 | 已由 0001 锚点方案规避；`umask 077` 的剩余风险点只有 configure（第 4 行） |
| 4 | configure 报 `cannot create ./confXXXXXX/subs1.awk: Permission denied` | configure 为 config.status 建临时目录时用 `umask 077`，HMDFS 下 0700 目录对构建用户不可写 | 0002 把 configure 中 2 处 `umask 077` 改为 `umask 022`（E011 口径） |
| 5 | hts_engine_API 无处可依赖（configure 硬要求头文件 + 静态库） | hts_engine_API 未发布到 ohpcd Conan 制品仓（`conan list 'hts_engine/*' -r=ohpcd` = 0 条），也不在 cmd-pkgs 预编译索引（1248 个包）中 | 用 `private_sources` 在配方内私有构建 1.10 并静态链接（同 `archives/a/aws-c-http` 做法），不新增独立包 |
| 6 | hts_engine_API 编译 `lib/HTS_misc.c` 报 `no member named '__pos' in 'union _G_fpos64_t'` | OHOS SDK 26 的 `fpos_t` 是 `union _G_fpos64_t { char __opaque[16]; long long __lldata; double __align; }`，无 glibc 的 `__pos` 成员 | hts_engine 0002 补丁把 `HTS_ftell()` 改用可移植的 `ftell()`（与 `HTS_fseek()` 的 `fseek` 语义一致）；已沉淀草稿 `knowledge/drafts/E6342-draft-4A7C.md` |
| 7 | conan 构建（profile `cppstd=17`）报 `ISO C++17 does not allow 'register' storage class specifier` | 内置 MeCab 0.996 是 C++98 代码，用了 C++17 删除的 `register` | `tc.extra_cxxflags.append("-Wno-register")`（`archives/a/autodocksuite` 同法）；native 手工构建不传 `-std=c++17` 故未暴露 |
| 8 | 补丁导出后路径嵌套（`patches/hts_engine/patches/hts_engine/...`） | `copy()` 默认保留源码相对路径 | `copy()` 的源目录直接取 `recipe_folder/patches/hts_engine`，目标为 `export_sources/patches/hts_engine` |
| 9 | hts_engine 的 configure 补丁直接套用 open_jtalk 的补丁文件时 patch_ng 报 `premature end of source file` | 两个 configure 行号不同（7655 vs 5823），toybox `patch` 能模糊命中而 patch_ng 不能 | 按 hts_engine 自身源码重新生成该补丁，并用 `patch_ng.fromfile(...).apply(strip=1)` 回验 |
| 10 | 预查询（G0）命中 E490：autotools helper 脚本可能丢失执行位 | 部分 OHOS 适配链路保留内容但不保留 POSIX 执行位，configure 会以 `Permission denied` 提前失败 | 配方 `_restore_autotools_modes()` 在 configure 前对 `configure`/`config.guess`/`config.sub`/`install-sh`/`missing` 等已知脚本恢复执行位（两棵树都做） |

## 源码修改（补丁）

| 文件 | 目标 | 内容 |
|------|------|------|
| `patches/0001-config-guess-sub-ohos.patch` | open_jtalk + hts_engine_API | config.guess 加 `aarch64:HarmonyOS:*:*` 运行时分支；config.sub 加 `linux-ohos*` maybe_os 锚点与 basic os 列表锚点（无 `__OHOS__` 宏） |
| `patches/0002-configure-hmdfs-umask.patch` | open_jtalk | configure 内 2 处 `umask 077` → `umask 022` |
| `patches/hts_engine/0001-configure-hmdfs-umask.patch` | hts_engine_API | configure 内 2 处 `umask 077` → `umask 022` |
| `patches/hts_engine/0002-HTS_misc-use-ftell.patch` | hts_engine_API | `HTS_ftell()` 由 `fgetpos` + `pos.__pos` 改为 `ftell()` |

四个补丁都不能由 `refresh-patch --auto` 生成：0001/0002 的基线是上游 tarball 原样文件（手工 diff），
`patches/hts_engine/*` 的目标树是配方内私有下载的 hts_engine_API（不在本包源码树内，工具不可达）。
四者均以 `patch_ng.fromfile(...).apply(strip=1)` 回验，并由真实 `conan create` 的 `Apply patch` 日志确认生效。

未修改上游任何测试用例（上游本就没有测试目标）。

## 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| hts_engine_API | 1.10 | SourceForge 官方 tarball，sha256 `e2132be5860d8fb4a460be766454cfd7c3e21cf67b509c48e1804feab14968f7` | **私有内建**（`private_sources`），静态链接进 open_jtalk；未发布为独立 Conan 包 |
| clang / clang++ | 15.0.4 | OHOS SDK（profile `tools.build:compiler_executables`） | — |
| libc++_shared.so / libc.so | OHOS 系统 | 运行期 `DT_NEEDED` | 设备自带 |

## 验证结果

```bash
# 设备 native 构建（与 conan create 同一 profile 语义）
open_jtalk -h
# → The Japanese TTS System "Open JTalk" / Version 1.10 ...   rc=0
# → The HMM-Based Speech Synthesis Engine "hts_engine API"（HTS_COPYRIGHT 宏，证明私有依赖已链入）

# 三元组检测（锚点补丁后）
sh config/config.guess            # → aarch64-unknown-linux-ohos
sh config/config.sub aarch64-unknown-linux-ohos   # → aarch64-unknown-linux-ohos

# 词典加载路径（无 .htsvoice 声学模型时按上游行为退出 1）
printf 'こんにちは\n' | open_jtalk -x <prefix>/dic -m <prefix>/dic/__no_voice__.htsvoice
# → Warning: HTS_fopen: Cannot open ...__no_voice__.htsvoice.
# → Error: Dictionary or HTS voice cannot be loaded.          rc=1
#   注意：HTS_fopen 警告出现在 Mecab_load 之后，说明 dic/ 已被成功加载

readelf -d bin/open_jtalk | grep NEEDED
# → libc++_shared.so, libc.so（hts_engine 为静态链接，无运行期 hts 依赖）

make check   # 全部 SUBDIR 输出 Nothing to be done for 'check'，rc=0（上游无测试目标）
```

`conan create`（含 `test_package/test.sh`）的完整日志见 PR 正文的 W3 证据段。

## 交付物

下表为 `conan create` 打包产物（`sys.dic` 等词典文件在 native 验证构建与 conan 构建中逐字节相同）；
`bin/open_jtalk` 在设备 native 验证构建中为 4598336 B（带 `-g -O2` 调试信息），
conan 构建按 profile 用 `-O3 -DNDEBUG` 且不带 `-g`，打包后为 870976 B。

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/open_jtalk` | 870976 B | 主 TTS 可执行文件（ELF 64-bit LSB arm64, PIE；`readelf -h/-lW/-dW` 见 PR 正文） |
| `dic/sys.dic` | 103073776 B | MeCab NAIST-JDic 系统词典 |
| `dic/matrix.bin` | 3792262 B | 连接矩阵 |
| `dic/char.bin` | 262496 B | 字符类别表 |
| `dic/unk.dic` | 5690 B | 未知词词典 |
| `dic/left-id.def` / `right-id.def` | 77672 B | 左/右连接 ID 定义 |
| `dic/pos-id.def` | 1923 B | 词性 ID 定义 |
| `dic/rewrite.def` | 7457 B | 重写规则 |

## 注意事项

- **运行 open_jtalk 合成语音还需要外部 `.htsvoice` 声学模型**（如
  `nitech_jp_atr503_m001.htsvoice`），该文件不在上游源码包中，本包也不分发；
  缺少时程序在 `HTS_Engine_load` 处按上游行为报
  `Error: Dictionary or HTS voice cannot be loaded.` 并退出 1。
- 因此 `test_package/test.sh` 的最深断言是「词典加载成功 + 到达声学模型加载阶段」，
  没有做端到端合成（如实记录，未覆盖范围见 MANIFEST.yml）。
- 本包只支持 in-tree 构建；改动 `layout()` 时必须保持
  `build_folder == source_folder`，否则会复现「No rule to make target ...libtext2mecab.a」。
- 包名与仓库内已有的历史纯归档目录 `archives/o/open_jtalk/1.11`（无 conanfile.py，
  ARCHIVE-SPEC v2.0 时代产物）**并存且互不影响**；本包是任务卡分支
  `feat/open-jtalk-1.11` 对应的 Conan 化制品（CI L0n 要求「分支名去前缀 == 包目录名-版本」，
  故目录名为 `open-jtalk`）。

## 知识沉淀

- 新增草稿 `knowledge/drafts/E6342-draft-4A7C.{md,kv}`：OHOS SDK 26 的 `fpos_t`
  为无 `__pos` 成员的 union，与既有 E414 的前提（struct + `__pos`）不同，
  含反证命令与实测输出。
- config.guess/config.sub 的处置复用草稿 `DRAFT-E564-oldstyle-config-guess-ohos-reanchor`
  （旧式脚本改手工最小锚点补丁），并参照 E007（OHOS 识别）与 E011（HMDFS umask）。
---

**编译结束**: 2026-09-13 01:26
**最终状态**: built
