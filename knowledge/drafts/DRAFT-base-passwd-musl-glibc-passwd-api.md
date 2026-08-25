# DRAFT — OHOS musl libc 不提供 glibc 专用密码数据库 API

> 状态: 草稿（仅服务 base-passwd 3.6.8，待查重/提升）。

## 真实问题

`conan create` 编译 `update-passwd.c` 时报错：

```
update-passwd.c:534:19: error: incompatible integer to pointer conversion
  assigning to 'struct passwd *' from 'int' [-Wint-conversion]
    while ((result=fgetpwent(input))!=NULL) {
                  ^~~~~~~~~~~~~~~~~
update-passwd.c:573:19: error: calling 'fgetgrent'
    while ((result=fgetgrent(input))!=NULL) {
                  ^
update-passwd.c:613:19: error: calling 'fgetspent'
    while ((result=fgetspent(input))!=NULL) {
                  ^
update-passwd.c:1213:6: error: calling 'putspent'
    if (putspent(&(shadow->d.sp), output)!=0) {
        ^
update-passwd.c:1493:9: error: calling 'lckpwdf'
    if (lckpwdf()!=0) {
        ^
update-passwd.c:1505:9: error: calling 'ulckpwdf'
    if (ulckpwdf()!=0) {
        ^
```

**根因**: OHOS SDK 的 libc（musl）不实现以下 glibc 扩展函数：
- `fgetpwent()` — 从 FILE 流读取 passwd 条目
- `fgetgrent()` — 从 FILE 流读取 group 条目
- `fgetspent()` — 从 FILE 流读取 shadow 条目
- `putspent()` — 写入 shadow 条目到 FILE 流
- `lckpwdf()` / `ulckpwdf()` — 密码数据库锁定/解锁

这些函数是 glibc 的扩展，不在 POSIX 标准中，musl 没有实现。

## 兼容方案

通过 `-include musl-compat.h` 注入兼容实现，使用 `fgets()` + 冒号字段解析替代：

| 缺失函数 | 替代实现 |
|---------|---------|
| `fgetpwent()` | `fgets()` + `strchr()` 按 `:` 切分 7 字段 |
| `fgetgrent()` | `fgets()` + 按 `:` 切分 + 成员列表 `,` 切分 |
| `fgetspent()` | `fgets()` + 按 `:` 切分 9 字段 |
| `putspent()` | `fprintf()` 格式化输出 |
| `lckpwdf()` | no-op（OHOS 不修改系统密码文件） |
| `ulckpwdf()` | no-op |

完整实现见 `archives/b/base-passwd/3.6.8/patches/musl-compat.h`。

## 知识库查重

| 关键词 | 命中条目 | 覆盖结论 |
|--------|---------|---------|
| musl + glibc composer | E020, E093, E063, E032 | 部分覆盖 — 通用 musl/glibc 兼容模式 |
| getpass missing function | E093 | 最接近 — 但处理的是 `getpass` 而非 `fgetpwent` 系列 |
| `fgetpwent`/`fgetgrent`/`fgetspent`/`putspent`/`lckpwdf`/`ulckpwdf` | **无命中** | 未覆盖 — 本 DRAFT 首次记录 |

**判定**: 现有知识库有 musl/glibc 兼容性问题的通用模式，但没有专门针对密码数据库 API 的条目。这些函数在多个 Debian 密码管理工具中可能遇到，具有跨库复用价值。建议提升为正式 E-entry。