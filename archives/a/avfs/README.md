# avfs — A Virtual File System

AVFS is a virtual file system library that provides transparent access to archive files (tar, zip, gzip, bzip2, etc.) as if they were directories.

## 功能概述

- 透明访问多种归档格式（tar、zip、gzip、bzip2、rpm、deb、cpio 等），将其视为目录浏览
- 提供虚拟文件系统接口（virt_open、virt_read、virt_stat 等），支持程序化访问
- 支持静态库（libavfs.a）和共享库（libavfs.so）两种链接模式
- 内嵌 zlib 和 bzip2，无需额外依赖即可处理常见压缩格式
- 可通过 extfs 扩展脚本机制支持更多文件系统格式

## 编译版本

| 版本 | 状态 | 日期 | 构建系统 |
|------|------|------|----------|
| 1.2.0 | built | 2026-07-02 | autotools |

## OHOS 适配

- **E001**: OHOS 上无 cc/c++ 软链接，需设置 CC=clang CXX=clang++
- **E007**: config.guess/config.sub 不识别 HarmonyOS，需打补丁添加 OHOS 检测
- **E125**: HMDFS 上 mktemp 不可用，configure 中需替换为 TMPDIR 路径
- **E002**: /tmp 只读，功能测试需使用 $TMPDIR
- test_package 需手动设置 LD_LIBRARY_PATH 解析共享库

## 依赖关系

### 编译依赖
- 无外部 Conan 依赖（zlib 和 bzip2 为内嵌版本）
- 系统库: pthread, dl

### 运行依赖
- pthread
- dl

## 许可证

- LGPL-2.0 (库)
- GPL-2.0 (工具)

## 参考资料

- 官网: https://savannah.nongnu.org/projects/avfs/
- 源码仓库: https://git.savannah.nongnu.org/cgit/avfs.git
