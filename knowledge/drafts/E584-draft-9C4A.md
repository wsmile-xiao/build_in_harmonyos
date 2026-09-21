# E584 — OHOS libc/NDK 无 glibc 重入解析器 API（res_n*）：改用经典 res_query()/h_errno

## 错误特征

从 glibc/Linux 移植的 DNS 客户端代码在 OHOS 上编译或链接失败：

```text
resolver.cpp:53:14: error: use of undeclared identifier 'res_ninit'
resolver.cpp:168:9:  error: use of undeclared identifier 'res_nquery'
resolver.cpp:69:13:  error: use of undeclared identifier 'res_nclose'
# 或（若自行 extern 声明后）
ld.lld: error: undefined symbol: res_nquery
```

## 触发条件

- 构建系统: cmake（或任意）
- 阶段: compilation / linking
- 源码模式: `res_ninit(&state)` / `res_nquery(&state, ...)` / `res_nclose(&state)`
  或 `struct __res_state` 作为调用方状态

## 根因分析

OHOS 的 libc（musl 系）与 NDK 头文件只提供**经典非重入**解析器 API：

```text
NDK sysroot/usr/include/resolv.h 声明:
  res_init / res_query / res_querydomain / res_search / res_mkquery / res_send
  dn_comp / dn_expand / dn_skipname
设备侧 /system/lib64/libc.so 导出:
  res_init, res_query, res_querydomain, dn_expand(W), dn_skipname
```

`res_ninit` / `res_nquery` / `res_nclose` 既无声明也无符号；`struct __res_state`
类型虽然存在于头文件（"unused; purely for broken apps" 注释），但没有与之配套的
重入查询函数，OHOS 也不导出 glibc 的 `__res_state()` 线程局部访问器
（参见同族条目 E516：`_res`/`__res_state` 缺失）。

实测（smtpping 1.1.4 适配，2026-09-20）：
- `res_query("halon.io", C_IN, T_MX, buf, 65536)` 返回 66 字节、2 条 MX 答案，
  `dn_expand`/`dn_skipname` 解析正确 → 经典 API 运行可用；
- `h_errno` 为 libc 全局变量（`nm -D` 可见 `B h_errno`），`NO_DATA`（=4）语义完整。

## 解决方案

### 推荐方案

把查询入口整体替换为经典 API（进程级全局态），响应解析代码原样保留：

```cpp
// resolver.cpp
- int len = res_nquery(&m_res, domain.c_str(), C_IN, req_rec_type, response, sizeof response);
+ int len = res_query(domain.c_str(), C_IN, req_rec_type, response, sizeof response);
  if (len < 0) {
-     if (m_res.res_h_errno == NO_DATA)
+     if (h_errno == NO_DATA)
          return true;
      return false;
  }
// 构造/析构：删除 res_ninit(&m_res); / res_nclose(&m_res);
```

```cpp
// resolver.hpp：删除 struct __res_state m_res; 成员，补 #include <netdb.h>
- return m_res.res_h_errno;
+ return h_errno;
```

**适用前提**：程序单线程使用解析器，或通过 `fork()` 并发（每个子进程独立
副本）。多线程程序需自行加锁，或实现自包含 DNS 客户端（UDP 查询 + 报文解析）。

### 禁止做法

- ❌ 保留 `res_ninit/res_nquery/res_nclose` 并自行 `extern` 声明——只是把编译错误
  推迟为链接错误（OHOS 无这些符号）。
- ❌ 期望链接 `libresolv.a` 解决——OHOS 的 libresolv.a/libc.so 同样没有 `res_n*`。

## 验证

```bash
# 1) 负向验证：确认 res_n* 不存在
printf '#include <resolv.h>\nint main(){struct __res_state s;res_ninit(&s);return 0;}\n' > t.c
clang --target=aarch64-linux-ohos --sysroot=$OHOS_SDK/native/sysroot t.c -o t 2>&1 | grep res_ninit

# 2) 正向验证：经典 API 可编译、可运行、可解析
#    （见 smtpping test_package A15：MX->A/AAAA 回退路径在真机通过）
```

## 关联条目

- 相关: E516（OHOS libc 缺 `_res`/`__res_state` 访问器）、E020（musl 不透明类型）
- 实例: smtpping 1.1.4（补丁 0001/0002）、exim 4.99.5（E516）
