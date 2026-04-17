# JNA 5.19.0 Build Progress

## 构建环境
- OS: HarmonyOS (HongMeng Kernel 1.12.0, aarch64, GNU/Linux)
- JDK: BiSheng JDK 17.0.13
- Compiler: clang 15.0.4 (ohos)
- libffi: 8.2.0 (已适配鸿蒙，静态链接)

## 步骤记录

### Step 1: 环境验证 ✅
- java/javac 可用
- JNI 头文件完整 (jni.h + jni_md.h)
- libffi 验证通过 (ffi_call(add, 3, 5) = 8)
- dlopen/dlsym 验证通过
- pthread 可用

### Step 2: 源码获取 ✅
- git clone --depth 1 https://github.com/java-native-access/jna

### Step 3: Java 层编译 ✅
- 修改 Version.java: TEMPLATE → 5.19.0
- javac 编译全部 Java 源码 (123 个 class)
- -h 参数生成 JNI 头文件

### Step 4: Native 层编译 ✅
- dispatch.c → dispatch.o (无错误)
- callback.c → callback.o (无错误)
- 静态链接 libffi.a → libjnidispatch.so (186KB)

### Step 5: 签名 ✅
- sign-elf 对 libjnidispatch.so 自签名
- JDK 全量拷贝至 ~/usr/local/bishengjdk17
- 批量签名 JDK 65 个 ELF 文件

### Step 6: 打包 ✅
- jna.jar 包含 harmonyos-aarch64/libjnidispatch.so
- 纯 JAR 方式加载成功（无需外部 .so）

### Step 7: 验证测试 ✅
- libc 调用: puts/getpid/abs/sqrt/getenv ✅
- Pointer 内存: malloc/setInt/getInt/free ✅
- 动态加载: libm cos(0.0) = 1.0 ✅
- ffi_closure 回调: qsort 排序正确 ✅

## 关键发现
1. BiSheng JDK 的 System.load 校验 ELF 签名，要求 .so 与 JVM 同签名体系
2. 必须拷贝 JDK 并全量自签名后才能加载自定义 JNI 库
3. JNA 在鸿蒙上的 RESOURCE_PREFIX 是 harmonyos-aarch64
4. 回调中 qsort 比较函数参数是 void* 指针，需用 Pointer.getInt(0) 解引用
