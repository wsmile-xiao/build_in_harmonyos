# vips 8.14.1 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-20
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. **初始化编译环境**
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build vips 8.14.1 --url="file:///storage/Users/currentUser/builds/vips-8.14.1.tar.gz"
   source $SKILL_ROOT/.build-context-vips-8.14.1
   export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
   cd $BUILD_SRC_DIR
   ```

2. **安装依赖**
   - glib 2.88.0（预编译包）
   ```bash
   curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- glib 2.88.0
   ```

3. **meson 配置**
   ```bash
   meson setup builddir --prefix=$DEFAULT_PREFIX -Dintrospection=false
   ```

4. **编译**
   ```bash
   meson compile -C builddir -j2
   ```

5. **staging 安装（DESTDIR 模式）**
   ```bash
   meson install -C builddir --destdir=$TEST_PREFIX
   ```

6. **本地安装验证**
   ```bash
   meson install -C builddir
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 配置时找不到 glib-2.0 | PKG_CONFIG_PATH 未设置 | 安装 glib 预编译包并设置 PKG_CONFIG_PATH |
| 2 | 安全弹窗验证失败 | ELF 文件未签名 | 使用 binary-sign-tool 签名（在打包阶段自动执行） |

## 源码修改

无补丁，源码无需修改即可编译。

## 依赖版本

| 软件 | 版本 | 说明 |
|------|------|------|
| glib | 2.88.0 | 必需依赖，预编译包 |
| libpng | 1.6.43 | 可选依赖（已安装） |
| libjpeg | 3.1.4.1 | 可选依赖（已安装） |
| cairo | 1.18.2 | 可选依赖（已安装） |
| libheif | 1.18.2 | 可选依赖（已安装） |
| pangocairo | 1.50.14 | 可选依赖（已安装） |

## 验证结果

```bash
# staging 验证
ls -la $TEST_PREFIX$DEFAULT_PREFIX/bin/
ls -la $TEST_PREFIX$DEFAULT_PREFIX/lib/
# 输出：vips, vipsedit, vipsheader, vipsthumbnail 等二进制文件已安装
# 输出：libvips.so.42.16.1, libvips-cpp.so.42.16.1 等库文件已安装

# 本地安装验证
ls -la $DEFAULT_PREFIX/bin/vips*
# 输出：所有二进制文件已安装到 ~/usr/local/bin/
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| vips-8.14.1-ohos-aarch64.tar.gz | TBD | 预编译包（打包阶段生成） |

## 注意事项

1. vips 使用 meson 构建系统，需要设置 `-Dintrospection=false` 参数
2. 必须安装 glib 预编译包并设置 PKG_CONFIG_PATH
3. 编译过程中会产生一些警告，但不影响编译结果
4. ELF 文件签名在打包阶段自动执行

---
**编译结束**: 2026-05-20 12:34
**最终状态**: published
---

**编译结束**: 2026-05-20 12:35
**最终状态**: built
