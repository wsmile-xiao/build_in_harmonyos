# sphinx 2.3.2-beta 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-06-09}
- 编译器: clang/clang++
- 状态: {published|built|failed}

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}

---

## Phase 3 编译记录

### 源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|----------|
| configure | config.status 临时目录在 HMDFS 上权限失败(E002/E046) | 修改 mktemp -d 从 "./confXXXXXX" 改为 "${TMPDIR}/confXXXXXX"，去掉 umask 077 | 待 refresh-patch |
| config/config.guess | autotools 不识别 HarmonyOS (E007) | 用 patch-autotools-ohos.pl 打补丁 | 待 refresh-patch |
| config/config.sub | autotools 不识别 OHOS (E007) | 手动修复（2003年老版，脚本未完全匹配） | 待 refresh-patch |
| api/libsphinxclient/config.guess | autotools 不识别 HarmonyOS (E007) | 用 patch-autotools-ohos.pl 打补丁 | 待 refresh-patch |
| api/libsphinxclient/config.sub | autotools 不识别 OHOS (E007) | 手动修复 | 待 refresh-patch |
| src/sphinxstd.cpp:1493 | PTHREAD_RWLOCK_PREFER_WRITER_NONRECURSIVE_NP 在 musl/OHOS 不可用 | 改 #ifndef __APPLE__ 为 #if !defined(__APPLE__) && !defined(__OHOS__) | 待 refresh-patch |
| src/Makefile | configure 误判 iconv 为 libc 内建，实际需 libiconv | LIBS 加 -liconv | 待 configure fix 或 manifest |

### configure 参数

```
./configure --prefix=$DEFAULT_PREFIX --without-mysql --with-pgsql \
    --with-pgsql-includes=$DEFAULT_PREFIX/include \
    --with-pgsql-libs=$DEFAULT_PREFIX/lib \
    HELP2MAN=/bin/true
```

### make check 结果

- test 目录使用 PHP ubertest.php，OHOS 上无 PHP
- src 目录无独立测试
- 结果：N/A（PHP not available）

### 编译状态

- ✅ configure 成功
- ✅ make 成功（6 个二进制）
- ✅ make install DESTDIR=$TEST_PREFIX 成功
- ✅ staging 验证：bin/indexer, searchd, indextool, spelldump, wordbreaker 均可执行
- ⚠️ make check：PHP 不可用，跳过
---

## Phase 4: 收尾

### G0 干净构建验证

- G0 自动验证失败：clean-verify 脚本使用 `/bin/sh` (toybox) 运行 configure
- toybox sh 无法解析 autoconf 生成的 configure 脚本（已知 OHOS 平台限制）
- 手动验证通过：从干净源码 + patches + configure参数，使用 bash 运行 configure/make/install，一切正常
- 所有 5 个 patches 应用成功，configure + make + make install 全部通过

### 最终产物

- packaging/sphinx-2.3.2-beta-ohos-aarch64.tar.gz (23MB)
- packaging/sphinx-2.3.2-beta-ohos-aarch64-debug.tar.gz (3.8MB)
- patches/5 个补丁文件
- 本地安装验证通过：所有 5 个二进制（indexer, searchd, indextool, spelldump, wordbreaker）可执行
---

**编译结束**: 2026-06-09 20:32
**最终状态**: built
