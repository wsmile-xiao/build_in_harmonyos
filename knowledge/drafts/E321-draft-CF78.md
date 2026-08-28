# E321 — OHOS libc omits `_res`/`__res_state()` and `<linux/ip.h>`

## 错误特征
链接器报 `undefined reference to '_res'` 或 `undefined symbol: _res`；编译器报
`error: 'struct ip_options' has incomplete type` 或 `fatal error: linux/ip.h:
No such file or directory`。

## 触发条件
- 构建系统: 任意（autotools/cmake/meson/自定义 Makefile 均可触发）
- 阶段: make（链接阶段触发 _res）/ make（编译阶段触发 linux/ip.h）
- 平台: HarmonyOS PC（aarch64），glibc→bionic 迁移类软件

## 根因分析
OHOS libc（bionic 衍生）实现了 `res_init()`/`res_search()`/`res_query()` 等
解析器 API，但**不导出** glibc 的全局 `_res` 符号，也不提供 `__res_state()`
线程局部访问器。软件若用 `return &_res;` 获取解析器状态指针则会链接失败。
此外 OHOS NDK 头文件不提供 `<linux/ip.h>`，导致 `struct ip_options` 成为
不完整类型，引用该结构体的代码无法编译。

## 解决方案

### 推荐方案
在 OS 头文件中定义 `OS_GET_DNS_RESOLVER_RES` 跳过通用 `_res` 路径，并提供
进程级静态 `struct __res_state` 访问器；对 `ip_options` 定义 `NO_IP_OPTIONS`
并 `#undef GLIBC_IP_OPTIONS` 跳过已弃用的 IPv4 源路由路径。

```c
// OS/os.h-<plat>
#define OS_GET_DNS_RESOLVER_RES
#undef GLIBC_IP_OPTIONS
#define NO_IP_OPTIONS

// OS/os.c-<plat>
#include <resolv.h>
static struct __res_state s;
res_state os_get_dns_resolver_res(void) {
    if (!s.options & RES_INIT) res_ninit(&s);
    return &s;
}
```

### 禁止做法
- ❌ 直接 `return &_res;`（OHOS 无此符号，即便用 shim 静默链接，运行时
  解析器选项也不会生效）
- ❌ `#include <linux/ip.h>`（OHOS NDK 不提供此头文件）

## 验证
```bash
# 确认 _res 符号缺失
echo 'int main(void){extern int _res; return _res;}' > /tmp/t.c && \
  clang /tmp/t.c -o /tmp/t 2>&1 | grep -q 'undefined.*_res' && echo CONFIRMED
# 确认 linux/ip.h 缺失
echo '#include <linux/ip.h>' > /tmp/t.c && \
  clang -fsyntax-only /tmp/t.c 2>&1 | grep -q 'No such file' && echo CONFIRMED
```

## 关联条目
- caused_by: E320（OHOS NDK 头文件与系统调用面与 Linux/glibc 差异）
