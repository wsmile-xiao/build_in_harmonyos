# LAME

## 简介
High quality MPEG Audio Layer III (MP3) encoder

## OHOS 适配
- autotools：config.sub 不认 aarch64-linux-ohos → configure 覆盖 --host/--build 为 gnu 三元组(原生 build==host)
- uname-shim 修 config.guess(设备 uname=HarmonyOS)
- --disable-frontend 只建 libmp3lame

## 依赖
- 无 conan 依赖（仅系统库）
- 编译工具: clang, autotools

## 参考
- 官网: https://lame.sourceforge.io/
