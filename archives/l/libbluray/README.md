# libbluray

## 简介

libbluray 是一个开源的 Blu-ray 光盘访问库，为媒体播放器（如 VLC、MPlayer）提供 Blu-ray Disc 播放功能。该项目由 VideoLAN 团队开发，是一个从零开始的研究项目，不依赖任何外部规格或代码。

## 主要功能

- **BD-ROM 导航**：提供 Blu-ray 光盘的导航功能，支持播放列表解析和菜单导航
- **BD-J 支持**：支持 Blu-ray Disc Java (BD-J) 交互式内容
- **AACS 解密**：支持 AACS（Advanced Access Content System）内容保护（需配合 libaacs）
- **BD+ 支持**：支持 BD+ 内容保护系统（需配合 libbdplus）
- **跨平台**：支持 GNU/Linux、Windows、macOS 等多个平台
- **轻量级**：依赖极少，易于集成

## OHOS 适配要点

### 关键问题及解决方案

1. **E072: config.sub 平台识别**
   - **问题**：`config.sub` 不识别 `ohos` 操作系统，报错 `unknown operating system 'ohos'`
   - **解决**：修改 `build-aux/config.sub`，在 maybe_os 和 kernel-os 白名单中添加 `ohos` 支持
   - **位置**：第 145 行和第 1828 行

2. **E011: HMDFS umask 权限问题**
   - **问题**：HMDFS 文件系统的 UID 映射导致 `umask 077` 创建的临时目录（0700权限）对进程不可写
   - **解决**：修改 `configure` 脚本中的 `umask 077` 为 `umask 022`（两处）
   - **影响**：仅影响 OHOS 平台，不影响其他平台

3. **缺少 ant 工具**
   - **问题**：BD-J jar 构建需要 Apache Ant，但 OHOS 默认不提供
   - **解决**：使用 `--disable-bdjava-jar` 参数禁用 BD-J jar 文件构建
   - **影响**：禁用后仍可播放普通 Blu-ray 光盘，仅影响 BD-J 交互式功能

### 构建依赖

- **必需依赖**：
  - libxml2：XML 解析
  - freetype2：字体渲染
  - fontconfig：字体配置

- **可选依赖**：
  - libaacs：AACS 解密支持
  - libbdplus：BD+ 支持
  - Apache Ant：BD-J jar 构建（可禁用）

### 推荐编译参数

```bash
./configure --prefix=$DEFAULT_PREFIX --disable-bdjava-jar
make -j1
make install
```

## 功能验证

编译完成后，可使用以下命令验证：

```bash
# 检查库文件
ls -lh ~/usr/local/lib/libbluray*

# 检查头文件
ls -lh ~/usr/local/include/libbluray/

# 查看链接信息
ldd ~/usr/local/lib/libbluray.so
```

## 排除与替代

- `bdjava-jar`：由于缺少 ant 依赖，使用 `--disable-bdjava-jar` 禁用。BD-J 交互式功能不可用，但基本播放功能正常。

## 注意事项

1. **DRM 说明**：libbluray 本身不包含任何 DRM 绕过工具。大多数商业 Blu-ray 光盘受 AACS 或 BD+ 保护，需要额外安装 libaacs 和 libbdplus 库才能播放。

2. **法律合规**：libbluray 符合欧盟互操作性权利法规（CPI 122-6-1、CPI 331-5），不包含任何 DRM 绕过工具，可安全集成到软件中。

3. **临时文件位置**：configure 脚本已修改为使用 `$TMPDIR` 或 `$HOME/tmp` 作为临时目录，避免 OHOS 平台的 `/tmp` 只读问题。

## 参考

- **官方网站**：https://www.videolan.org/developers/libbluray.html
- **源码仓库**：https://code.videolan.org/videolan/libbluray.git
- **API 文档**：https://videolan.videolan.me/libbluray/
- **许可证**：LGPL-2.1-or-later