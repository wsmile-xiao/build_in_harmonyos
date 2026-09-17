# libjpeg6b

IJG jpeg-6b 参考实现的 JPEG 图像编解码库（Debian 维护的 autotools 谱系）。

## 版本
- 6b2 (2013-12-25)：jpeg-6b + CVE-2013-6629/6630 信息泄露修复，构建系统换为 autoconf/libtool

## 用途
- JPEG 图像压缩/解压缩（baseline + progressive）
- 图像处理工具
- 为仍依赖 classic JPEG ABI (JPEG_LIB_VERSION=62) 的老软件提供运行库

## 可执行文件
- **cjpeg**: JPEG 编码器（PPM/BMP/TGA → JPEG）
- **djpeg**: JPEG 解码器（JPEG → PPM/BMP/GIF/TGA）
- **jpegtran**: JPEG 无损转换（旋转、镜像、渐进优化）
- **rdjpgcom**: 读取 JPEG 注释
- **wrjpgcom**: 写入 JPEG 注释

## 库文件
- `libjpeg.a` - 静态库（默认仅静态，见下）

## 头文件
- `jpeglib.h` - JPEG 库主接口
- `jconfig.h` - 配置定义
- `jerror.h` - 错误码定义
- `jmorecfg.h` - 更多配置选项

## 安装
```bash
curl install.sh | sh -s -- libjpeg6b 6b2
```

## 验证
```bash
cjpeg -h
djpeg -h
```

## 编译选项
- `--enable-static --disable-shared`: SONAME `libjpeg.so.62` 与 libjpeg-turbo 的 classic ABI 冲突（R26），仅构建静态库

## 补丁说明
1. **0001-config.guess.patch**: HarmonyOS 平台识别（2009-11-20 版 config.guess 无 HarmonyOS 分支）
2. **0002-config.sub.patch**: aarch64 CPU 与 linux-ohos 三元组识别（2009-11-20 版 config.sub 均不认识）
3. **0003-configure-umask.patch**: HMDFS 文件系统 umask 限制修复

## 注意事项
- 头文件与 `libjpeg` 包（IJG 10）同名，消费方二选一，不可同时链接
- `jmorecfg.h` 中 `typedef int boolean`，消费方不得再 include `stdbool.h`
- jpeg-6b API 无 `jpeg_mem_src`/`jpeg_mem_dest`（jpeg-8 才有），仅 stdio 流接口
- 无 SIMD/asm，可执行文件无外部依赖（仅 libc）
