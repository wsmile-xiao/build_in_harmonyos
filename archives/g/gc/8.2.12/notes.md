# gc 8.2.12 适配笔记

## 编译环境
- 构建系统: cmake（因autotools configure在HMDFS上权限问题）
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 初始化编译环境：`ohc-run.py init-build gc 8.2.12`
2. 应用config.guess/config.sub补丁：`perl patch-autotools-ohos.pl`
3. 修改源码禁用pthread_cancel功能（见源码修改章节）
4. 使用CMake编译：
   ```bash
   mkdir -p build && cd build
   cmake -DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DCMAKE_BUILD_TYPE=Release ..
   make -j1
   make install DESTDIR=$TEST_PREFIX
   make install
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure失败："source directory already configured" | HMDFS文件系统权限问题，无法创建临时文件 | 改用CMake构建系统 |
| 2 | libatomic_ops依赖缺失 | configure检测到需要libatomic_ops | 使用`--with-libatomic-ops=none`，编译器内置原子操作支持 |
| 3 | pthread_cancel/pthread_setcancelstate未定义 | HarmonyOS不支持pthread_cancel系列函数 | 在gcconfig.h和gc_config_macros.h中添加__OHOS__检测 |

## 源码修改

### 1. config.guess + config.sub
- 应用HarmonyOS平台检测补丁
- 输出三元组：aarch64-unknown-linux-ohos

### 2. include/private/gcconfig.h（禁用CANCEL_SAFE）
```diff
-#if defined(UNIX_LIKE) && defined(THREADS) && !defined(NO_CANCEL_SAFE) \
-    && !defined(HOST_ANDROID)
+#if defined(UNIX_LIKE) && defined(THREADS) && !defined(NO_CANCEL_SAFE) \
+    && !defined(HOST_ANDROID) && !defined(__OHOS__)
  /* ... */
+ /* HarmonyOS lacks pthread_cancel and pthread_setcancelstate.         */
 # define CANCEL_SAFE
 #endif
```

**原因**：CANCEL_SAFE宏会启用DISABLE_CANCEL/RESTORE_CANCEL宏，这些宏调用pthread_setcancelstate。HarmonyOS不支持此函数。

### 3. include/gc_config_macros.h（定义GC_NO_PTHREAD_CANCEL）
```diff
 #   endif
 # endif

+/* HarmonyOS lacks pthread_cancel and pthread_setcancelstate. */
+# if defined(__OHOS__) && !defined(GC_NO_PTHREAD_CANCEL)
+#   define GC_NO_PTHREAD_CANCEL
+# endif
+
 # if (!defined(GC_HAVE_PTHREAD_EXIT) || defined(__native_client__)) \
      && !defined(GC_NO_PTHREAD_CANCEL)
     /* Either there is no pthread_cancel() or no need to intercept it.  */
```

**原因**：GC_NO_PTHREAD_CANCEL宏禁用pthread_cancel相关的wrapper函数。

## 依赖版本

无外部依赖，使用编译器内置原子操作。

## 验证结果

```bash
nm ~/usr/local/lib/libgc.so | grep -E "(pthread_cancel|pthread_setcancel)"
# 输出: 空（无引用）
# ✅ 验证通过
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libgc.so | ~1.5MB | 垃圾回收核心库 |
| libcord.so | ~100KB | 字符串库（可选） |
| include/gc.h | 头文件 | 主接口头文件 |

## 注意事项

1. **必须使用CMake构建**：autotools在HarmonyOS HMDFS上因权限问题无法正常工作。
2. **GC_INIT()显式调用**：configure提示需要显式调用GC_INIT()，应用代码需注意。
3. **线程取消功能缺失**：HarmonyOS不支持pthread_cancel，应用代码不应依赖线程取消机制。
---

**编译结束**: 2026-07-20 11:38
**最终状态**: built
