# JNA 5.19.0 适配笔记

## 编译环境
- 构建系统: 手动构建（Java + Native 混合）
- 编译日期: 2026-04-21
- 编译器: clang 15.0.4（Native 层），bishengjdk 17.0.13（Java 层）
- 状态: success

## 编译步骤
1. 环境验证：java/javac、JNI 头文件、libffi 8.2.0 验证通过
2. 源码获取：git clone
3. Java 层编译：修改 Version.java (TEMPLATE → 5.19.0)，javac 编译 123 个 class，生成 JNI 头文件
4. Native 层编译：
   - `dispatch.c → dispatch.o`
   - `callback.c → callback.o`
   - 静态链接 libffi.a → libjnidispatch.so (186KB)
5. 签名：sign-elf 对 libjnidispatch.so 自签名；拷贝 JDK 并批量签名 65 个 ELF 文件
6. 打包：jna.jar 包含 harmonyos-aarch64/libjnidispatch.so

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | System.load 校验 ELF 签名失败 | BiSheng JDK 要求 .so 与 JVM 同签名体系 | 拷贝 JDK 至可写路径并全量自签名 |
| 2 | JNA 资源路径不匹配 | JNA 检测为 harmonyos-aarch64 | JAR 包含 com/sun/jna/harmonyos-aarch64/libjnidispatch.so |
| 3 | Version.java 版本号错误 | TEMPLATE 未替换 | 修改 VERSION = "5.19.0" |
| 4 | qsort 回调参数类型 | Pointer 比较需用 Pointer.getInt(0) | 使用正确的解引用方式 |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|----------------|
| src/com/sun/jna/Version.java | TEMPLATE → 5.19.0 | 手动修改 |

## 依赖版本
- bishengjdk 17.0.13
- libffi 8.2.0（静态链接）

## 验证结果
- libc 调用 (puts/getpid/abs/sqrt/getenv) ✅
- Pointer 内存操作 (malloc/setInt/getInt/free) ✅
- 动态加载 (libm cos(0.0) = 1.0) ✅
- ffi_closure 回调 (qsort 排序正确) ✅
- 平台检测 (harmonyos-aarch64) ✅

## 交付物
| 文件 | 说明 |
|------|------|
| packaging/jna.jar | 完整 JNA 库（含 harmonyos-aarch64 原生代码） |
| packaging/libjnidispatch.so | 独立原生库（libffi 静态链接，仅依赖 libc.so） |

## 注意事项
- BiSheng JDK 需拷贝至可写路径并全量自签名后才能加载自定义 JNI 库
- Platform.getOSType() 返回 -1（HarmonyOS 不被识别）
- 使用方式：`$JAVA_HOME/bin/java -cp jna.jar:your-app.jar YourApp`
