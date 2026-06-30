# flactag

## 简介

flactag 是一个用于编辑 FLAC 音频文件元数据标签的命令行工具。它能够自动从 MusicBrainz 数据库查询专辑信息，并将标签写入 FLAC 文件。

## 功能特性

- ✅ MusicBrainz 元数据查询
- ✅ FLAC 文件标签编辑
- ✅ 专辑信息自动匹配
- ✅ 文件重命名功能
- ✅ CD 光盘 ID 计算

## 版本历史

| 版本 | 发布日期 | 状态 | 说明 |
|------|---------|------|------|
| 2.0.4 | 2012-06-19 | built | 最后发布版本，已停止维护 |

## 编译状态

### HarmonyOS 平台适配

- **平台**: aarch64-unknown-linux-ohos
- **编译器**: clang 15.0.4
- **状态**: ✅ 编译成功

### 平台补丁

| 补丁文件 | 说明 |
|---------|------|
| 0001-build-aux-config.guess.patch | HarmonyOS 平台识别支持 |
| 0002-build-aux-config.sub.patch | ohos 三元组支持 |

## 依赖库

### 必需依赖

| 依赖 | 版本 | 来源 |
|------|------|------|
| libdiscid | 0.6.5 | cmd-pkgs 预编译包 |
| neon | 0.35.0 | cmd-pkgs 预编译包 |
| flac | 1.4.3 | cmd-pkgs 预编译包 |
| slang | 2.3.3 | 本地编译 |
| libmusicbrainz5 | 5.1.0 | 本地编译 |
| unac | 1.7.0 | 本地编译 |

## 使用方法

### 安装

预编译包安装（推荐）：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- flactag 2.0.4
```

或从归档编译：
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build flactag 2.0.4
python3 $SKILL_ROOT/scripts/ohc-run.py build flactag 2.0.4
```

### 基本用法

```bash
# 查看版本
flactag --version

# 查看帮助
flactag --help

# 检查 FLAC 文件标签
flactag --check album.flac

# 写入 MusicBrainz 标签
flactag --write album.flac

# 重命名文件
flactag --rename album.flac
```

## 已知问题

1. **运行时库路径**: 需要设置 `LD_LIBRARY_PATH`（预编译包已处理）
2. **软件维护**: 上游已停止维护（2012年最后更新）
3. **光盘读取**: discid 工具的光盘读取功能在 HarmonyOS 未实现

## 许可证

GPL-2.0-or-later

## 参考链接

- 官方网站: https://sourceforge.net/projects/flactag/
- MusicBrainz: https://musicbrainz.org/