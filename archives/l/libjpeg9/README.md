# libjpeg9

经典的 JPEG 图像压缩/解压缩库（IJG 版本，libjpeg9 系列）。

## 版本
- 9f (2024-01-14)

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
- `libjpeg.a` - 静态库

## 头文件
- `jpeglib.h` - JPEG 库主接口
- `jconfig.h` - 配置定义
- `jerror.h` - 错误码定义
- `jmorecfg.h` - 更多配置选项

## 安装
```bash
curl install.sh | sh -s -- libjpeg9 9f
```

## 验证
```bash
cjpeg -h
djpeg -h
```

## 编译选项
- `--enable-static --disable-shared`: 产物与系统 libjpeg 同名，仅构建静态库（R26），同时规避 HMDFS 动态库加载问题

## 补丁说明
1. **0001-config.guess.patch**: HarmonyOS 平台识别支持（2021-06-03 版 config.guess 不识别 HarmonyOS）
2. **0002-config.sub.patch**: 2021-08-14 版 config.sub 不识别 ohos，新增 ohos*/linux-ohos* 三元组
3. **0003-configure.patch**: HMDFS 文件系统 umask 限制修复

## 注意事项
- 仅提供静态库 `libjpeg.a`，可执行文件无外部依赖（仅 libc）
- JPEG_LIB_VERSION = 90（libjpeg9 系列兼容版本号，区别于 libjpeg/10 的 100）
