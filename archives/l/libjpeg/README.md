# libjpeg

经典的 JPEG 图像压缩/解压缩库（IJG 版本）。

## 版本
- 10 (2026-01-01)

## 用途
- JPEG 图像压缩/解压缩
- 图像处理工具
- Web 应用图像处理

## 可执行文件
- **cjpeg**: JPEG 编码器（PPM/BMP → JPEG）
- **djpeg**: JPEG 解码器（JPEG → PPM/BMP）
- **jpegtran**: JPEG 无损转换（旋转、镜像）
- **rdjpgcom**: 读取 JPEG 注释
- **wrjpgcom**: 写入 JPEG 注释

## 库文件
- `libjpeg.a` (305KB) - 静态库

## 头文件
- `jpeglib.h` - JPEG 库主接口
- `jconfig.h` - 配置定义
- `jerror.h` - 错误码定义
- `jmorecfg.h` - 更多配置选项

## 安装
```bash
curl install.sh | sh -s -- libjpeg 10
```

## 验证
```bash
cjpeg -h
djpeg -h
```

## 编译选项
- `--enable-static --disable-shared`: 与系统同名库，仅构建静态库（R26），同时规避 HMDFS 动态库加载问题

## 补丁说明
1. **0001-config.guess.patch**: HarmonyOS 平台识别支持（config.sub 已内置 linux-ohos，无需补丁）
2. **0002-configure.patch**: HMDFS 文件系统 umask 限制修复

## 注意事项
- 仅提供静态库 `libjpeg.a`，可执行文件无外部依赖（仅 libc）