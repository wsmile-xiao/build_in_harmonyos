# DRAFT: trickle 1.08 — AC_TRY_RUN libc 访问探测在 OHOS 交叉编译下的默认值选择

- Status: UNMATCHED
- Category: build-system / autotools / cross-compile
- Keywords: AC_TRY_RUN, cross compile, dlopen, libc.so, musl, trickle, E064, configure
- Related: E064 (conftest 无法执行), E004/E088 (musl dlsym / namespace)

## 现象

trickle（用户态带宽整形，LD_PRELOAD 型工具）的 configure.in 用两组
`AC_TRY_RUN` 在**运行时**探测如何拿到 libc 句柄：

1. 符号是否需要下划线前缀（`dlsym(dh, "_underscoreprobe")`）；
2. 能否不 dlopen 直接 `dlsym((void*)-1, "printf")`（NODLOPEN）；
3. 否则逐个 `dlopen("libc.so" / /lib/libc.so.* / /usr/lib/libc.so*)`。

OHOS aarch64 交叉编译时测试程序无法执行，三条全落到"no"，最终
`configure: error: cannot figure out how to access libc` 中止配置。

## 根因

`AC_TRY_RUN` 的第四个参数（cross-compiling action）在上游 configure.in
里全部写成 `AC_MSG_RESULT(no)`，且 libc 访问探测没有 cache 变量，无法用
`ac_cv_*` 预置绕过——这是"无法执行 conftest"（E064 模式）叠加"无 cache
变量"的组合问题。

## 方案

给第 2 组探测（NODLOPEN probe）的 cross action 定义 musl 语义默认：

```m4
[AC_MSG_RESULT(cross-compiling: assuming dlopen("libc.so") works)
    AC_DEFINE_UNQUOTED(DLOPENLIBC, "libc.so")
    HAVEMETHOD=yes])
```

依据：musl 的 dlopen 对 "libc.so" 特判，返回已加载 libc 的句柄；
trickle-overload.c 运行时 `dlopen(DLOPENLIBC, RTLD_LAZY)` +
`dlsym(dh, "connect"/"send"/...)` 在 musl/OHOS 上成立。符号下划线探测
cross 默认 no 对 musl 也是正确值（musl 符号无下划线前缀），无需改。

## 验证状态

- 本机：13 个补丁链（含本条）对 Debian 1.08+ds 源码 git apply 全通过。
- 真机：待 shadow CI 验证 `dlopen("libc.so")` 是否返回有效句柄；若失败
  （报 "[trickle] Failed to open libc"），备选方案是定义 NODLOPEN 改用
  `dlsym(RTLD_DEFAULT)` 路径——但上游代码 NODLOPEN 分支用 `(void*)-1`
  句柄，需要另行 patch trickle-overload.c，当前方案优先。

## 适用面

任何用 AC_TRY_RUN 探测运行时动态链接器行为、且无 cache 变量的老
autotools 项目交叉到 OHOS 时，同样适用"cross action 给 musl 语义默认"。
