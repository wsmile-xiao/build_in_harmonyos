# libvo-aacenc

VisualOn AAC 编码器库 — 开源 AAC 音频编码实现。

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件名 | libvo-aacenc |
| 描述 | VisualOn AAC 音频编码库 |
| 许可证 | Apache-2.0 |
| 主页 | https://sourceforge.net/projects/opencore-amr/ |
| 分类 | 音频编解码库 |

## 编译版本

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 0.1.3 | built | 2026-06-03 | 静态库，3 个平台适配补丁 |

## OHOS 平台特性

- 仅编译为静态库（共享库在 OHOS 上不受 linker 支持）
- 需要 clang-wrapper 作为 CC（E064: conftest 执行限制）
- 需要 OHOS-aware config.guess/config.sub（E007）
- 需要修复 configure 中 umask 077（E011）

## 使用方法

```bash
# pkg-config 查询
pkg-config --cflags vo-aacenc    # → -I/storage/Users/currentUser/usr/local/include
pkg-config --libs vo-aacenc      # → -L/storage/Users/currentUser/usr/local/lib -lvo-aacenc

# 链接示例
clang-wrapper -o myapp myapp.c -lvo-aacenc
```

## 依赖

无外部编译依赖。