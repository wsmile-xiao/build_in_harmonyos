# JNA 5.19.0 for HarmonyOS (aarch64)

## 变更
- 首次适配鸿蒙系统
- `libjnidispatch.so` 静态链接 libffi 8.2.0，零外部依赖
- 支持自动从 JAR 解压 native library（需使用已签名的 JDK 副本）

## 验证
- ✅ libc/libm 动态调用
- ✅ Pointer 内存操作
- ✅ ffi_closure 回调机制
- ✅ 自动 JAR 解压加载

## 使用前提
- BiSheng JDK 17.0.13（需拷贝至可写路径并全量自签名）
- `$JAVA_HOME/bin/java -cp jna.jar:your-app.jar YourApp`
