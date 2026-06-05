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
- `--disable-shared`: 使用静态链接模式，避免 HMDFS 动态库加载问题

## 补丁说明
1. **0001-config.guess.patch**: HarmonyOS 平台识别支持
2. **0002-config.sub.patch**: linux-ohos 平台三元组支持
3. **0003-umask.patch**: HMDFS 文件系统 umask 限制修复

## 注意事项
- 使用静态链接模式，避免 HMDFS 动态库加载问题
- 可执行文件均为静态链接，无外部依赖