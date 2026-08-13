# mutt 2.4.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-23
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载并校验源码 (HTTPS 证书 hostname mismatch, 但传输加密有效; sha256 校验完整性):
   ```bash
   curl -L -o mutt-2.4.1.tar.gz https://ftp.mutt.org/pub/mutt/mutt-2.4.1.tar.gz
   echo "5624321f0b1cc1eff6cab9ef08f25954ff64c51b33d4bf3b99484cf1edd8cfff  mutt-2.4.1.tar.gz" | sha256sum -c
   ```
2. 初始化编译: `ohc-run.py init-build mutt 2.4.1 --url=https://ftp.mutt.org/pub/mutt/mutt-2.4.1.tar.gz` (sha256 由 conandata.yml 自动校验)
3. 修复 config.guess (E007): 添加 __OHOS__ LIBC 检测和 HarmonyOS 系统识别
4. 修复 config.sub (E007): 添加 ohos-linux triplet
5. 修复 umask 077 (E011): sed 修改 configure 中 umask 077 为 umask 022
6. 修复 check_sec.sh (E002): /tmp 路径改为 ${TMPDIR:-/tmp}
7. 修复 shebang: /bin/sh → /system/bin/sh (HarmonyOS 无 /bin/sh)
8. Configure: `./configure --prefix=$DEFAULT_PREFIX --enable-imap --enable-pop --enable-smtp --enable-sidebar --with-ssl --with-curses --with-homespool=Mail --with-mailpath=/var/mail`
9. Make: `make -j1`
10. Staging install: `make install DESTDIR=$TEST_PREFIX`
11. Local install: `make install`
12. make check: check_sec.sh 通过 (shellcheck 缺失为非关键)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007: GNU config.guess 不包含 HarmonyOS 检测分支 | build() 中 inline 修改 config.guess |
| 2 | configure umask 077 权限错误 | E011: HMDFS umask 077 导致临时目录不可写 | umask 077 → 022 |
| 3 | check_sec.sh /tmp 只读 | E002: /tmp 在 OHOS 上只读 | mktemp -p ${TMPDIR:-/tmp} |
| 4 | shebang /bin/sh 不存在 | HarmonyOS 无 /bin/sh | 替换为 /system/bin/sh |
| 5 | conandata patches 与 mutt PATCHES 冲突 | HMDFS 大小写路径冲突 | patches 在 build() 内联修改，不使用 export_conandata_patches |

## 依赖版本

- ncurses: 6.5 (静态编译, R26)
- openssl: 3.5.6
- zlib: 系统内置

## 验证结果

```bash
$ mutt -v
Mutt 2.4.1 (2026-07-04)
System: HarmonyOS HongMeng Kernel 1.12.0 (aarch64)
ncurses: ncurses 6.5 (compiled with 6.5, recipe available in 制品仓)
+USE_POP +USE_IMAP +USE_SMTP +USE_SSL_OPENSSL +HAVE_COLOR +USE_SIDEBAR
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (内联补丁) |
| conandata.yml | 源码 URL + sha256 |
| test_package/ | Conan L1 测试 (mutt -v) |
| patches/ | 4 个补丁文件 (归档参考) |
| commands.json | 命令行工具声明 (R38) |

## 注意事项

- mutt 需要指定邮件存储路径 (--with-homespool, --with-mailpath)
- HMDFS 文件系统上需要修改 configure 中的 umask 077 为 umask 022
- conandata.yml 不声明 patches，因 HMDFS PATCHES/patches 大小写冲突
- 补丁在 build() 中通过 replace_in_file 内联应用
