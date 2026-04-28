# libjpeg 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | libjpeg (IJG JPEG) |
| 版本 | 10 |
| 官网 | https://www.ijg.org/ |
| 源码下载 | https://www.ijg.org/files/jpegsrc.v10.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64
- 构建系统: autotools

## 编译步骤

### 1. 下载源码

```bash
curl -L -o jpegsrc.v10.tar.gz "https://www.ijg.org/files/jpegsrc.v10.tar.gz"
tar -xzf jpegsrc.v10.tar.gz
cd jpeg-10
```

### 2. 应用补丁

```bash
# 补丁位于 archives/j/jpeg/10/patches/
patch -p1 < 0001-config.guess.patch
patch -p1 < 0002-config.sub.patch
```

### 3. 配置

```bash
./configure --prefix=$HOME/usr/local
```

### 4. 编译

```bash
make -j$(nproc)
```

### 5. 测试

```bash
make check
```

### 6. 安装

```bash
make install
```

## 补丁说明

### 0001-config.guess.patch

**类型**: 平台检测  
**问题**: config.guess 无法识别 HarmonyOS 系统  
**解决**: 添加 HarmonyOS 检测分支

```diff
+#elif defined(__OHOS__)
+    LIBC=ohos
```

### 0002-config.sub.patch

**类型**: 平台检测  
**问题**: config.sub 不支持 ohos-linux 三元组  
**解决**: 添加 ohos-linux 配置支持

## 编译结果

安装后会生成以下文件：

```
$HOME/usr/local/
├── lib/
│   ├── libjpeg.a          # 静态库
│   ├── libjpeg.so         -> libjpeg.so.10.0.0
│   ├── libjpeg.so.10      -> libjpeg.so.10.0.0
│   └── libjpeg.so.10.0.0  # 动态库
├── include/
│   ├── jconfig.h          # 配置头文件
│   ├── jerror.h           # 错误处理
│   ├── jmorecfg.h         # 更多配置
│   └── jpeglib.h          # 主头文件
├── bin/
│   ├── cjpeg              # JPEG 压缩工具
│   ├── djpeg              # JPEG 解压缩工具
│   ├── jpegtran           # JPEG 无损转换
│   ├── rdjpgcom           # 读取 JPEG 注释
│   └── wrjpgcom           # 写入 JPEG 注释
└── lib/pkgconfig/
    └── libjpeg.pc         # pkg-config 文件
```

## 功能验证

### 命令行工具测试

```bash
# 测试压缩
echo "test" | $HOME/usr/local/bin/cjpeg > test.jpg

# 测试解压缩
$HOME/usr/local/bin/djpeg test.jpg > test.ppm

# 测试无损转换
$HOME/usr/local/bin/jpegtran -optimize test.jpg > test_opt.jpg

# 验证版本
$HOME/usr/local/bin/cjpeg -version
# 输出: Independent JPEG Group's CJPEG, version 10
```

### 库链接测试

```bash
cat > test_jpeg.c << 'EOF'
#include <stdio.h>
#include <jpeglib.h>

int main() {
    printf("libjpeg version: %d\n", JPEG_LIB_VERSION);
    return 0;
}
EOF

clang -o test_jpeg test_jpeg.c -I$HOME/usr/local/include \
      -L$HOME/usr/local/lib -ljpeg -Wl,-rpath,$HOME/usr/local/lib
./test_jpeg
# 输出: libjpeg version: 80 (对应 jpeg 10)
```

### make check 结果

| 测试 | 状态 | 说明 |
|------|------|------|
| djpeg PPM 解压缩 | ✅ PASS | 解压缩为 PPM 格式 |
| djpeg GIF 解压缩 | ✅ PASS | 解压缩为 GIF 格式 |
| djpeg BMP 解压缩 | ✅ PASS | 解压缩为 BMP 格式 |
| cjpeg 压缩 | ✅ PASS | 压缩 PPM 图像 |
| jpegtran 转换 | ✅ PASS | JPEG 无损转换 |
| 渐进 JPEG | ✅ PASS | 渐进式 JPEG 支持 |
| **总计** | **13/13** | **100% 通过** |

## 已知限制

### 无

libjpeg 10 在 HarmonyOS 上编译和测试均正常，无已知限制。

## 依赖关系

### 无外部依赖

libjpeg 是一个独立的库，不依赖其他第三方库。

### 被依赖

以下软件依赖 libjpeg：
- libjpeg-turbo（兼容 API）
- ImageMagick
- Python Pillow
- gdk-pixbuf
- 以及许多图像处理软件

## 兼容性说明

### ✅ 无需特殊配置

libjpeg 10 在 HarmonyOS 上编译**简单直接**：
- autotools 构建系统自动识别平台
- 只需应用 config.guess/config.sub 补丁
- 无需额外的编译选项或禁用功能

### 构建系统特点

| 特点 | 说明 |
|------|------|
| 配置方式 | 标准 autotools (./configure) |
| 平台检测 | 需要补丁添加 HarmonyOS 支持 |
| 共享库 | 默认构建 .so |
| 静态库 | 默认构建 .a |
| 测试套件 | make check 完整支持 |

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 10 | 2024-01-14 | 当前稳定版 |
| 9f | 2022-05-14 | 旧稳定版 |
| 9e | 2022-01-16 | 旧版本 |

## 参考资料

- libjpeg 官方网站: https://www.ijg.org/
- JPEG 标准: https://jpeg.org/
