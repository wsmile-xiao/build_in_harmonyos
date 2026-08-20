# mpg123 1.33.5 编译笔记

## 编译日期
2026-08-07

## 构建系统
autotools

## 编译选项
```bash
./configure --prefix=$DEFAULT_PREFIX \
    --enable-static \
    --disable-shared \
    --disable-modules
```

## 遇到的问题

### 1. HMDFS umask 默认 077
configure 中 umask 077 导致创建的文件权限不足，修改为 022。

### 2. config.sub ohos 格式错误
手动修复 config.sub 第156-161行的 case 语句格式。

### 3. HMDFS 管道操作限制
`sort | uniq` 管道操作返回 Permission denied，导致 libtool 符号导出失败。
解决方案：使用静态库模式 `--disable-shared --disable-modules`。

### 4. libtool 静态库嵌套合并失败
libmpg123.a 未正确合并 libcompat.a、libmodule.a 等嵌套库。
解决方案：手动解压并合并对象文件。

## 功能验证
- mpg123 --version: ✅
- 解码库 API: ✅
- 支持采样率: 8000/11025/12000/16000/22050 Hz 等

## 产物
- mpg123, mpg123-id3dump, mpg123-strip, out123
- libmpg123.a, libout123.a, libsyn123.a
---

**编译结束**: 2026-08-07 00:54
**最终状态**: built
# mpg123 1.33.5 - Conan recipe for HarmonyOS PC (aarch64)

<!-- trigger -->
