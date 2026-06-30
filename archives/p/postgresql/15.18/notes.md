# postgresql 15.18 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-09
- 编译器: clang/clang++
- 状态: published
- 平台: HarmonyOS NEXT aarch64 (musl libc)

## 编译步骤

1. 下载源码: `postgresql-15.18.tar.bz2` (23,405,115 bytes)
2. `ohc-run.py init-build postgresql 15.18` — 生成构建上下文
3. 修补 `config/config.guess` — 添加 HarmonyOS 识别 (`aarch64-unknown-linux-ohos`)
4. 修补 `config/config.sub` — 添加 `ohos-linux` 三元组映射和 `ohos*` 白名单
5. 修补 `configure` — 去除 `umask 077`（HMDFS 兼容）
6. 运行 configure:
   ```
   ./configure \
     --prefix=/storage/Users/currentUser/usr/local \
     --disable-thread-safety \
     --with-ssl=openssl \
     --with-readline \
     --with-zlib \
     --with-lz4 \
     --with-zstd \
     --without-icu \
     --without-llvm
   ```
7. `make -j$(nproc)` — 编译成功
8. `make install DESTDIR=$TEST_PREFIX` — 安装成功 (bin=33, lib=21)
9. `ohc-run.py package` — 打包 aarch64 + aarch64-debug tar.gz
10. `ohc-run.py finish postgresql 15.18 published` — 收尾归档

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 不包含 HarmonyOS 系统 | 添加 `*:HarmonyOS:*:*` case 分支，输出 `aarch64-unknown-linux-ohos` |
| 2 | config.sub 三元组验证失败 | config.sub 不认识 `ohos` 操作系统 | 添加 `ohos-linux` 三元组映射、`ohos*` 白名单和 `linux-ohos*` 系统验证 |
| 3 | musl pthread_cancel 缺失/不完整 | musl libc 的 pthread_cancel 符号存在但行为不完整 | 使用 `--disable-thread-safety` 预防 |
| 4 | HMDFS 上 umask 077 创建的目录归属异常 | HMDFS 上 umask 077 创建目录归属 uid 20001006，当前用户 uid 20020082 无法写入 | 修补 configure 去除 umask 077（两处：mktemp 和 mkdir） |
| 5 | HMDFS 不支持符号链接 ln -sf | HMDFS 文件系统不支持 ln -sf 覆盖已存在文件 | 预扫描标记为风险但未阻断 make/install |

## 源码修改

3 个补丁文件:
- `0001-config-config.guess.patch` (+11/-0): 添加 HarmonyOS 系统识别
- `0002-config-config.sub.patch` (+7/-1): 添加 ohos 三元组映射和白名单
- `0003-configure.patch` (+2/-2): 去除 umask 077 (HMDFS 兼容)

## 依赖版本

- readline (static .a)
- ncursesw (static .a, 无 .pc)
- openssl/libcrypto (.a/.so)
- zlib (.a/.so)
- lz4 (.a)
- zstd (.a)
- bz2 (.a/.so)

## 验证结果

- make 编译: 成功 (0 errors)
- make install: 成功 (bin=33, lib=21)
- 打包产物: postgresql-15.18-aarch64-ohos.tar.gz + postgresql-15.18-aarch64-ohos-debug.tar.gz

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| postgresql-15.18-aarch64-ohos.tar.gz | ~4.6MB | 稳定版运行包 |
| postgresql-15.18-aarch64-ohos-debug.tar.gz | ~20MB | 调试符号包 |

## 注意事项

- musl libc 下必须使用 `--disable-thread-safety`
- HMDFS 不支持 `ln -sf` 覆盖符号链接，需用 `rm -f && ln -s` 替代
- ppoll 在 OHOS 上不可用（预扫描标记但未阻断编译）
- /tmp 为只读，需使用 `$TMPDIR` 作为临时目录