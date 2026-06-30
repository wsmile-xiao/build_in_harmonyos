# pdfpc 4.7.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-27
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

1. 初始化编译: `python3 ohc-run.py init-build pdfpc 4.7.0`
2. 设置环境变量:
   ```bash
   export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$HOME/usr/local/share/pkgconfig:$PKG_CONFIG_PATH"
   ```
3. 复制 gee-0.8.vapi 到 vala 默认搜索目录:
   ```bash
   cp ~/usr/local/share/vala/vapi/gee-0.8.vapi ~/usr/local/share/vala-0.56/vapi/
   ```
4. cmake configure:
   ```bash
   cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DMOVIES=OFF -DMDVIEW=OFF -DREST=OFF
   ```
5. 编译: `make -j2`
6. DESTDIR 安装: `make install DESTDIR=$TEST_PREFIX`
7. 本地安装: `make install`
8. 打包: `ohc-run.py package pdfpc 4.7.0` 和 `--debug`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Vala 编译报错 "Package gee-0.8 not found" | libgee 安装后 vapi 文件放在 ~/usr/local/share/vala/vapi/ 而 valac 默认搜索 ~/usr/local/share/vala-0.56/vapi/ | 将 gee-0.8.vapi 复制到 vala-0.56/vapi 目录 |
| 2 | manifest 质量门禁失败: "缺少 build_system" | 模板 manifest.yaml 使用嵌套 build.system 而验证脚本检查顶层 build_system 字段 | 在 manifest.yaml 添加顶层 build_system: cmake 字段 |

## 源码修改

无源码修改，无需补丁文件。编译过程仅需要：
- 将 gee-0.8.vapi 复制到 vala 默认搜索路径（非源码修改）
- 禁用 MOVIES/MDVIEW/REST 功能（通过 cmake 选项，非源码修改）

## 依赖版本

| 依赖 | 版本 |
|------|------|
| glib | 2.84.0 |
| gtk+3 | 3.24.43 |
| cairo | 1.18.4 |
| pango | 1.50.14 |
| json-glib | 1.10.1 |
| poppler-glib | 23.12.0 |
| vala | 0.56.18 |
| libgee | 0.20.6 |

## 验证结果

```bash
# pdfpc 二进制已安装到 ~/usr/local/bin/pdfpc
# 由于是交叉编译的 aarch64 二进制，无法在主机上直接运行 --version
# 但二进制文件确认是 ELF aarch64 格式
file ~/usr/local/bin/pdfpc  → ELF executable (aarch64)
# 编译链接无错误，make -j2 100% 完成
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pdfpc-4.7.0-ohos-aarch64.tar.gz | 36MB | 标准版（strip 后） |
| pdfpc-4.7.0-ohos-aarch64-debug.tar.gz | 51MB | debug 版（含调试符号） |

## 注意事项

- pdfpc --version 无法在交叉编译主机上运行，因为是 aarch64 目标二进制
- MOVIES、MDVIEW、REST 功能已禁用（缺少 GStreamer 等视频相关依赖）
- 编译过程中有大量 G_TYPE_IO_CONDITION 宏重定义警告（来自 glib 头文件冲突），不影响功能
- libgee 的 vapi 文件默认安装路径不在 vala 默认搜索目录，需要手动复制
---

**编译结束**: 2026-05-27 17:39
**最终状态**: built
