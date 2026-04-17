# JNA (Java Native Access)

## 简介

JNA 提供在 Java 中直接调用本地共享库（.so/.dll）的能力，无需编写 JNI胶水代码。核心原理是通过 libffi 在运行时动态生成函数调用桥接。

## 鸿蒙适配要点

1. **静态链接 libffi** — `libjnidispatch.so` 内嵌 libffi，部署时无额外依赖（仅 libc.so）
2. **JDK 签名** — BiSheng JDK 的 `System.load` 要求 `.so` 与 JVM 使用同一签名体系，需拷贝 JDK 至可写路径并全量自签名（`binary-sign-tool -selfSign 1`）
3. **版本号** — 编译前需将 `Version.java` 中 `TEMPLATE` 替换为实际版本号
4. **平台识别** — 鸿蒙被 JNA 识别为 `harmonyos`（非 Linux），资源路径为 `com/sun/jna/harmonyos-aarch64/`

## 使用方式

```bash
# 前提：使用已签名的 JDK 副本
JAVA=$HOME/usr/local/bishengjdk17/bin/java
java -cp jna.jar:your-app.jar YourApp
```

JNA 会自动从 JAR 内解压 `libjnidispatch.so` 并加载。

## 验证过的功能

| 功能 | 状态 |
|------|------|
| dlopen/dlsym 动态加载 .so | ✅ |
| FFI 函数调用 (libc/libm) | ✅ |
| Pointer 内存操作 | ✅ |
| ffi_closure 回调 (qsort) | ✅ |
