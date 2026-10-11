# DRAFT-ohos-libc-missing-family-variant-entrypoints：OHOS libc 缺少 utmp/pwd 族的"变体入口"

> Contributor: Lee-BX | Status: Draft | Updated: 2026-10-04
> Source: trousers 0.3.15 / tpm-tools 1.3.9.2 HarmonyOS PC 适配
> 对应：knowledge/drafts/DRAFT-ohos-libc-missing-family-variant-entrypoints.kv
> 相关：E121（utmp 有、utmpx 整族无）、DRAFT-cconv-0.6.3-rindex-strrchr（BSD 遗留函数被裁）

## 现象

trousers 0.3.15 在 OHOS PC（aarch64-linux-ohos，clang 15）上编译/链接时先后出现：

```text
# tcsd/platform.c
error: incompatible integer to pointer conversion assigning to 'struct utmp *' from 'int'
   next = getutid(&ut);
          ^ ~~~~~~~~~~~

# 补上 extern 原型后，链接期
ld.lld: error: undefined symbol: getutid

# tspi/ps/tspps.c（消费者链接静态库时才暴露）
ld.lld: error: undefined symbol: getpwent_r
>>> referenced by tspps.c:100 (get_user_ps_path)
>>>               libtspi.a(libtspi_la-tspps.o)
```

三种症状其实是同一类根因的不同阶段：**函数所属的 API 族存在，但族内的"变体入口"被 libc 裁掉了**。

## 根因

OHOS 的 libc（musl 系）只实现 utmp/pwd 两族的基础迭代器：

| 族 | 平台提供 | 平台缺失 | 上游用法 |
|----|---------|---------|---------|
| utmp | `setutent` / `getutent` / `endutent` | `getutid` / `getutxid` | 按 `ut_type` 定位 RUN_LVL 记录 |
| pwd | `setpwent` / `getpwent` / `endpwent` | `getpwent_r` | 可重入遍历，按 uid 找 home |

关键点与 **E121** 不同：E121 是"有 utmp、没有 utmpx 整族"，本条是族内的**高阶/可重入变体**被裁。
因此补声明、加 `#define` 都救不了——符号本身不存在，必须换成族内的基础迭代器。

## 判定方法（先查再改）

```sh
SYSR=$(dirname $(clang -print-file-name=libc.so))          # SDK sysroot
nm -D "$SYSR/libc.so" | grep -wE 'getutid|getutxid|getpwent_r|getutent|getpwent'
grep -rn 'getutid\|getpwent_r' "$(dirname $SYSR)/include" 2>/dev/null
```

- 符号在、原型缺 → 补 `extern` 原型即可（最小改动）。
- 符号也不在 → 用同族基础迭代器改写（本次情况）。
- 特别提醒：**构建机（/system/lib64/libc.so）与链接用的 SDK sysroot libc 不是同一份**，
  device 上有 `getutid` 而 sysroot 里没有时，编译能过、CI 链接失败。

## 处置（等价改写，R8：不引入平台宏）

```c
/* utmp 查询：getutid(&ut) -> 基础迭代器 + 类型过滤 */
setutent();
while ((next = getutent()) != NULL) {
        if (next->ut_type != RUN_LVL)
                continue;
        /* ... 原逻辑 ... */
}
endutent();

/* pwd 遍历：getpwent_r(...) -> 基础迭代器（上游 BSD 分支本来就这么写） */
setpwent();
while ((pwp = getpwent()) != NULL) {
        if (euid == pwp->pw_uid) { home_dir = strdup(pwp->pw_dir); break; }
}
endpwent();
```

## 验证

```text
trousers 0.3.15：conan create rc=0；消费者 6/6 通过；W3 本地 CI 100%
tpm-tools 1.3.9.2：conan create rc=0；消费者 4/4 通过（库 API + tpm_version CLI 冒烟）
```

## 通用化建议

1. 移植任何"账户/终端/登录"相关组件前，先按族盘点：utmp/utmpx、pwd/grp、termios、nsswitch。
2. 族内出现一个变体缺失时，同族其它 `_r` / `*id` 变体大概率也缺失，一次性排查，避免
   "库编过、消费者链接失败"这种更晚暴露的坑。
