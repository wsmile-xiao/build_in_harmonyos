# libavif 1.0.4 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-05-19}
- 编译器: clang/clang++
- 状态: {published|built|failed}

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}

### 知识匹配（E073 方案）
- **E073**（severity 3）：鸿蒙 HMDFS 文件系统对 .so 符号链接的运行时加载支持不完整
- **解决方案**：采用静态编译（`-DBUILD_SHARED_LIBS=OFF`）
- **关键配置**：
  - `-DPNG_LIBRARY=$DEFAULT_PREFIX/lib/liblibpng16_static.a`（指定静态库绝对路径）
  - `-DJPEG_LIBRARY=$DEFAULT_PREFIX/lib/libjpeg.a`（指定静态库绝对路径）
- **结果**：
  - libavif.a 成功编译（静态库，213KB）
  - avifenc 和 avifdec 成功编译（静态链接，符号都在可执行文件中）
  - 运行时需设置 `LD_LIBRARY_PATH=$DEFAULT_PREFIX/lib`（RPATH 未设置）
  - **E073 问题已避免**：不依赖 libavif.so，所有代码静态链接

### 遗留问题
- 运行时仍需 LD_LIBRARY_PATH 才能加载系统库（libc.so）
- 建议：打包时设置 RPATH 或在安装脚本中处理
---

**编译结束**: 2026-05-19 23:13
**最终状态**: built
