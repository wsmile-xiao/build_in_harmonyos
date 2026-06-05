# mpg123

高性能 MPEG Audio Layer 1/2/3 解码器，经典 MP3 播放器。

## 版本
- 1.33.5 (2026-05-19)

## 用途
- MP3 音频解码播放
- ID3 标签处理
- 音频输出工具

## 可执行文件
- mpg123: MP3 播放器
- mpg123-id3dump: ID3 标签查看
- mpg123-strip: MP3 剥离工具
- out123: 音频输出工具

## 库文件
- libmpg123.a: 解码库（静态）
- libout123.a: 输出库（静态）
- libsyn123.a: 合成库（静态）

## 头文件
- mpg123.h: 解码库接口
- out123.h: 输出库接口
- syn123.h: 合成库接口
- fmt123.h: 格式定义

## 安装
curl install.sh | sh -s -- mpg123 1.33.5

## 验证
mpg123 --version

## 使用示例

### 播放 MP3 文件
```bash
mpg123 music.mp3
```

### 查看 ID3 标签
```bash
mpg123-id3dump music.mp3
```

### 解码为 WAV
```bash
mpg123 -w output.wav music.mp3
```

### 在代码中使用解码库
```c
#include <mpg123.h>

int main() {
    mpg123_init();
    mpg123_handle *mh = mpg123_new(NULL, NULL);
    // ... 解码操作
    mpg123_delete(mh);
    mpg123_exit();
    return 0;
}
```

## 平台支持
- OpenHarmony aarch64

## 构建系统
autotools

## 编译选项
- --enable-static
- --disable-shared
- --disable-modules

## 许可证
LGPL-2.1-or-later