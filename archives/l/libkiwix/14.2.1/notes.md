# libkiwix 14.2.1 编译笔记

## 编译时间
2026-06-08

## 软件信息
- **软件名称**: libkiwix
- **版本**: 14.2.1
- **描述**: Common code base for all Kiwix ports
- **构建系统**: Meson (C++17)
- **仓库**: https://github.com/kiwix/libkiwix

## 依赖分析结果

### 必需依赖
1. **mustache.hpp** (Header-only) - kainjow/Mustache v4.1+ ✅ 已安装
2. **pugixml** - XML 解析库 ✅ 已编译 v1.15
3. **libmicrohttpd** - GNU HTTP 服务器库 ✅ 已编译 v1.0.5
4. **xapian-core** - 搜索引擎库 ✅ 已编译 v1.4.28
5. **libzim** (版本 >=9.4.0, <10.0.0) - ✅ 已编译 v9.7.0（已启用 Xapian）

### 已安装的系统依赖
- ICU 77.1 ✅
- zlib ✅
- libcurl ✅
- pthread ✅

---

## 预编译包修复记录（2026-06-08）

### 发现的问题

1. **绝对路径依赖**
   ```
   NEEDED: /storage/Users/currentUser/usr/local/lib/libpugixml.so
   NEEDED: /storage/Users/currentUser/usr/local/lib/libcurl.so
   ```
   影响：跨机器部署失败

2. **RUNPATH 子目录解析失败**
   ```
   RUNPATH: $ORIGIN:$ORIGIN/external
   ```
   影响：HMDFS 上 $ORIGIN/external 无法正确解析

3. **缺失依赖库**
   - libpugixml.so 未包含在打包产物中

4. **缺失头文件**
   - zim/*.h 未包含在打包产物中（API 编译失败）

### 修复措施

| 问题 | 修复方法 | 时间 |
|------|---------|------|
| 绝对路径依赖 | `patchelf --replace-needed` | 16:28 |
| RUNPATH 子目录 | 扁平化部署（移除 external） | 16:30 |
| 缺失 libpugixml | 添加到打包产物 | 16:30 |
| 缺失 zim 头文件 | 添加 include/zim/*.h | 16:30 |

### 修复后验证

```bash
# 动态库加载
✅ libkiwix.so 加载成功

# 工具运行
✅ kiwix-compile-resources --help 正常
✅ kiwix-compile-i18n --help 正常

# API 功能
✅ Library::create() 成功
✅ Book 操作成功
✅ Library::addBook() 成功
```

### 最终状态

- **状态**: published
- **预编译包**: libkiwix-14.2.1-ohos-aarch64.tar.gz (61MB)
- **RUNPATH**: $ORIGIN（扁平化）
- **依赖**: 全部相对路径，可跨机器部署
---

**编译结束**: 2026-06-08 15:19
**最终状态**: built
