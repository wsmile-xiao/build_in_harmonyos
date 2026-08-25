# asterisk-speex 22.10.1 — HarmonyOS PC (aarch64) 适配笔记

## 结论
- **状态**: published（本地 conan-verify 全门禁 PASS）
- **交付物**: `codec_speex.so`（Asterisk Speex 编解码器模块，`codecs/codec_speex.c`）
- 仅打包 Speex 模块；其余 Asterisk 模块（res/funcs/format 等）一律排除。
- 源码包: `asterisk-22.10.1.tar.gz`（与 asterisk-srtp 同源包）

## 编译环境
- 构建系统: autotools（Asterisk 官方 configure + make）
- 编译日期: 2026-08-23
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang），llvm-ranlib/llvm-ar
- Conan: 2.29.1（OHOS 适配版），profile `ohos-aarch64`（os=OHOS, arch=armv8, clang 15, libc++）
- 目标: HarmonyOS PC aarch64（aarch64-unknown-linux-ohos triplet）
- 构建目录: conan build_folder 内 `worktree/` 子目录（规避 HMDFS 对 .conan2 缓存目录的 MAC 限制 E052/E060）

## 依赖（全部从 ohpcd / 本地 conan 缓存解析）

| 依赖 | 版本 | 作用 | 备注 |
|------|------|------|------|
| speex | 1.2.1 | `speex/speex.h` + `speex_encode`（libspeex.a 静态） | 本地缓存 armv8 包 9ccf3357 |
| speexdsp | 1.2.1 | `speex/speex_preprocess.h` + `speex_preprocess_ctl`（libspeexdsp.a 静态） | 本地 `conan create archives/s/speexdsp/1.2.1` 构建（ohpcd 已发布 recipe） |
| libedit | 20240808 | Asterisk configure 硬依赖（pkg-config 探测） | |
| libxml2 | 2.15.3 | menuselect 子 configure 硬依赖（需 xml2-config） | |
| ncurses | 6.6 | libedit.pc `Libs.private=-ltinfo` 的 tinfo 符号 | |
| e2fsprogs | 1.47.4 | libuuid（`uuid_generate_random` 硬依赖） | |
| jansson | 2.15.1.1 | Asterisk configure 硬依赖（>= 2.11） | |
| sqlite3 | 3.49.1 | Asterisk configure 硬依赖（内部数据库） | |

> **发布状态核验（W0/R36）**: speexdsp/1.2.1 recipe 已在 ohpcd 制品仓（`conan download -r=ohpcd` 命中
> a5663774）；speex/1.2.1 本地缓存齐全但 **ohpcd 制品仓查不到**（`conan list -r=ohpcd` 与
> `conan search -r=ohpcd` 均为 not found，`conan download -r=ohpcd` 报 CNB 基础设施错误
> `error:system acceleration policy not enabled`）。**CI 构建前必须先发布 speex/1.2.1 到 ohpcd**，
> 否则远程 clean 环境无法解析。本地验证不依赖远程，全部走缓存。

## 编译步骤

1. **依赖注入（generate()）**：把各依赖包的 include/lib/pkgconfig 复制到
   `build_folder/prefix`（私有 prefix，不污染共享 ~/usr/local），改写 .pc 的 `prefix=`
   为私有 prefix。speex/speexdsp 用 `--with-speex=<prefix> --with-speexdsp=<prefix>`
   （AST_EXT_LIB_CHECK 直接产出 `SPEEX_LIB=-L<prefix>/lib -lspeex -lm` 等）。
   缺失依赖即 `ConanInvalidConfiguration`。
2. **configure**：
   ```
   ./configure --prefix=/ --build=x86_64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos \
     --without-pjproject --with-pjproject-bundled=no \
     --with-speex=<prefix> --with-speexdsp=<prefix> \
     CPPFLAGS=-I<prefix>/include LDFLAGS='-L<prefix>/lib -Wl,-rpath,<prefix>/lib' \
     PKG_CONFIG_PATH=<prefix>/lib/pkgconfig ac_cv_prog_cc_works=yes
   ```
   - `ac_cv_prog_cc_works=yes`：CI 沙箱（hishell_hap 域）禁止运行 conftest 可执行文件。
   - HMDFS 间歇性写临时文件失败 → configure 失败时重跑 config.status（3 次尝试）。
3. **menuselect 子项目预配置**：`cd menuselect && CC=clang PKG_CONFIG_PATH=... ./configure
   --build=x86_64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos ac_cv_prog_cc_works=yes`
   （libxml2 经 pkg-config 解析）。
4. **注入 menuselect.makeopts / menuselect.makedeps**（packaging/ 随源导出，探索验证过的
   完整版；未来时间戳防覆盖；缺失即报错）。语义为**排除列表**：除 codec_speex 外所有
   codec 模块排除 → `make -C codecs` 只构建 codec_speex.so。
   - `format_ogg_speex` 被排除（需 `<ogg/ogg.h>` / libogg，本任务不引入）；
     `func_speex` 不在构建范围（仅编译 codecs/ 子目录）。
5. **生成构建头**：`make_buildopts_h > include/asterisk/buildopts.h`、`make_build_h >
   include/asterisk/build.h`、`make_defaults_h > defaults.h`（裸 `make -C codecs` 不会
   触发顶层 Makefile 的这些目标；buildopts.h 被 autoconfig.h → asterisk.h 引用）。
