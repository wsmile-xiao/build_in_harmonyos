# assimp

## 简介

assimp (Open Asset Import Library) 是一个跨平台的 3D 模型导入库，支持导入多种 3D 模型格式。

## OHOS 适配要点

- 使用 CMake 构建系统
- 需要显式指定 zlib 路径（PKG_CONFIG_PATH 或 CMake 变量）
- 建议编译为静态库（`-DBUILD_SHARED_LIBS=OFF`）

## 依赖

- zlib（已预编译）

## 功能验证

```bash
# 检查库文件
ls ~/usr/local/lib/libassimp.a

# 检查头文件
ls ~/usr/local/include/assimp/
```

## 参考

- https://github.com/assimp/assimp