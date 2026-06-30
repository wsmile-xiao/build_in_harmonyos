# libbs2b 3.1.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-01
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published

## 编译步骤

1. 下载源码 tarball (SourceForge)
2. init-build 创建构建上下文
3. 修补 config.guess (2009版太旧，不支持HarmonyOS) → 使用 `echo ... ; exit ;;` 格式
4. 修补 config.sub (添加 linux-ohos* / -ohos* / linux-ohos* 三处修改)
5. 修改 configure.ac: sndfile 改为可选依赖 + 现代化宏（移除 dist-lzma, AC_PROG_LIBTOOL→LT_INIT）
6. 修改 src/Makefile.am 使 bs2bconvert 依赖 sndfile 条件编译
7. autoreconf -fi 重新生成 configure 和 Makefile.in（从修补后的 configure.ac/Makefile.am）
8. 创建 mktemp wrapper 脚本绕过 HarmonyOS sandbox 对 umask-077 目录的写入限制
9. ./configure --prefix=$DEFAULT_PREFIX (PATH含mktemp wrapper)
10. make -j1
11. make install DESTDIR=$TEST_PREFIX (staging)
12. make check (无测试套件)
13. make install (本地安装)
14. 验证: bs2bstream --help, pkg-config --modversion libbs2b → 3.1.0
15. ohc-run.py package → libbs2b-3.1.0-ohos-aarch64.tar.gz
16. ohc-run.py finish → published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 2009版脚本不含HarmonyOS检测分支 | 修补添加HarmonyOS case分支，使用 `echo ... ; exit ;;` 格式 |
| 2 | config.sub 不验证 aarch64-unknown-linux-ohos 三元组 | 缺少ohos相关验证规则 | 添加3处修改: linux-ohos*内核OS识别, -ohos* OS白名单, linux-ohos*内核-OS白名单 |
| 3 | configure 错误: "Please install libsndfile" | sndfile是硬依赖 | 修改configure.ac使sndfile可选(HAS_SNDFILE=yes/no + AM_CONDITIONAL) |
| 4 | mktemp -d 创建的目录权限过严(umask 077) | HarmonyOS sandbox阻止写入 | 创建mktemp wrapper使目录权限为0755 |
| 5 | autoreconf 失败: dist-lzma 已废弃, AC_PROG_LIBTOOL 已废弃 | 新版automake/autoconf不支持旧宏 | 移除dist-lzma, AC_PROG_LIBTOOL→LT_INIT |
| 6 | G0 clean-verify 失败（补丁不自包含） | 只修补了configure.ac但没重新生成configure | 只保留源文件补丁(R6)，autoreconf在G0中自动重新生成 |

## 源码修改（R6: 只改源文件，生成文件由autoreconf重新生成）

- 0001-build-aux-config.guess.patch: 添加HarmonyOS系统识别分支
- 0002-build-aux-config.sub.patch: 添加ohos三元组验证支持
- 0003-configure.ac.patch: sndfile可选 + 现代化宏(移除dist-lzma, LT_INIT)
- 0004-src-Makefile.am.patch: bs2bconvert条件编译

## 依赖版本

- 无强制外部库依赖（sndfile为可选依赖，当前未安装）

## 功能测试结果（2026-06-01）

### bs2bstream 命令行工具
- `--help`: ✅ 输出 3.1.0 版本和完整用法
- `--version`: ⚠️ 不支持独立版本参数（输出等同于 --help）
- 6 种参数组合（default/chu moy/jan meier/8bit/32bit/unsigned LE）全部通过
- 音频处理验证：输入 352800B PCM → 输出 352800B，88199/88200 样本变化（binaural crossfeed 正确生效）

### libbs2b C API
- `bs2b_open/close/set_level/get_level/get_fcut/get_feed/cross_feed_f` 7 个 API 全部验证通过

### pkg-config
- `--modversion`: 3.1.0 ✅
- `--cflags/--libs`: 正确输出 ✅

### ELF 与依赖
- bs2bstream NEEDED: libbs2b.so.0, libc.so
- libbs2b.so NEEDED: libc++_shared.so, libc.so
- ⚠️ 无 RPATH（运行时需 LD_LIBRARY_PATH 或安装到系统路径）

### 协作质量评估（review）

- ✅ 补丁完整性（4 个源文件补丁）
- ✅ notes.md 关闭、临时文件、knowledge_ref 引用、打包产物、测试报告
- ❌ Manifest 缺 `compile_date` → 已修复
- ❌ E编号冲突 → 全局知识图谱问题，按 R16 协作不越权，需主编处理

### 上库结论
**✅ 满足上库要求**。G0-G4 全部 PASS，功能测试通过，文档完整。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libbs2b-3.1.0-ohos-aarch64.tar.gz | 379KB | 预编译包(含库+头文件+bs2bstream) |
| libbs2b-3.1.0-ohos-aarch64-debug.tar.gz | 166KB | 调试符号包 |

## 注意事项

1. bs2bconvert 未编译（需要libsndfile预编译包支持）
2. G0 clean-verify 需要 mktemp wrapper 在 PATH 中 + autoreconf 重新生成 configure
3. 只保留4个源文件补丁（R6原则），生成文件由autoreconf在clean-verify中自动生成
4. bs2bstream 和 libbs2b.so 无 RPATH，安装到系统路径或通过 cmd-pkgs 安装脚本部署后可正常运行

---
**编译结束**: 2026-06-01 20:19
**最终状态**: published