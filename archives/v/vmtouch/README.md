# vmtouch

**全称**: vmtouch - the Virtual Memory Toucher
**描述**: Portable file system cache diagnostics and control

## 简介

vmtouch 是一个轻量级的文件系统缓存诊断和控制工具，用于：
- 查看文件或目录在内存中的缓存状态（哪些页面已驻留）
- 将文件页面主动加载到内存中（touch）
- 将文件页面从内存中驱逐出去（evict）
- 锁定文件页面在物理内存中（mlock/mlockall）

## 已编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.3.1 | published | 2026-06-15 |

## 特性

- 单文件 C 程序，无外部依赖
- 支持 POSIX mincore() 系统调用查询缓存状态
- 支持 mlock(2)/mlockall(2) 锁定页面
- 支持递归目录扫描
- 支持 daemon 模式持续锁定

## 鸿蒙平台注意事项

- `vmtouch -t` 在 HMDFS 上有 getcwd 警告（非阻塞）
- `vmtouch -e` 驱逐效果受 HMDFS 文件系统特性影响（页面可能立即重新加载）
