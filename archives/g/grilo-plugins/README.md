# grilo-plugins

## 简介

Grilo Plugins 是 GNOME Grilo 框架的插件集合，提供多种媒体源访问功能。

Grilo 是一个框架，用于简化应用发现和浏览媒体内容的任务。grilo-plugins 包含各种插件，用于从不同来源访问媒体内容，包括：
- DLNA/UPnP 服务器
- Flickr
- YouTube
- Tracker 本地索引
- Podcasts
- 等等

## 项目信息

- **主页**: https://gnome.pages.gitlab.gnome.org/grilo/
- **许可证**: LGPL-2.1-or-later
- **维护者**: GNOME Project

## 构建特性

- **构建系统**: Meson
- **构建难度**: 中等
- **特殊处理**: 需要
  - 设置 PKG_CONFIG_PATH 包含本地安装路径
  - 大部分插件依赖额外的库（libsoup、lua 等）

## 插件列表

grilo-plugins 包含以下插件：

### 核心插件（已编译）
- **dleyna**: DLNA/UPnP 媒体服务器访问
- **gravatar**: Gravatar 头像服务

### 可选插件（因缺少依赖未编译）
- **lua-factory**: Lua 脚本插件（需要 lua）
- **youtube**: YouTube 视频源（需要 libsoup）
- **flickr**: Flickr 图片源（需要 libsoup）
- **dmap**: DMAP/DAAP 协议（需要 libdmapsharing）
- **tracker/tracker3**: Tracker 本地索引（需要 tracker）
- **podcasts**: Podcast 订阅（需要 totem-plparser）
- **magnatune**: Magnatune 音乐服务（需要 libsoup）
- **metadata-store**: 元数据存储（需要 sqlite3）
- **bookmarks**: 书签管理（需要 libsoup）

## 依赖关系

### 必需依赖
- glib-2.0 >= 2.66
- grilo-0.3 >= 0.3.8
- gio-2.0
- gio-unix-2.0

### 可选依赖
- libsoup-3.0 或 libsoup-2.4（HTTP 客户端）
- lua 5.3 或 5.4（脚本支持）
- libarchive（光学媒体）
- gstreamer-1.0（音频处理）
- avahi-client（本地网络发现）

## 编译状态

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 0.3.16 | built | 2026-06-16 | 部分插件启用 |

## 使用建议

1. 如果只需要 DLNA/UPnP 功能，当前的 dleyna 插件已可用
2. 如果需要更多插件，需要先安装相应依赖（libsoup、lua 等）
3. 每个插件可以独立启用/禁用，通过 Meson 配置选项控制

## 配置示例

```bash
# 最小化编译（仅启用基本插件）
meson setup build --prefix=/usr/local \
  -Denable-lua-factory=no \
  -Denable-youtube=no \
  -Denable-flickr=no \
  -Dhelp=no

# 完整编译（需要安装所有依赖）
meson setup build --prefix=/usr/local
```

## 注意事项

1. **构建系统**: grilo-plugins 使用 Meson，不是 autotools
2. **插件依赖**: 每个插件有独立的依赖需求
3. **PKG_CONFIG_PATH**: 必须正确设置才能找到依赖
4. **无测试**: 项目没有定义测试套件