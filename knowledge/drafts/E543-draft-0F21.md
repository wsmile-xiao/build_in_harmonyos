# E543 — autoconf 2.72 config.status 损坏旧版 ltmain.sh 的引号转义

- **分类**: autotools / libtool / compat
- **严重度**: 3
- **触发工具**: configure / make / libtool
- **阶段**: linking / packaging
- **发现于**: openconnect 8.10 适配（2026-09-02，设备实测）

## 错误特征

```
libtool: link: ar cru                    ← 无文件参数
Usage: ar [emulation options] ...        ← ar 打印用法
libtool[363]: syntax error: unexpected '}'   ← bash/mksh 解析失败
libtool: install: chmod 644              ← install 模式无文件名
.libs/lib$name.a                         ← 字面量 lib$name（变量未展开）
./libtool: line 906: print: command not found ← ksh 风格 ECHO
grep: //lib/libgpg-error.la: No such file or directory ← ohpcd .la 残留路径
libtool: error: '//lib/libgpg-error.la' is not a valid libtool archive
clang-15: error: no such file or directory: '../.libs/libpthread.a'
```

## 根因

2020 年代的 ltmain.sh（libtool 2.4.x，随 openconnect-8.10 等旧 release tarball 分发）早于 autoconf 2.72。新版 config.status 执行旧模板时：

1. **双引号提前展开**：`old_archive_cmds="$AR $AR_FLAGS $oldlib$oldobjs~..."` 中 `$oldobjs` 在赋值时展开为空（应为单引号延迟到 libtool 运行时 eval）
2. **过度转义**：`libname_spec='lib\$name'`——`\$` 在单引号里保留字面反斜杠，libtool 的 eval 展开失败，产出 `.libs/lib$name.a`
3. **ksh 风格 ECHO**：`ECHO="print -r --"`（第 63 行，晚于 808 行 printf fallback 定义但优先级更高）——OHOS /bin/sh 无 print 内建
4. **叠加 ohpcd .la 残留**：二进制包构建时 prefix=/，`.la` 里 `libdir='//lib'` + `dependency_libs` 指向过期包目录，libtool 递归解析报 "not a valid libtool archive"（cattle-1.0 CI#16082 同源问题）
5. **-lpthread 误解析**：libgpg-error 的 mtlibs 残留 `-lpthread`，旧 libtool 对其做 .la 解析推导出 `../.libs/libpthread.a`（musl 的 pthread 在 libc 内）

## 修复方案

配方 build() 内 configure 之后、make 之前修补生成的 libtool 脚本（确定性文本变换）：

1. 损坏的双引号模板赋值 → 单引号（恢复延迟展开语义）
2. `*_spec`/`*_cmds` 赋值行内 `\$` → `$`（去过度转义）
3. `ECHO="print -r --"` → `ECHO="printf %s\n"`
4. 损坏的多行 `archive_expsym_cmds` 置空（或 configure 加 `--disable-symvers`）
5. 依赖 `.la` 的 `libdir='//lib'` → 实际 conan 缓存路径；`dependency_libs` 与生成 Makefile 的 `LIBS` 剥离 `-lpthread`

## 参考实现

`archives/o/openconnect/8.10/conanfile.py`：`_fix_libtool_quoting()` / `_fix_dependency_la_paths()` / `_strip_libpthread_from_makefile()`（2026-09-02 设备验证通过，conan create G2 PASS + 上游 make check 3/3）

## 禁止做法

- 不要手改 Makefile 注入字面库路径（修 libtool 模板变量才是正解）
- 不要删除共享 conan 缓存里的依赖 .la（其他包构建依赖它们）
