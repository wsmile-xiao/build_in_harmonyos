# CMakeDeps config 包截胡 find_package：旧式变量桥接

## 机制
上游用旧式 Find 模块（FindGLIB2.cmake 等）时，find_package(GLIB2) 会被 CMakeDeps 生成的 glib2-config.cmake 以 config 模式截胡——config 包只提供 target（glib2::glib2），不设旧式变量，于是上游期待的 GLIB2_INCLUDE_DIR / GLIB2_LIBRARIES 恒空，编译期报 glib.h not found。

## 判据
- 首错：fatal error: glib.h: No such file or directory（且包含/链接路径里完全没有 glib 痕迹）
- 特征：上游存在旧式 Find 模块；conan 依赖侧是 CMakeDeps 生成的 config 包
- 现象：glib2 target 存在但旧式变量为空

## 方案（配方 generate() 显式变量桥接）
1. 聚合依赖 cpp_info 的 includedirs 喂旧式变量 GLIB2_INCLUDE_DIR；
2. 库变量直接给 target 名：GLIB2_LIBRARIES=glib2::glib2（INTERFACE target 链接语义完整）；
3. 静态库依赖给全路径：DB_INCLUDE_DIR / DB_LIBRARY=libdb.a 全路径（OHPCD berkeley-db 包为静态）。

参考实现：libpinyin 2.8.1 配方 generate()（本 PR）。

## 适用边界
- 上游旧式 Find 模块 + 依赖走 CMakeDeps 的组合；上游本身已是 config 模式消费则无此问题。
