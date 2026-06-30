# lensfun 0.3.4 编译笔记

## 基本信息
- **软件名**: lensfun
- **版本**: 0.3.4
- **构建系统**: CMake
- **编译日期**: 2026-05-21

## 编译过程

### 1. 初始化
- 下载源码：从 GitHub API 获取 tarball（v0.3.4）
- 手动下载并解压到 ~/builds/lensfun-0.3.4.work

### 2. 配置
- 构建系统：CMake
- 配置选项：
  - `-DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX`
  - `-DCMAKE_BUILD_TYPE=Release`
  - `-DBUILD_TESTS=OFF`
  - `-DBUILD_LENSTOOL=OFF`
  - `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（兼容性）

### 3. 编译
- 命令：`make -j2`
- 结果：成功（有警告但无错误）
- 警告：glib 函数调用缺少 sentinel（nullptr）

### 4. 安装
- Staging 安装：`make install DESTDIR=$TEST_PREFIX`
- 结果：成功
- 产物：
  - `/usr/local/lib/liblensfun.so`
  - `/usr/local/include/lensfun/lensfun.h`
  - `/usr/local/share/lensfun/version_1/*.xml`（数据库文件）

### 5. 验证
- 质量门禁：verify-build 运行中

## 依赖
- **必需**：glib2（>= 2.26）
- **可选**：libpng（用于 lenstool，未启用）

## 问题与解决

### 问题1：SSL 证书验证失败
- **原因**：Python urllib 验证 SSL 证书失败
- **解决**：使用 wget --no-check-certificate 手动下载

### 问题2：CMake 兼容性错误
- **错误**：`CMAKE_MINIMUM_REQUIRED` 版本 < 3.5 不兼容
- **解决**：添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`

### 问题3：pkg-config 路径
- **错误**：找不到 glib-2.0.pc
- **解决**：设置 `PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig`

## 编译状态
- **当前状态**: built
- **下一步**: 预编译包制作、本地安装、用户验证
---

**编译结束**: 2026-05-21 19:41
**最终状态**: built
