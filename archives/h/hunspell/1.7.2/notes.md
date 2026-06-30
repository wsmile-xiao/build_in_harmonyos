# hunspell 1.7.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: published
- 系统: HarmonyOS (aarch64)

## 编译步骤

### 1. 解压源码
```bash
cd /data/service/hnp/tmp
tar -xzf ~/tmp/hunspell-1.7.2.tar.gz
cd hunspell-1.7.2
```

### 2. 应用补丁
```bash
# 补丁已通过 ohc-run.py refresh-patch 自动生成
# 位于 archives/h/hunspell/1.7.2/patches/ 目录
```

### 3. 配置
```bash
./configure --prefix=/data/service/hnp/usr/local
```

### 4. 编译
```bash
make -j2
```

### 5. 安装
```bash
make install DESTDIR=/data/service/hnp/tmp/test-install-hunspell-1.7.2
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 不包含 HarmonyOS 检测 | 添加 HarmonyOS case 分支，输出 `aarch64-unknown-linux-ohos` 三元组 |
| 2 | config.sub 不支持 ohos 三元组 | config.sub 不认可 `linux-ohos` 作为合法操作系统 | 在 maybe_os 列表、-ohos* 处理、内核-os 白名单三处添加 ohos 支持 |
| 3 | configure 脚本创建临时目录失败 | HMDFS 文件系统上 `umask 077 && mktemp` 创建的目录带 setgid 位（2700权限） | 修改 configure，移除 umask 077，使用 `${TMPDIR:-$HOME/tmp}` 作为临时目录 |
| 4 | 动态链接器无法解析符号链接 | HMDFS 文件系统上符号链接解析异常 | 将 libhunspell-1.7.so.0 符号链接替换为实际库文件副本（cp -a） |

## 源码修改

### 补丁列表
1. **0001-config.guess.patch** - 添加 HarmonyOS 检测支持
   - 在 case 分支中添加 `*:HarmonyOS:*:*` 处理
   - 支持 aarch64、arm、x86_64、i686 架构
   - 输出格式：`{arch}-unknown-linux-ohos`

2. **0002-config.sub.patch** - 添加 ohos 三元组支持
   - maybe_os 列表添加 `linux-ohos*`
   - 添加 `ohos-linux` 到 `-linux-ohos` 的映射
   - 添加 `-ohos*` 到 `-linux-ohos` 的处理
   - 在内核-os 白名单中添加 `linux-ohos*`

3. **0003-configure.patch** - 修复 HMDFS 临时目录问题
   - 移除 `umask 077` 调用
   - 使用 `${TMPDIR:-$HOME/tmp}` 替代当前目录作为临时目录路径
   - 避免创建带 setgid 位的目录

## 依赖版本

无外部依赖

## 验证结果

```bash
# 版本验证
hunspell --version
# 输出: Hunspell 1.7.2

# 功能验证
echo "hello" | hunspell
# 正常输出拼写检查结果

# 库文件验证
ldd /data/service/hnp/usr/local/lib/libhunspell-1.7.so.0
# 所有依赖库正确链接
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/hunspell | 283KB | 主程序 |
| bin/hunzip | 15KB | 解压工具 |
| bin/hzip | 15KB | 压缩工具 |
| lib/libhunspell-1.7.so.0.0.0 | 936KB | 动态库 |
| lib/libhunspell.a | 1.2MB | 静态库 |
| lib/libhunspell.la | 1KB | libtool 归档文件 |
| lib/pkgconfig/hunspell.pc | 305B | pkg-config 文件 |
| include/hunspell/*.hxx | 多个 | C++ 头文件 |

## 注意事项

1. **HMDFS 符号链接问题**：在 HMDFS 文件系统上，动态链接器无法正确解析符号链接。安装后需要将 `libhunspell-1.7.so.0` 符号链接替换为实际库文件副本：
   ```bash
   cd /data/service/hnp/usr/local/lib
   rm libhunspell-1.7.so.0
   cp -a libhunspell-1.7.so.0.0.0 libhunspell-1.7.so.0
   ```

2. **临时目录限制**：HMDFS 文件系统上使用 `umask 077` 创建目录会触发 setgid 位，configure 脚本已修复此问题。

3. **补丁自包含性**：所有补丁文件已生成，可通过 `ohc-run.py finish` 触发 G0 干净构建验证。

## 知识沉淀

本编译过程沉淀了以下知识条目（E007, E072）：
- **E007**: config.guess 需要添加 HarmonyOS case 分支，支持自动识别 HarmonyOS 系统
- **E072**: config.sub 需要在三处添加 ohos 支持，使 `*-linux-ohos` 成为合法的目标三元组
---

**编译结束**: 2026-05-21 20:59
**最终状态**: built
