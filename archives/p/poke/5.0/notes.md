# poke 5.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos, 原生构建)
- 状态: built (conan create 通过 + test_package R34 冒烟通过)

## 编译步骤

```bash
# conan 依赖（profile: ci/conan/profiles/ohos-aarch64，已定义 SHELL/CONFIG_SHELL）
conan install --requires gc/8.2.12 --requires readline/8.3 \
  -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build=missing

# conan create（配方已固化以上全部步骤）:
conan create . -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 \
  -r ohpcd --build=missing

# 配方等价手动流程:
#  1) apply 两个补丁（umask + OHOS 三元组）
#  2) ./configure CC=clang --prefix=/ --disable-libnbd \
#       --with-libreadline-prefix=<conan readline 包目录> \
#       BDW_GC_CFLAGS=-I<gc include> BDW_GC_LIBS="-L<gc lib> -lgc -lcord" \
#       --enable-static --disable-shared
#     （ncurses 由 LDFLAGS/LIBS 注入，readline 传递依赖）
#  3) configure 后按依赖顺序钉扎 doc 时间戳（见下）
#  4) make -j8 MAKEINFO=true
#  5) make install MAKEINFO=true（DESTDIR 打包）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报错无法创建临时目录 (E011) | HMDFS UID 映射下 `umask 077 && mktemp -d "./confXXXXXX"` 生成 0700+setgid 目录，后续同 UID 写入被拒 | 补丁 0001：顶层 configure（4 处）+ jitter/configure（3 处）umask 077→022 |
| 2 | config.guess 无法识别平台 (E007) | 上游 autotools 快照早于 OHOS，无 ohos 三元组 | 补丁 0002：顶层与 jitter/build-aux 的 config.{guess,sub} 增加 `aarch64-unknown-linux-ohos`（LIBC=ohos + `*:HarmonyOS:*:*` 机器映射） |
| 3 | make 阶段 doc 报 `Error 127 (missing makeinfo)` 且 version.texi 被污染成环境变量转储 | `doc/stamp-vti` 依赖 `$(top_srcdir)/configure`；补丁重写 configure 后 mtime=now → mdate-sh 规则触发，而 mdate-sh 在 OHOS 输出为空 → bash `set` 无参将整个环境写入 version.texi → .info 判过期 → `MAKEINFO=missing` 包装器报 127 | 配方 `_pin_prebuilt_docs()`：configure 后按依赖顺序（stamp-* → version*.texi → poke.info 等）刷新 mtime；并向 make/install 传 `MAKEINFO=true` 命令行覆盖兜底 |
| 4 | configure 找不到 bdw-gc | poke 用 PKG_CHECK 查 pkg-config 模块名 `bdw-gc`，而 conan 包名为 `gc`（包内 bdw-gc.pc 的 prefix 指向旧缓存路径不可靠） | guile/2.2.7 先例：`BDW_GC_CFLAGS`/`BDW_GC_LIBS` 是 precious 变量，经 configure 命令行注入绕过 pkg-config |
| 5 | readline 链接 | gnulib havelib 探测 include/ + lib/ | `--with-libreadline-prefix=<conan readline 包>`；ncurses(-w) 由 AutotoolsDeps 注入（readline 传递依赖 ncurses/6.6.Z） |
| 6 | libnbd 不存在于 OHOS | 上游可选 IO 空间 | `--disable-libnbd` |
| 7 | Guile 选项不存在 | poke 5.0 上游已移除 Guile 支持 | 无需任何 --without-guile，记入笔记防止后人误加 |

## 源码修改

| 补丁 | 内容 |
|------|------|
| `0001-configure-hmdfs-umask-022.patch` | configure 与 jitter/configure 共 7 处 `umask 077`→`umask 022`（E011） |
| `0002-config-guess-sub-ohos-triplet.patch` | 顶层与 jitter/build-aux 的 config.guess/config.sub 增加 OHOS 三元组（E007） |

两补丁均在干净 tarball 树用 `git apply --check` 与 `patch --dry-run` 双工具验证可应用。

## 依赖版本

- gc/8.2.12（Boehm GC，conan ohpcd）
- readline/8.3（conan ohpcd；传递依赖 ncurses/6.6.Z）
- libnbd：禁用；Guile：上游 5.0 已移除

## 验证结果

### conan create 内 test_package（R34 冒烟，test.sh）
```
PASS: T1 poke --version (GNU poke 5.0)
PASS: T2 arithmetic/shift/bitwise evaluation
PASS: T2b -c one-shot evaluation
PASS: T3 load crc16.pk pickle (standard vector)
PASS: T4a pokefmt expression interpolation
PASS: T4b pokefmt arithmetic
PASS: T4c pokefmt pickle load (0x29B1 == 10673)
TOTAL PASS=7 FAIL=0
```

### make check（构建树，手动）
- EXIT=0。DejaGnu（runtest/expect/tclsh）在 OHOS 不可用 → HAVE_DEJAGNU 未定义，
  testsuite/*.exp 的 DejaGnu 部分被跳过（如实记录，无代偿声明）。
- testsuite/poke.libpoke 4 个独立 C 测试（不经 DejaGnu）手动运行：
  `LD_LIBRARY_PATH=<build>/libpoke/.libs POKEDATADIR=<build>/libpoke POKECONFIGDIR=<build>/libpoke ./testsuite/poke.libpoke/{values,api,foreign-iod,decls}`
  → **181 通过 / 0 失败**（values=116、api=57、foreign-iod=7、decls=1）。

### L4 安全
poke/poked/pokefmt 二进制 RELRO/NX/PIE 全过；三个可执行文件 NEEDED 仅 libc.so（gc/readline/ncursesw 静态并入，R26）。libpoke 以 libpoke.a 静态形态交付（--disable-shared）；"libpoke.so.2.0.0 仅 NEEDED libc.so" 的观察来自适配早期探索树（--enable-shared 试验），与最终交付物无关。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | autotools 配方（R26 静态、R32 settings 四项） |
| conandata.yml | 官方 https URL + sha256 + 两补丁 |
| patches/0001, 0002 | E011 + E007 |
| test_package/{conanfile.py,test.sh,MANIFEST.yml} | aa3d 模式：VirtualRunEnv + test_type=explicit + bash 包装 |
| commands.json | poke/pokefmt，type=tool |

## 注意事项

1. **运行时重定位**：安装 prefix=/（aurpublish 先例），运行时数据须用环境变量定位——
   `POKEDATADIR=<pkg>/share/poke`（主开关）、`POKECONFIGDIR`、`POKEPICKLESDIR=<pkg>/share/poke/pickles`
   （注意：POKEPICKLESDIR **不随** POKEDATADIR 派生，须显式设置）、`POKEFMTAPPDIR`（pokefmt 专用）。
   test_package 已验证这套组合。
2. **CLI 怪癖（OHOS）**：stdin 管道 REPL 与裸文件参数模式 stdout 完全为空（RC=0）——
   脚本化必须用 `poke -c 'code'` 或 `poke -s file`；`-s` 模式断言失败不传播退出码（打印
   "unhandled assertion failure exception" 且继续执行），自动化断言用**精确输出匹配**。
   `poke -c` 退出码可传播（assert 失败 RC=1）。
3. **pokefmt 用法**：模板走 stdin、Poke 代码走 argv（`pokefmt 'var s = ...;' < tmpl.pkfm`）；
   文件参数模式会报 undefined variable 'fmt'。
4. **Poke 语言**：位移是 `<<.` / `.>>`（带点）；printf 用 Poke 标签（`%v`、`%u16x`），
   无 C 的 `%d`；`%v` 打印字符串带引号、uint<16> 带 `UH` 后缀。
5. **stderr "GC Warning: Failed to find PT_GNU_RELRO segment"** 为良性告警（静态 libgc 查找自身段），不影响功能。
6. bin/ 下 pk-strings 等脚本 shebang 硬编码 prefix，重定位场景需注意。
7. pickles 无 elf.pk（5.0 事实），勿在测试中引用。
---

**编译结束**: 2026-09-03 14:10
**最终状态**: built
