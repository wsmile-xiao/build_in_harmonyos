# libbacktrace 20240505 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-02
- 编译器: clang（OHOS 原生 /data/service/hnp/bin/clang）
- 状态: published

## 编译步骤

```bash
# 探索阶段（W3 同源参数）
./configure --prefix=$DEFAULT_PREFIX CC=$CC CFLAGS="$CFLAGS -fno-optimize-sibling-calls -fno-omit-frame-pointer"
make -j1
make install DESTDIR=$TEST_PREFIX
make -j1 check   # 33 项上游测试
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 报 `unable to guess system type`，临时目录 Permission denied | HarmonyOS `uname -s` 返回 `HarmonyOS` 不被识别；HMDFS 对 umask 077 私有目录拒绝创建文件 | 补丁 0001：识别 `aarch64:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos` |
| 2 | config.sub 报 `Invalid configuration 'aarch64-unknown-linux-ohos': OS 'ohos' not recognized` | 上游 config.sub (2021) 无 ohos 枚举 | 补丁 0002：OS 表加 `ohos*`，kernel-os 校验加 `linux-ohos*` |
| 3 | configure 末段 `config.status: error: could not setup config files machinery`（E129） | autotools 用 `umask 077 && mktemp -d ./confXXXXXX` 建私有临时目录，HMDFS 对 0700 目录写文件被拒 | 补丁 0003：`umask 077` → `umask 022`（configure 内 2 处） |
| 4 | btest/edtest/mtest/dwarf5 等 8 项 FAIL：`got 489 expected 60 / got main expected test1` | clang 忽略 `__attribute__((noclone))`，-O2 下 sibling-call 优化与帧指针省略使 test1/test3 等栈帧被合并，行号与函数名断言落空 | 全部测试编译追加 `-fno-optimize-sibling-calls -fno-omit-frame-pointer`（conanfile generate() extra_cflags） |
| 5 | b2test_buildid/b2test_buildidfull/btest_gnudebuglink/btest_gnudebuglinkfull/mtest_minidebug 5 项 exit 126 `Operation not permitted`（E077） | objcopy --strip/--add-gnu-debuglink 重写 ELF 后 `.codesign` 签名段失效，OHOS 内核拒绝执行 | 补丁 0004：Makefile.in 派生规则尾部内联 `llvm-objcopy --remove-section .codesign` → `binary-sign-tool sign -selfSign 1` → `chmod a+x` |

## 源码修改

| 文件 | 内容 |
|------|------|
| patches/0002-config.guess.patch | config.guess case 分支识别 aarch64-unknown-linux-ohos |
| patches/0003-config.sub.patch | config.sub 接受 `ohos*` OS 与 `linux-ohos*` 组合 |
| patches/0004-configure.patch | configure 私有临时目录 umask 077→022（E129，知识图谱命中） |
| patches/0001-Makefile.in.patch | 5 类 objcopy 派生测试产物规则内联重签名（E077 口径：remove-section → sign → chmod，顺序不可变） |

无平台宏 `__OHOS__` 引入；全部为构建系统可移植性修改。

## 依赖版本

- zlib/1.3.1（制品仓已发布，`conan download zlib/1.3.1 -r=ohpcd --only-recipe` 验证通过）
  - 仅供上游 ztest/ztest_alloc 链接 `-lz`；configure 探测到系统 zlib，产物本身无 zlib 依赖
- 无其他第三方依赖

## 验证结果

```text
make check（HarmonyOS PC aarch64, 2026-09-02）
Testsuite summary: TOTAL 33 / PASS 33 / FAIL 0 / SKIP 0 / XFAIL 0 / ERROR 0
```

- 首轮基线（无适配参数）：33 项中 20 PASS / 13 FAIL（分类见问题表 #4 #5）
- 栈帧编译参数修复后：26 PASS / 7 FAIL（仅剩 objcopy 派生类）
- 测试规则重签名修复后：33 PASS / 0 FAIL（全量通过）
- 详细日志：reports/upstream-tests.log（最终）、reports/upstream-tests-flags.log（中间轮）

## 注意事项

- 版本 20240505 为上游快照命名（waterlan.home.xs4all.nl libbacktrace-20240505），对应官方 GitHub 提交 11427f3，conandata.yml 直接指向官方源
- libbacktrace 为系统同名库场景无关的独立库，产物仅 `libbacktrace.a` + 头文件（静态，R26 无冲突）
- 上游 `--compress-debug-sections`（zlib-gnu/gabi/zstd）与 `-llzma` 在 OHOS 环境探测为不支持，zstdtest/xztest 走未压缩回退路径，属上游设计而非缺陷
---

**编译结束**: 2026-09-02 20:22
**最终状态**: published
