# macchanger 1.7.0-r3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 1. Source from GitHub tag archive lacks configure script
autoreconf -fi

# 2. Fix E129: HMDFS umask issue
sed -i 's/umask 077/umask 022/g' configure

# 3. Configure
./configure --prefix=$DEFAULT_PREFIX

# 4. Build (MAKEINFO=true to skip texinfo doc build)
make -j1 MAKEINFO=true

# 5. Install
make install DESTDIR=$TEST_PREFIX MAKEINFO=true

# 6. Test
make check  # no-op for macchanger
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | caddr_t not defined | OHOS doesn't have caddr_t type | Patch: replace (caddr_t) with (char *) in src/netinfo.c |
| 2 | config.status permission denied | E129: HMDFS umask 077 creates drwx--S--- | sed s/umask 077/umask 022/ in configure |
| 3 | makeinfo missing/failing | texinfo Perl version mismatch | MAKEINFO=true to skip doc build |
| 4 | No configure script | GitHub tag archive doesn't include generated files | autoreconf -fi in conanfile.py build() |

## 源码修改

- patches/0001-src-netinfo.c.patch: Fix caddr_t → char* (portability)

## 依赖版本

无外部依赖

## 验证结果

```bash
$ macchanger --version
GNU MAC changer 1.7.0
Written by Alvaro Lopez Ortega <alvaro@gnu.org>
```

Conan verification: ALL PASS (G0-G4, L2/L4/L5)
W3 Local CI simulation: PASS

---

**编译结束**: 2026-08-07 03:07
**最终状态**: built
