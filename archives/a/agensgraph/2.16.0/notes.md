# agensgraph 2.16.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-09
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

```bash
source .build-context-agensgraph-2.16.0
cd $BUILD_SRC_DIR

# 1. Patch config.guess/config.sub for OHOS
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config/config.guess config/config.sub
# Additional fix: add linux-ohos* to valid kernel-OS list in config.sub
sed -i 's/linux-musl* | linux-relibc*/linux-musl* | linux-ohos* | linux-relibc*/' config/config.sub

# 2. Patch configure to fix HMDFS umask 077 bug
# HMDFS filesystem: umask 077 makes mktemp directories unwritable
# Changed "umask 077 && mktemp" to "umask 022 && mktemp" in configure

# 3. Configure with ICU and C++ runtime support
export PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig:$PKG_CONFIG_PATH
bash ./configure --prefix=$DEFAULT_PREFIX --disable-nls --without-readline \
  LDFLAGS="-L$DEFAULT_PREFIX/lib -lc++ -Wl,--as-needed"

# 4. Build
make -j2

# 5. Install (DESTDIR mode)
make install DESTDIR=$TEST_PREFIX

# 6. make check - SKIPPED (initdb requires NSS user lookup, unavailable on OHOS)

# 7. Package
python3 $SKILL_ROOT/scripts/ohc-run.py package agensgraph 2.16.0

# 8. Install to real prefix
make install

# 9. Verify
$DEFAULT_PREFIX/bin/agens --version  → "agens (AgensGraph) 2.16"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.sub rejects `aarch64-unknown-linux-ohos` | OHOS triplet not in valid OS list | patch-autotools-ohos.pl + manual sed to add `linux-ohos*` to config.sub |
| 2 | HMDFS umask 077 makes mktemp dirs unwritable | HMDFS filesystem bug: directory created with umask 077 has drwx--S--- which blocks writes | Patch configure: change `umask 077` to `umask 022` for mktemp temp dir creation |
| 3 | ICU static libs need C++ runtime | libicuuc.a/libicui18n.a are static C++ libs needing libc++ symbols | Add `-lc++` to LDFLAGS |
| 4 | readline headers missing | libreadline.so exists but headers not installed | `--without-readline` |
| 5 | initdb fails in make check | OHOS lacks NSS user database (passwd) | Skip make check, record as platform limitation |
| 6 | src/Makefile.global.in missing in .work dir | Not copied during dual-track extraction | Copy from .orig directory |

## 源码修改

3 patches generated:
- `0001-config-config.guess.patch` — Add __OHOS__/HarmonyOS detection
- `0002-config-config.sub.patch` — Add ohos-linux triplet + linux-ohos* OS
- `0003-configure.patch` — Change umask 077 to umask 022 for mktemp (HMDFS fix)

## 依赖版本

- ICU 77.1 (static libs, need -lc++)
- zlib 1.3.1

## 验证结果

```bash
$DEFAULT_PREFIX/bin/agens --version
agens (AgensGraph) 2.16

$DEFAULT_PREFIX/bin/pg_config --version
PostgreSQL 16.9
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| agensgraph-2.16.0-ohos-aarch64.tar.gz | ~99MB | 预编译包 |
| agensgraph-2.16.0-ohos-aarch64-debug.tar.gz | ~6.5MB | Debug symbols |

## 注意事项

- AgensGraph is based on PostgreSQL 16, inherits all PG platform issues
- `make check` skipped: initdb requires passwd/NSS which OHOS lacks
- ICU linked statically requires `-lc++` in LDFLAGS
- HMDFS umask 077 bug is a known platform issue (similar to E046)
---

**编译结束**: 2026-06-09 12:04
**最终状态**: built
