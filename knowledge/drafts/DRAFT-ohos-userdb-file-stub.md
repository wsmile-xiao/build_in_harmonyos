# DRAFT-ohos-userdb-file-stub — OHOS musl 补 passwd/group/shadow 文件访问函数 stub

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-03
> **Severity**: 🟡 medium | **Category**: ohos / musl / passwd / shadow / group

## 相关既有条目（同族差异化定位）

本 skill 与既有 "musl libc 缺失" 条目共享 OHOS musl 兼容层背景，但本条目是
**整族 passwd/group/shadow 文件访问函数缺失**——非重复条目；申报路径 B 时以
此差异化定位为准。

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E081**（secure_getenv） | 正式收录 | musl 无 secure_getenv（单函数） | 非本题——那是**单函数**且可降级 getenv；本条目是**整族文件访问函数**（getspnam(-r)/putpwent/putspent/putgrent/fgetpwent/fgetspent/fgetgrent），OHOS 无 /etc/passwd//etc/shadow//etc/group，只能 stub |
| **E085/E127**（pthread 取消族） | 正式收录 | musl 无 pthread_cancel 族 | 同族（函数族 stub），但**符号族不同**——pthread 取消 vs passwd/shadow/group 文件访问 |
| **polkit 0001 getspnam stub**（配方实践，未沉淀为 E） | 配方实践 | polkit 的 getspnam 存根（返回 NULL+EACCES） | 与 polkit 同族但**函数面更全**——本条目覆盖 getspnam(-r)+putpwent+putspent+putgrent+fgetpwent+fgetspent+fgetgrent 七函数族（读/写两方向），polkit 只存根 getspnam 单函数 |
| **E493**（program_invocation_name） | 正式收录 | musl 无 glibc 符号 | 非本题——那是**数据符号** |

> 全库查证（2026-09-03）：`getspnam`/`putpwent`/`putspent`/`fgetpwent`/passwd/
> shadow 文件访问 stub 命中 0 条——无正面撞车；本条目为真增量。

## Scope（何时用）

在 OHOS 上编译、读取/写入 passwd/group/shadow 文件（或调用这些 glibc 文件访问
函数）的库时，若出现：

- `call to undeclared function 'putpwent'`（user-util.c 的 putpwent_sane）；
- `call to undeclared function 'putspent'`（putspent_sane）；
- `call to undeclared function 'putgrent'`（putgrent_sane）；
- `call to undeclared function 'fgetpwent'`/`fgetspent`/`fgetgrent`（user-util.c）；
- `call to undeclared function 'getspnam_r'`（user-record-nss.c）；
- `call to undeclared function 'getspnam'`（firstboot.c）。

典型实例：systemd/261。

## Symptom

```text
user-util.c:973: error: call to undeclared function 'putpwent'
user-record-nss.c:194: error: call to undeclared function 'getspnam_r'
firstboot.c:1190: error: call to undeclared function 'getspnam'
```

## Root Cause

1. glibc 的 `<pwd.h>`/`<grp.h>`/`<shadow.h>` 声明 passwd/shadow/group 文件访问
   函数（getspnam/getspnam_r/putpwent/putspent/putgrent/fgetpwent/fgetspent/
   fgetgrent）；
2. OHOS musl 不提供这些函数（OHOS 不管理 /etc/passwd、/etc/shadow、/etc/group）；
3. 使用这些接口的库编译报 `call to undeclared function`（ISO C99 起隐式声明是错误）。

## Recommended Solution

**主方案：musl 兼容头补声明 + userdb.c stub 实现。**

- `src/include/musl/pwd.h`/`grp.h`/`shadow.h`：`include_next` 后补函数声明；
- `src/libc/musl/userdb.c`：读函数返回 NULL + errno（OHOS 无这些文件，`getspnam`
  返回 NULL+EACCES 与 polkit 存根语义一致），写函数返回 -1 + ENOSYS；
- 注册 userdb.c 进 musl 编译单元（`src/libc/musl/meson.build`）。

```c
struct spwd *getspnam(const char *name) { (void) name; errno = EACCES; return NULL; }
int getspnam_r(const char *name, struct spwd *result_buf, char *buf,
               size_t buflen, struct spwd **result) {
        (void) name; (void) result_buf; (void) buf; (void) buflen;
        *result = NULL; errno = EACCES; return EACCES;
}
struct passwd *fgetpwent(FILE *stream) { (void) stream; return NULL; }
int putpwent(const struct passwd *pw, FILE *stream) {
        (void) pw; (void) stream; errno = ENOSYS; return -1;
}
/* fgetspent/fgetgrent → NULL；putspent/putgrent → -1+ENOSYS */
```

**回退方案**：若 stub 不可行，patch 源码绕开 passwd/shadow 文件访问——改动面大，
不推荐。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| **systemd/261** | 主验证（本 PR） | ✅ 覆盖前 getspnam(-r)/putpwent/putspent/putgrent/fgetpwent/fgetspent/fgetgrent 系列报 undeclared；补声明+stub 后编译通过，conan create 通过 |

## 测试覆盖边界

- stub 只在 **OHOS 无这些文件**下生效（读返回 NULL/ENOENT、写返回 ENOSYS），不改变
  有 passwd/shadow/group 文件的平台行为；
- 声明通过率时：以 conan create 全流程（libsystemd.so.0.44.0 链接 + test_package
  R34）为实证；systemd 上游测试按 rule 1.2 平台限制声明（需运行中的 systemd 环境）。
