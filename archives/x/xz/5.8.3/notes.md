# xz 5.8.3 — 独立复验交付笔记（任务 #3584）

> 档案创建时间: 2026-09-11
> 认领人: calbee21（天津大学鸡屁股队）
> 构建系统: autotools (configure + make)

## 一、任务背景

平台任务 #3584（xz 5.8.3）。xz/5.8.3 早已通过 PR #3383（ZACH_123，2026-08-14 合入）发布到制品仓
（rrev b578e07391f8256ded9aedf5b102d8c0，含 OHOS armv8 二进制 01d92cf3...）。
后续上游系列演进 5.8.3.1（PR #5991）/5.8.3.2（PR #6542）已合入 main 归档，但 5.8.3 基础版本目录
在 main 上不存在（归档清理），平台任务保持 open。

本交付参照 libXfixes 6.0.2（PR #9506）先例：**认领人以当前 main 基线重建 5.8.3 归档目录，
配方与制品仓已发布版本逐字节一致（L0j 零差异），形成完整的可复验交付闭环**。

## 二、制品仓核验（三维核验记录）

| 项目 | 结果 |
|------|------|
| `conan download xz/5.8.3 -r=ohpcd --only-recipe` | ✅ rrev b578e07391f8256ded9aedf5b102d8c0 (2026-08-13) |
| `conan install --requires=xz/5.8.3` (ohos-aarch64 profile) | ✅ binary 01d92cf349a0dd98ff915f4bd99a04430171517f 可下载安装 |
| main 归档 archives/x/xz/ | 5.2.3 / 5.4.5 / 5.6.2 / 5.8.3.2（无 5.8.3 基础目录） |
| 分支 feat/xz-5.8.3 | 曾被 #3383/#5666/#6294/#7735 使用（均已终结），本次按任务 taskBranch 重置占用 |
| 制品仓同版本策略 | 配方逐字节复用制品仓版 → L0j "recipe unchanged" |

## 三、配方身份（与制品仓一致性证据）

| 文件 | md5 | 与制品仓 |
|------|-----|---------|
| conanfile.py | 3474b1a2946de38a52788a88a086ac60 | ✅ 逐字节一致 |
| conandata.yml | 6378eb6a5a128d97d7bfbdcd8041a039 | ✅ 逐字节一致 |
| patches/0001-build-aux-config.guess.patch | be7d31f33057d93316dd6b536306f42f | ✅ 逐字节一致（与 conanmanifest.txt 声明一致） |

## 四、上游测试 N 核验（rule4 口径）

`tests/Makefile.am` 注册口径（上游默认形态）：
- TESTS 基础 17 项：12 个 C 测试二进制（test_check/test_hardware/test_stream_flags/test_filter_flags/test_filter_str/test_block_header/test_index/test_index_hash/test_bcj_exact_size/test_memlimit/test_lzip_decoder/test_vli）+ 3 个 shell 测试（test_files.sh/test_suffix.sh/test_scripts.sh）+ 3 个生成压缩测试（test_compress_generated_abc/random/text）
- COND_MICROLZMA：+test_microlzma（默认配置启用）
- **上游默认形态 N=19**
- 适配构建用 `--disable-scripts`（OHOS 无 /bin/sh，xzdiff/xzgrep 脚本不装），COND_SCRIPTS 分支不激活 → **实际注册 18 项，make check 18/18 PASS (100%)**
- test_scripts.sh 1 项因脚本禁用未运行——平台限制豁免（OHOS 无 /bin/sh）

## 五、本地 W3 复验记录

- 本机 OHOS armv8 / clang 15 / conan 2.29.1（OHOS 适配版）
- `conan create . xz/5.8.3 -pr:a=ohos-aarch64-profile -r=ohpcd` 全流程通过
- 上游测试套件 make check：18/18 PASS
- 消费者测试（test_package）：test_xz.c（liblzma API round-trip）+ test_xz.py（xz CLI round-trip）2/2 PASS

## 六、与 5.8.3.1/5.8.3.2 的关系

- 5.8.3.1（PR #5991）：配方现代化（umask 077→022 修复、CONFIG_SHELL 处理、SKIP_WERROR_CHECK）
- 5.8.3.2（PR #6542）：配方现代化重写
- 本目录 5.8.3 保持制品仓已发布配方原样（版本考古价值 + 任务交付要求），演进版用户请引用 5.8.3.2

## 七、踩坑记录（复用知识）

- E007：config.guess 无法识别 OHOS——patches/0001 添加 HarmonyOS case
- E011：config.status 临时目录权限问题——mktemp wrapper 方案（见 conanfile.py generate()）
- OHOS 无 /bin/sh——--disable-scripts 规避 test_scripts.sh 与脚本安装
- test_package 需 conanrun 环境注入（PATH 中 xz bin/）——沿 5.8.3.2 经验
