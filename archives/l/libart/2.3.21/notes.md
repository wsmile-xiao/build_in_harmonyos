# libart 2.3.21 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 / clang++
- 状态: built（conan-verify 门禁执行中）

## 上游调研结论（任务 #1）

- libart_lgpl 2.3.21（2010-06-10 发布）是 GNOME 2 时代的 2D 图形基元库（affine 变换、bezier 路径、SVP 扫描线栅格化、UTA 微调平铺数组），GTK+ 2 / GdkRgb 的渲染后端
- 上游源码: `https://download.gnome.org/sources/libart_lgpl/2.3/libart_lgpl-2.3.21.tar.bz2`（SHA256 `fdc11e74c10fc9ffe4188537e2b370c0abacca7d89021d4d303afdf7fd7476fa`）
- 构建系统: Autotools（configure.in 114 行，AM_PROG_LIBTOOL 隐式触发 config.guess/sub）
- 依赖: 零外部依赖，仅链接 libm（`libart_lgpl_2_la_LIBADD = $(libm)`）
- 正式测试: **无** `make check` 目标。仅 noinst_PROGRAMS: testart（5 个子命令 testpat/gradient/dist/dash/intersect）与 testuta，`tests:` 目标构建之
- shared/static: libtool 完整支持 `--enable-shared/--enable-static`，产物 `libart_lgpl_2`（.so.2.x.x / .a），头文件安装至 `$(includedir)/libart-2.0/libart_lgpl/`，pkg-config 文件 `libart-2.0.pc`
- tarball 自带 `art_config.h` 的 32-bit 值（`ART_SIZEOF_LONG 4`），但其类型定义（`art_u8/u16/u32` 基于 char/short/int）在 aarch64 上类型正确，无需重生成

## 编译步骤

```bash
# 源码（/tmp 只读，用 TMPDIR 落盘到工作目录）
mkdir -p .tmp-libart-dl && cd .tmp-libart-dl
TMPDIR="$PWD" \
  curl -LO https://download.gnome.org/sources/libart_lgpl/2.3/libart_lgpl-2.3.21.tar.bz2

# 补丁生成（per-file-difflib，先 orig/work 对照后验证）
python3 gen_patches.py   # 生成 3 个补丁 + 行为验证 + patch -p1 干净应用验证

# 完整构建与测试（Conan）
conan create archives/l/libart/2.3.21 --build=missing -pr:a <OHOS profile>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot guess build type | tarball 自带 config.guess（2009-04-27 版）无 HarmonyOS 检测分支（知识图谱 E007） | 手写补丁在主系统 case 首位插入 `*:HarmonyOS:*:*` 分支，按 UNAME_MACHINE 映射 aarch64→aarch64、armv7*→arm 等，输出 `aarch64-unknown-linux-ohos` 后 `echo; exit`（避免落至编译探测路径） |
| 2 | config.sub 不识别 aarch64-linux-ohos 三元组 | 2008 版 config.sub 既无 AArch64 CPU 类型，又无 linux-ohos KERNEL-OS/OS 组合支持（E007） | 手写补丁 5 处：CPU 无厂商白名单加入 `aarch64`；带厂商白名单加入 `aarch64-*`；maybe_os 列表加入 `linux-ohos*`；OS 大列表加入 `| -linux-ohos*`；在 `-linux*`→`linux-gnu` 重写前加入 `-linux-ohos` 直通 case。验证 `aarch64-linux-ohos` 正确规范化为 `aarch64-unknown-linux-ohos`，同时 x86_64/arm OHOS 及 x86_64 GNU 均无回归 |
| 3 | config.status: can't create ./confXXXXXX/out: Permission denied | HMDFS 文件系统 umask 077 临时目录对当前进程不可写（知识图谱 E011） | configure 中两处 `umask 077` → `umask 022`（mktemp 与 mkdir 回退路径） |
| 4 | 补丁验证树与工作树 diff 不一致 | 生成脚本以文本模式读写 configure，通用换行转换把内嵌 CR（`ac_cr='<CR>'` 字面回车）转成换行，拆行损坏文件 | Python 读写改 `newline=""` 保留原始字节；root cause 是 work 树被写坏而 patch 应用的 verify 树是对的 |
| 4b | config.guess 编译探测失败 | 2009 版脚本无 HarmonyOS 分支时会 fallback 到编译 dummy.c 探测，HMDFS 上创建临时文件失败 | 由问题 1 的 HarmonyOS 分支 `echo; exit` 一并解决（不进入探测路径） |

## 源码修改

- `config.guess`：新增 HarmonyOS 系统识别分支 + `echo "$GUESS"; exit`
- `config.sub`：新增 AArch64 CPU 类型及 `linux-ohos` 三元组支持（5 处）
- `configure`：`umask 077` → `umask 022`（两处，HMDFS 平台限制，E011）

## 依赖版本

无任何依赖（requirements 为空，仅 system_libs=m）。

## 验证结果

```bash
# 上游测试（无 make check；构建并运行 noinst 测试程序作为最近似验证）
make tests   # 构建 testart + testuta
./testart testpat && ./testart gradient && ./testart dist \
  && ./testart dash && ./testart intersect   # 5 个子命令，写 stdout，退出码 0
./testuta 42   # 随机种子 42，输出 PostScript 至 stdout，退出码 0

# test_package（消费者视角）

- `test_libart`：消费者 API 测试，9 项断言通过
- `libart_ohos_platform`：HarmonyOS 特有测试，验证 `__OHOS__`、AArch64 和 64 位指针环境
- static：CTest 2/2 通过
- shared：CTest 2/2 通过

conan create ... # CMakeDeps 消费最终 package_folder，验证 libart::libart 链接与 API 调用
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools，静态默认，构建 noinst 测试并运行，system_libs=m） |
| conandata.yml | 源码 URL + SHA256（fdc11e74...）+ 3 个补丁声明 |
| manifest.yaml | 版本级 manifest（per-file-difflib 元数据，orig/work 树哈希） |
| notes.md | 本适配笔记 |
| patches/ | 0001 config.guess / 0002 config.sub / 0003 configure umask |
| test_package/ | 消费者测试（affine 变换 + SVP 栅格化 + 版本宏断言）+ HarmonyOS AArch64/64 位平台专有测试 + MANIFEST.yml |

## 注意事项

- 库名为 `art_lgpl_2`（libart_lgpl_2.so/libart_lgpl_2.a），非包名 libart；头文件在 `include/libart-2.0/libart_lgpl/`（cpp_info.includedirs 需保留子目录层级）
- config.guess/sub 为 2009/2008 老版本，知识图谱 E007 命中并按 lcms1 先例处理；未发现新的未覆盖根因 → 路径 A（复用现有知识），不新增知识草稿
- `make tests` 构建的 testart/testuta 是 noinst 目标，不进入 package
- tarball 自带 art_config.h 的 32-bit 尺寸值在 aarch64 上类型正确，无需 gen_art_config.sh 重生成
- 无 commands.json：上游无安装的可执行工具（仅 noinst 测试程序）

---

**编译结束**: 2026-09-16
**最终状态**: built
