# Ptex

Per-Face Texture Mapping for Production Rendering

## 描述

Ptex 是一种纹理映射系统，专为生产渲染而开发，允许每个面有独立的纹理映射。它由 Walt Disney Animation Studios 开发并开源。

## 主要功能

- Per-face 纹理映射，无需 UV 映射
- 高效的纹理存储和访问
- 支持 mipmap 和过滤
- 支持压缩（使用 libdeflate）

## 库文件

- `libPtex.a` - 静态库
- `libPtex.so` - 共享库

## 工具

- `ptxinfo` - Ptex 文件信息查看工具

## 头文件

- Ptexture.h - 主接口头文件
- PtexCache.h - 缓存管理
- PtexReader.h - 文件读取
- PtexWriter.h - 文件写入
- 其他辅助头文件

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 2.5.2 | built | 2026-06-16 | HarmonyOS 适配版本 |

## 依赖

- libdeflate 1.21+

## 使用示例

```cpp
#include <Ptexture.h>

// 打开 Ptex 文件
Ptex::String error;
PtexPtr<PtexTexture> ptex(PtexTexture::open("texture.ptx", error));

if (ptex) {
    // 获取纹理数据
    int faceId = 0;
    PtexFaceInfo info = ptex->getFaceInfo(faceId);
    // ...
}
```

## 查看文件信息

```bash
ptxinfo -v texture.ptx
```

## 许可证

PTEX Software License (Modified BSD) - 由 Disney Enterprises, Inc. 开发