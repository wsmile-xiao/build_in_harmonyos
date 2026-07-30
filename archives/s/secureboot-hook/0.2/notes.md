# secureboot-hook 0.2 适配笔记

## 编译环境
- 构建系统: makefile (simple file-copy Makefile)
- 编译日期: 2026-06-05
- 编译器: clang/clang++ (not used — script-only package)
- 状态: published

## 编译步骤

1. Examine original Makefile — found it lacks DESTDIR/PREFIX support
2. Modify Makefile to add DESTDIR and PREFIX variables, remove `-o root`, replace hardcoded paths
3. Track edit via `ohc-run.py track-edit`
4. Run `make install DESTDIR=$HOME/tmp/test-install-secureboot-hook-0.2 PREFIX=$HOME/usr/local`
5. Generate patch via `ohc-run.py refresh-patch --auto`
6. Run verify-build (PASS)
7. Run packaging via `ohc-run.py package`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile lacks DESTDIR/PREFIX support | Original Makefile uses hardcoded `/etc/` paths | Added DESTDIR and PREFIX variables to Makefile |
| 2 | `install -o root` fails without root | Void Linux package assumes root install | Removed `-o root` flag from install commands |
| 3 | manifest.yaml missing `build_system` field | Template had `system` nested under `build:` but not top-level `build_system:` | Added `build_system: makefile` as top-level key |
| 4 | No debug package | No ELF binaries — pure shell script/config | N/A (script-only tools) |

## 源码修改

- `0001-Makefile.patch`: Added DESTDIR/PREFIX support, removed `-o root`, replaced `find` with explicit `rm -f` in remove target

## 依赖版本

- No compile dependencies (script-only package)
- Runtime dependencies: dracut, sbctl, binutils (Void Linux specific)

## 验证结果

```bash
# make install DESTDIR=~/tmp/test-install-secureboot-hook-0.2 PREFIX=~/usr/local
installing the hook...
hook has been installed

# ls -laR ~/tmp/test-install-secureboot-hook-0.2/
# Two files installed:
#   /etc/kernel.d/post-install/30-secureboot (755)
#   /etc/kernel.d/secureboot.conf (644)

# verify-build: PASS
# G1: ✅0 ⚠️0 ❌0 (no binaries — script package)
# G2: ✅0 ⚠️1 ❌0 (no binaries to test)
# G3: ✅0 ⚠️0 ❌0 (no ELF → no RPATH/signature checks needed)
# G4: ✅0 ⚠️0 ❌0 (manifest and archive OK)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| secureboot-hook-0.2-ohos-aarch64.tar.gz | 9KB | Main package (shell script + config) |
| 0001-Makefile.patch | 981B | DESTDIR/PREFIX support patch |

## 注意事项

- This is a Void Linux-specific kernel hook; runtime functionality depends on Void Linux ecosystem (xbps, dracut, sbctl)
- The shell script sources `/etc/os-release` and checks for `NAME == "Void"`, which won't match on HarmonyOS NEXT
- No debug-symbols package needed (no ELF binaries)
- Packaging was successful despite no compilation — this is a file-copy-only package
---

**编译结束**: 2026-07-15 16:59
**最终状态**: built
