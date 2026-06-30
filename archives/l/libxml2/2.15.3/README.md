# libxml2 2.15.3 — OpenHarmony 预编译说明

## 基本信息

- **软件**: libxml2 2.15.3
- **目标平台**: OpenHarmony aarch64 (HongMeng Kernel 1.12.0)
- **构建系统**: meson/ninja (autotools 在 HMDFS 上不可用)
- **编译器**: clang/clang++
- **状态**: built

## 预编译包内容

- `bin/xmllint` — XML 命令行工具 (ELF 已签名)
- `lib/libxml2.so.16.1.3` — 共享库 (ELF 已签名)
- `lib/libxml2.so.16` / `lib/libxml2.so` — 符号链接
- `include/libxml2/libxml/*.h` — 开发头文件

## 补丁说明

1. **0001-config.guess.patch** (+11/-0): 添加 OpenHarmony 系统检测，识别 `aarch64-linux-ohos` 三元组
2. **0002-config.sub.patch** (+11/-3): 在 config.sub 中添加 `linux-ohos*` 操作系统识别规则

## 使用方法

```bash
# 解压预编译包
tar xzf libxml2-2.15.3-ohos-aarch64.tar.gz -C /target/dir

# 设置库路径
export LD_LIBRARY_PATH=/target/dir/lib:$LD_LIBRARY_PATH

# 运行 xmllint
/target/dir/bin/xmllint --version
# 输出: xmllint: using libxml version 21503

# XML 解析示例
/target/dir/bin/xmllint document.xml

# XPath 查询示例
/target/dir/bin/xmllint --xpath "//element/text()" document.xml
```

## 注意事项

- xmllint 和 libxml2.so 已完成 ELF 签名，可直接在 OpenHarmony 上执行
- 本地 ninja install 的未签名二进制无法直接执行（报 "operation not permitted"），必须使用预编译包中的签名版本
- 需通过 LD_LIBRARY_PATH 指向 libxml2.so.16 所在目录，避免与系统旧版 libxml2.so.2 冲突

## 编译知识要点

1. HMDFS 文件系统上 mktemp -d 创建的临时目录权限为 0700 (umask 077)，非 owner 用户无法写入，导致 autotools configure 失败 → 使用 meson 替代
2. libxml2 2.15.x 官方推荐 meson 构建系统，autotools 支持不完整（缺少 config.h.in）
3. meson 预编译包需要修复 shebang 和 PYTHONPATH wrapper 才能在 OpenHarmony 上运行
4. config.sub/config.guess 需要添加 linux-ohos* 三元组支持