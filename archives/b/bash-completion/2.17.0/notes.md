# bash-completion 2.17.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-05
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
# 1. Source build context
source .build-context-bash-completion-2.17.0

# 2. Apply patches (config.guess + config.sub for HarmonyOS)
cd $BUILD_SRC_DIR
patch -p1 < patches/0001-config.guess.patch
patch -p1 < patches/0002-config.sub.patch

# 3. Fix umask 077 issue in config.status template
# HarmonyOS HMDFS rejects file creation in dirs created with
# `umask 077 && mktemp -d` (setgid + no group execute = Permission denied)
sed -i 's|umask 077 && mktemp -d|mktemp -d|g' configure
sed -i 's|umask 077 && mkdir|mkdir|g' configure

# 4. Configure
./configure --prefix=$DEFAULT_PREFIX

# 5. Build (use -j1 due to HMDFS mkfifo limitation)
make -j1

# 6. Install to staging
make install DESTDIR=$TEST_PREFIX

# 7. Run tests
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: could not setup config files machinery | HarmonyOS HMDFS: `umask 077 && mktemp -d` creates dirs with 2700 perms (setgid + no group execute), file creation denied | Patch configure to remove `umask 077` from mktemp/mkdir commands |
| 2 | make: jobserver mkfifo: Operation not permitted | HMDFS doesn't support mkfifo | Use `make -j1` instead of `make -j2` |
| 3 | automake-1.17: inaccessible or not found | Makefile.am timestamp triggered regeneration rule | Touch generated files to prevent regeneration |

## 源码修改

- `patches/0001-config.guess.patch`: Add HarmonyOS detection to config.guess
- `patches/0002-config.sub.patch`: Add harmonyos* to config.sub recognized OS list
- `conanfile.py`: Fix `umask 077` issue in configure template for HarmonyOS HMDFS compatibility

## 依赖版本

No build dependencies required. bash-completion is a pure shell script collection.

## 验证结果

```bash
conan create ... → SUCCESS
conan-verify G1-G4 + L2/L4/L5 → ALL PASS
test_package: 5 assertions verifying installed scripts exist
```

## 注意事项

- bash-completion is a shell script package, not a compiled library
- package_type = "application" (no .so/.a files)
- The `umask 077` fix in conanfile.py is HarmonyOS-specific and handled via `replace_in_file`
- GitHub direct download is blocked; use ghproxy.net mirror or conan-verify's ghfast.top injection

**编译结束**: 2026-08-05 06:55
**最终状态**: published
---

**编译结束**: 2026-08-05 07:05
**最终状态**: built
