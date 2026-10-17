# htpdate 1.3.7 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-03
- 编译器: clang/clang++
- 状态: built

## 编译步骤

htpdate 是一个简单的 C 程序，使用 Makefile 构建，无需 configure 步骤。

1. 下载源码：从 GitHub 下载 v1.3.7 tag
2. 解压到 builds 目录
3. 使用 make CC=$CC CFLAGS="-Wall -std=c11 -pedantic -O2" 编译（CC 从环境变量获取，默认 clang；Debug 构建使用 -g -O0）
4. 手动安装到 staging 目录（因为 install 命令不存在）
5. 签名 ELF 文件
6. 创建预编译包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 下载 URL SSL 证书验证失败 | HarmonyOS 环境缺少 CA 证书 | 使用 curl --insecure 手动下载 |
| 2 | adjtime 函数不存在 | OpenHarmony 使用 adjtimex 替代 adjtime | 添加 OpenHarmony 兼容性补丁，用 adjtimex 替换 adjtime |
| 3 | install 命令不存在 | toybox 环境缺少 GNU install | 使用 cp + chmod 手动安装 |
| 4 | ELF 未签名无法执行 | 鸿蒙系统要求 ELF 签名 | 使用 ohc-run.py sign-elf 签名 |

## 源码修改

### 补丁 0001-htpdate.c.patch

```diff
+/* On Linux, use adjtimex instead of adjtime (adjtime may be unavailable on some libc) */
+#ifdef __linux__
+#define adjtime(tv, oldtv) adjtimex_compat(tv)
+static inline int adjtimex_compat(const struct timeval *tv) {
+    struct timex txc = {0};
+    txc.modes = ADJ_OFFSET_SINGLESHOT;
+    txc.offset = (long long)tv->tv_sec * 1000000LL + tv->tv_usec;
+    return adjtimex(&txc);
+}
+#endif
```

## 依赖版本

无外部依赖，仅需标准 C 库。

## 验证结果

```bash
$ ~/usr/local/sbin/htpdate -v
htpdate version 1.3.7
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| htpdate-1.3.7-ohos-aarch64.tar.gz | 36KB | 预编译包（主包） |
| htpdate-1.3.7-ohos-aarch64-debug.tar.gz | 16KB | 调试符号包 |

## 注意事项

1. htpdate 可选择编译 HTTPS 支持版本（make https），需要 libssl
2. 补丁使用 `__linux__` 标准宏（编译器预定义）启用 adjtimex 兼容性，无需额外编译参数
3. 运行时需要 root 权限才能调整系统时间

---
**编译结束**: 2026-06-03 15:52
**最终状态**: built
---

**编译结束**: 2026-06-03 15:53
**最终状态**: built
