# libatomic_ops

## 简介
libatomic_ops 提供原子内存操作接口，支持多种平台的原子操作。

## OHOS 适配
- 支持 autotools 和 CMake 两种构建系统
- autotools 遇到临时文件权限问题时可改用 CMake
- 需要更新 config.guess/config.sub 支持 HarmonyOS

## 依赖
- 无编译依赖

## 功能验证
```bash
ls -la $HOME/usr/local/lib/libatomic_ops*
```

## 参考
- 主页: https://github.com/ivmai/libatomic_ops
