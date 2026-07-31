# bison 3.8.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-26
- 编译器: clang
- 状态: built

## 编译步骤
```bash
./configure --prefix= --disable-nls --no-create
./config.status    # patched: umask 077 → 000, chmod 777 on ac_tmp
make -j1 MAKEINFO=true
make install DESTDIR=... MAKEINFO=true
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 创建的临时目录权限 0700，HMDFS 上无法写入文件 | autotools 默认 `umask 077 && mktemp -d`，OHOS 文件系统不允许向 0700 目录写文件 | 在 build() 中 patch config.status：`umask 077` → `umask 000`，并在 `ac_tmp=$tmp` 后插入 `chmod 777 "$ac_tmp"` |
| 2 | `make` 在 `doc/` 子目录失败（缺 texinfo/makeinfo） | CI 环境无 texinfo | `make MAKEINFO=true` 来跳过文档构建 |
| 3 | AWK/sed 默认在 /system/bin 不在 PATH，configure 掐中找不到 | OHOS 默认 PATH 不含 hnp | 显式设置 `PATH="/data/service/hnp/bin:$PATH"`、`AWK=/data/service/hnp/bin/awk` |
| 4 | config.sub/config.guess 不识别 HarmonyOS OHOS 三元组 | 上源未含 OHOS case | patches/0001、0002 增加 `HarmonyOS` 和 `__OHOS__` 识别 |
