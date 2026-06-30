# yazi

Yazi 是一个用 Rust 编写的超快终端文件管理器，基于异步 I/O 实现。

## 描述
Yazi 是一个终端文件管理器，具有极快的文件操作速度。基于 tokio 异步运行时，支持并发文件操作、实时预览、自定义快捷键等特性。

## 已编译版本
- 26.5.6 (2026-06-17)

## 依赖
- Rust 1.88.0

## 特性
- 异步 I/O 并发操作
- 文件预览（代码、图片、视频等）
- Vim 风格快捷键
- 插件系统
- 主题自定义

## 补丁
- 0001-Cargo.lock.patch: 移除 jemalloc 相关依赖锁定
- 0002-yazi-fm-Cargo.toml.patch: 移除 jemallocator 依赖声明
- 0003-yazi-fm-src-main.rs.patch: 移除 jemalloc global allocator 声明，改用系统默认分配器

## 使用方法
```bash
# 启动文件管理器
yazi

# 在当前目录打开
ya
```

## 注意事项
- musl 环境不支持 jemalloc，改用系统 allocator
- 需要 ohos-clang wrapper 处理 Rust target 映射
