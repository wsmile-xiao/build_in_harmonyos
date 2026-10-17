# mailutils 3.19 适配笔记

## 编译环境

- 构建系统：autotools（GNU Autoconf / Automake / Libtool）
- 编译日期：2026-09-27
- 编译器：clang / clang++（OHOS SDK，aarch64-linux-ohos）
- 平台：HarmonyOS PC，profile `ci/conan/profiles/ohos-aarch64`
- 状态：published（conan-verify G0-G4 + L2/L4/L5 通过）

## 编译步骤

```bash
# 手工（探索阶段）
./configure --prefix=$DEFAULT_PREFIX --disable-python   # 打完全部补丁后
make -j4
make -k check
make install DESTDIR=$TEST_PREFIX

# Conan（配方内，build() 依次执行 configure / make / make -k check / make install DESTDIR）
conan create archives/m/mailutils/3.19 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess: unable to guess system type`（并伴随 dummy.c 写入 Permission denied） | config.guess 无 HarmonyOS 分支；且临时目录 `umask 077` 建出 0700 目录，HMDFS UID 映射下不可写 | 补丁 0001/0002：`patch-autotools-ohos.pl` + 手动补 `linux-ohos*` 内核项，config.guess 直接输出 `aarch64-unknown-linux-ohos`（E007）；不使用 `--build/--host` 绕过 |
| 2 | `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 把目录 owner 映射为固定 UID，`umask 077` 的临时目录对当前进程不可写 | 补丁 0005：configure 中 `umask 077` → `umask 022`（E011） |
| 3 | `system.c: call to undeclared function 'getspnam'` | OHOS libc 有 `shadow.h` 但无 `getspnam()` | 补丁 0004/0005/0007：configure 增加 `getspnam` 特性探针，源码用 `HAVE_GETSPNAM` 守卫 |
| 4 | `comsat.c: GETUTENT() 返回 int / endutxent 未声明` | OHOS 只提供 `utmp.h` 的 `getutent/setutent/endutent`，`utmpx.h` 只有结构体、无 `getutxent` 函数 | 补丁 0003/0004/0005：configure 增加 `getutxent` 探针，comsat 用 `HAVE_GETUTXENT` 选择分支 |
| 5 | `makeinfo: inaccessible or not found`（doc/texinfo） | toybox `ls` 输出 ISO-8601 日期，mdate-sh 解析失败 → version.texi 被环境变量表污染 → mailinfo 重建；worker 无 texinfo | 补丁 0006：把 `doc/texinfo/Makefile.in` 的 stamp-vti 规则置为 `@:`，保留发行包自带 info/man |
| 6 | `ld.lld: unable to find library -lintl` / `-lpython3.12` | OHOS Python 的 `python3-config` 输出 `-lintl -lpython3.12`，不在 Conan 依赖图中 | 使用 `--disable-python` 关闭可选 Python 绑定（无外部依赖） |
| 7 | `lock.at` 7 个用例 `lck: child lock failed` | 默认 dotlock 用 `link(2)` 原子建锁；HMDFS 不支持硬链接（EPERM） | 补丁 0008：`lock(2)` 失败于 EPERM/EOPNOTSUPP/ENOSYS 等时回退为 `O_EXCL` 直接建锁文件（E079） |

## 源码修改（补丁）

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001 | build-aux/config.guess | 增加 HarmonyOS 系统识别分支（输出 `<machine>-unknown-linux-ohos`） |
| 0002 | build-aux/config.sub | 增加 `ohos-linux` 三元组、`ohos*` OS 项、`linux-ohos*` 内核项 |
| 0003 | comsat/comsat.c | `#ifdef HAVE_UTMPX_H` → `#if defined(HAVE_UTMPX_H) && defined(HAVE_GETUTXENT)` |
| 0004 | config.h.in | 增加 `HAVE_GETSPNAM`、`HAVE_GETUTXENT` 探针槽位 |
| 0005 | configure | `umask 077` → `umask 022`（2 处）；新增 `getspnam`、`getutxent` 函数检查 |
| 0006 | doc/texinfo/Makefile.in | stamp-vti 规则配方置为 `@:`（不重建 version.texi/info） |
| 0007 | libmailutils/auth/system.c | shadow 分支守卫改为 `HAVE_SHADOW_H && HAVE_GETSPNAM` |
| 0008 | libmailutils/base/locker.c | dotlock 的 `link(2)` 失败时回退到 `O_EXCL` 建锁文件 |

补丁均为「特性探针 + 通用回退」，不含平台宏。

## 依赖版本

无外部强制依赖：核心框架使用自带 gnulib；可选集成（GnuTLS、GSSAPI、PAM、
Guile、readline、fribidi、SQL、DBM）保持关闭。

## 验证结果

```bash
conan create archives/m/mailutils/3.19 -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing   # rc=0
python3 scripts/ohc-run.py conan-verify mailutils 3.19      # G0-G4 + L2/L4/L5 通过
```

- 上游 `make check`：1355 用例 / 1164 通过 / 163 失败 / 28 跳过（失败均为沙箱
  限制，见 `reports/test-report.md`）。
- test_package：`test_mailutils.c`（11 项断言全过）+ 鸿蒙特有
  `test_ohos_mailutils.sh`（平台身份 / CLI 与服务端冒烟 / 版本号，全过）。

## 已知限制

- Python 绑定关闭（可选组件，OHOS Python 的 `-lintl/-lpython3.12` 不在
  Conan 依赖图中）。
- 服务端套件（imap4d/mail/mh/comsat）在无 passwd 记录的沙箱中失败，非库缺陷。
---

**编译结束**: 2026-09-27 06:36
**最终状态**: published