6. **只构建 codecs 子目录**：
   ```
   make -j1 -C codecs SUBDIR=codecs ASTTOPDIR=<work> \
     ASTCFLAGS=-I<work>/include SOLINK=-shared \
     BUILD_CC=/data/service/hnp/bin/clang PKG_CONFIG_PATH=<prefix>/lib/pkgconfig all
   ```
   - `ASTCFLAGS`（用户级 flags）带 `-I<work>/include` 供 asterisk.h 使用；不要用 `_ASTCFLAGS`
     （命令行覆盖会屏蔽 makefile 的 `_ASTCFLAGS+=`，导致 MOD_ASTCFLAGS 的
     `-DAST_MODULE_SELF_SYM` 与依赖 `-I` 全部失效）。
   - `SOLINK=-shared`：子 make 不导入顶层 Makefile，SOLINK 需显式传入。
   - 模块 .so 不链接 asterisk 核心，跳过 main/utils。
7. **package()**：仅打包 `codec_speex.so` 到 `lib/asterisk/modules/`，附 LICENSE/COPYING。

## 补丁（5 个，与 asterisk-srtp 同源码包完全一致，refresh-patch --auto 生成）
| 补丁 | 内容 |
|------|------|
| 0001-configure.patch | OHOS clang 无 BlocksRuntime → configure 不再 `as_fn_error`，禁用 blocks |
| 0002-include-asterisk-astmm.h.patch | `ASTMM_LIBC` 默认改 `ASTMM_IGNORE`，astmm.h 不再毒化 libc 分配器名 |
| 0003-include-asterisk-utils.h.patch | `RAII_VAR` blocks 分支仅在 `__BLOCKS__` 下启用 |
| 0004-menuselect-config.guess.patch | config.guess 识别 HarmonyOS（aarch64-unknown-linux-ohos） |
| 0005-menuselect-config.sub.patch | config.sub 识别 ohos-linux triplet |

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 写临时文件 Permission denied（间歇） | HMDFS 对 0600 临时文件的 MAC 限制（E052/E060） | configure 失败重跑 config.status；`umask 077`→`umask 022`（运行时 `_drop_umask_077`） |
| 2 | `checking whether the C compiler works... no` | CI 沙箱禁止运行 conftest 可执行文件 | `ac_cv_prog_cc_works=yes` |
| 3 | `asterisk.h: fatal error: 'asterisk/buildopts.h' not found` | 裸 `make -C codecs` 不触发顶层 Makefile 的 buildopts.h 生成目标 | 显式运行 build_tools/make_buildopts_h（及 build.h/defaults.h） |
| 4 | `astmm.h: Do_not_use_free...` / `utils.h: blocks support disabled` | astmm.h 默认 ASTMM_BLOCK 毒化 libc 分配器；clang 无 blocks 时 RAII_VAR 编译失败 | 补丁 0002/0003 |
| 5 | `BlocksRuntime is required for clang` | 上游 configure 在无 libblocksruntime 时报错 | 补丁 0001 |
| 6 | 命令行传 `_ASTCFLAGS` 后 `-DAST_MODULE_SELF_SYM` 与 `-I<speex>/include` 丢失 | 命令行变量覆盖 makefile `+=` 追加 | 改传 `ASTCFLAGS`（CC_CFLAGS 中位于 _ASTCFLAGS 之后） |
| 7 | menuselect 二进制重生成 makeopts 覆盖注入文件 | 注入时机在预配置之前 / 时间戳旧 | 注入时机在 menuselect 预配置【之后】，文件时间戳设为未来（+365 天） |
| 8 | codec_speex 未启用 / 全部 codec 被启用 | menuselect.makeopts 语义为排除列表 | 注入探索验证版 makeopts：除 codec_speex 外全部排除 |

## 源码修改
- 探索阶段手动修改已固化为 5 个补丁（见上表）+ conanfile.py 运行时 `umask 022` 替换。

## 验证结果
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify asterisk-speex 22.10.1
# G0-G4 + L2/L4/L5 全部 PASS → status: published
```
- conan create 干净构建成功（删除缓存包后重建验证通过）。
- test_package（check_codec_speex.py）实质检查：
  - ELF 魔数/ELF64/小端/aarch64(e_machine=183) ✅
  - DT_NEEDED 含 libc.so（speex/speexdsp 静态链入，不在 DT_NEEDED）✅
  - 符号 `load_module` / `unload_module` 已定义 ✅
  - speex 功能符号存在（symtab 16 处 speex_encode/speex_preprocess/decoder 等）✅
  - dlopen 在 asterisk 进程外失败为预期行为（未解析 ast_module_register）✅
- 产物: codec_speex.so（约 215KB，DYN shared object）

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | 完整配方（依赖注入/configure/menuselect 预配置/makeopts 注入/只构建 codecs） |
| conandata.yml | 源码 sha256 与 5 个补丁声明 |
| patches/0001-0005 | OHOS 平台适配补丁 |
| packaging/menuselect.makeopts, menuselect.makedeps | 排除列表语义（只启用 codec_speex） |
| test_package/ | R34 实质 API 验证（ELF/符号/speex 链接检查） |
| reports/ | conan-verify-report.md + conan-create.log |

## 注意事项
1. **发布依赖**：CI 构建前必须先 `conan upload speex/1.2.1` 到 ohpcd（speexdsp 已在仓内）。
2. format_ogg_speex 未构建：需要 `<ogg/ogg.h>`（libogg）；如需支持 Ogg-Speex 容器格式需先发布 libogg 依赖并放开该模块。
3. func_speex 未构建：仅需 speexdsp preprocess 头，后续如需可单独开启（make -C funcs）。
4. 模块 .so 由 asterisk 二进制加载（`ast_module_register` 等核心符号运行时解析），
   进程外 dlopen 失败属预期，不影响交付。
---

**编译结束**: 2026-08-23 04:54
**最终状态**: built
