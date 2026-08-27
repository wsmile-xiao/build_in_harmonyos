# qt-unixodbc 5.15.2 适配笔记

## 编译环境
- 构建系统: custom (手动clang++编译 + vendored unixODBC)
- 编译日期: 2026-08-26
- 编译器: clang/clang++ (from Conan profile)
- 状态: built

## Conan 适配
### 依赖
- qt5-qtbase/5.15.2.2 (conan): Qt5Core headers, libraries, moc tool
- unixODBC 2.3.12 (vendored): built from source within recipe

### 构建流程
1. 下载 qtbase 5.15.2 源码
2. 下载并编译 unixODBC 2.3.12 源码 (vendored, E011 umask fix via Python)
3. 使用 qt5-qtbase conan 包的 moc 工具生成 moc 文件
4. 从 qtbase 源码编译 Qt5Sql 库
5. 从 qtbase 源码编译 ODBC 驱动插件
6. 打包 libqsqlodbc.so, libQt5Sql.so, libodbc.so 等

### 关键决策
- Qt5Sql 从源码编译: qt5-qtbase 使用 -no-feature-sql 禁用了 SQL 模块
- unixODBC vendored: 未发布到 conan 制品仓
- ohenvironment 不需要: OHOS 平台适配已通过补丁内置到 Qt5Core
- 版本化文件: HMDFS 不支持 symlink, libQt5Sql.so 需创建版本副本

## 验证结果
- conan create: 通过 (build + test_package)
- W3 本地 CI: 通过
- 产物: libqsqlodbc.so (162KB), libQt5Sql.so (236KB), libodbc.so 等

**最终状态**: built

## 2026-08-26 CI 修复

### CI 失败原因分析
1. 第一次 CI (2026-08-09 build #16485): 通过
2. 重跑 CI (2026-08-22 build #29445): 源码下载超时 (unixodbc.org 不可达)
3. 重跑 CI (2026-08-22 build #29451): Autotools configure 失败 (OHOS 平台识别问题)

### 修复内容
1. **unixODBC 源码 URL 镜像**: 添加 SourceForge 镜像作为首选, unixodbc.org 作为备选
2. **config.guess/config.sub 更新**: 从 conan 缓存中查找支持 OHOS 的 config.guess, 复制到 unixODBC 源码目录
3. **Shell 检测改进**: 添加 /bin/sh 作为最终回退, 尝试常见路径
