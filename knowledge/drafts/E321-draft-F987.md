# E321 — gnulib weak-symbol 探测在 musl/OHOS 引用不存在的 pthread_cancel

## 错误签名
```
glthread/lock.h:152:16: warning: weak identifier 'pthread_cancel' never declared
regcomp.c:648:7: error: use of undeclared identifier 'pthread_cancel'; did you mean 'pthread_once'?
(共 8 处 error: regcomp.c × 4 + regexec.c × 4)
```

## 触发场景
内嵌旧版 gnulib 的 autotools 项目 (libdap 3.20.6 的 gl/ 模块) 在
OHOS (musl libc) 上编译 regex/lock 相关源文件。configure 检测出
`USE_POSIX_THREADS_WEAK=1`，glthread/lock.h 走 weak 探测路径
`#pragma weak pthread_cancel`，而 musl 不提供 pthread_cancel 符号。

## 根因
- gnulib 的 threadlib.m4 用 `#pragma weak xyzzy` 探测链接器 weak 支持
- 探测通过后（OHOS lld 支持 weak），`pthread_in_use()` 定义为
  `(pthread_cancel != NULL)` —— 但 musl 头文件没有声明 pthread_cancel
- clang 报 undeclared identifier，#pragma weak 警告伴随 8 个编译错误

## 推荐修法 (rec_approach)
patch `gl/m4/threadlib.m4`（或上游对应 threadlib），在 AC_CACHE_CHECK 前
强制 OHOS 平台的 cache 值:
```m4
case "$host_os" in
  linux-ohos* | ohos*) gl_cv_have_weak=no ;;
esac
```
configure 参数传 `gl_cv_have_weak=no` 双保险（cache 变量可预设）。

## 关联
- 影响: 所有携带 gnulib glthread (regex/lock) 的 autotools 包
- 关联条目: E064 (conftest 运行), E002 (/tmp 只读)
- 实测案例: libdap 3.20.6 (archives/l/libdap/3.20.6)

# 附带发现（同次适配中记录）

## musl loader LD_LIBRARY_PATH 空格段陷阱
系统默认 `LD_LIBRARY_PATH` 含 `"         /system/lib64"`（空格前缀段）。
musl loader 遇到路径**中间**的该段后，后续所有段全部失效（实测 471 字符
路径下 conftest 找不到 libc++_shared.so；空格段移到末尾或剔除后恢复）。
修法: 配方 generate() 清洗空格段后用 env.define 重建。

## ohos-sdk lld 的 libxml2.so.16 遮蔽冲突
ohos-sdk 的 lld 二进制自身 NEEDED libxml2.so.16（正确版本在
`<sdk>/ohos/native/llvm/lib`）。conan 依赖 libxml2/2.15.3 的同名 .so
排在 LD_LIBRARY_PATH 前面时，lld 加载 conan 版后符号 relocating 失败
（`xmlFreeDoc: symbol not found` 等一连串），表现为"C++ compiler cannot
create executables"（易误诊为编译器问题）。修法: sdk llvm/lib 排
LD_LIBRARY_PATH 最前（从 tools.build:compiler_executables 的 realpath 推导）。

另注: `/data/storage/el1/bundle/libs/arm64` 含同名但符号集不兼容的
libc++_shared.so，必须让 /system/lib64 的正确版本先命中。
