# gstreamer 1.28.3 编译笔记

## 编译状态
**成功** - 所有191个编译步骤完成

## 编译环境
- 源码路径: `/storage/Users/currentUser/tmp/builds/gstreamer-1.28.3.work`
- 归档路径: `/storage/Users/currentUser/tmp/builds/archives/g/gstreamer/1.28.3/`
- 编译器: clang 15.0.4 (OHOS SDK)
- 构建系统: meson 1.11.1 + ninja 1.13.1
- 目标平台: aarch64-unknown-linux-ohos

## 关键问题及解决方案

### 1. Python脚本执行权限问题
**问题描述**: HMDFS文件系统上的Python脚本（glib-mkenums、glib-genmarshal）无法直接执行，报错：
```
PermissionError: [Errno 13] Permission denied: '/storage/Users/currentUser/usr/local/bin/glib-mkenums'
```

**解决方案**: 
- **方案1（源码修改）**: 修改meson.build，使用python3解释器调用Python脚本
  - 创建patch文件：`0001-fix-python-script-execution.patch`
  - 修改位置：meson.build第715-719行
  
- **方案2（构建配置修改）**: 修改meson pickle文件（meson-private/*.dat）
  - 将cmd_args从直接执行改为：`['python3', 'glib-mkenums', ...]`
  - 修改文件：
    - meson_exe_glib-mkenums_2b1cd9351ad6d6430602f8d5a40d9ea55cfc2e3c.dat
    - meson_exe_glib-mkenums_31630d96e6f09e0c6fffcb6a7a279f4aff76ec27.dat
    - meson_exe_glib-mkenums_f3b6dfe36736f4bd2a3cae337132720e31e3d0b1.dat
    - meson_exe_glib-mkenums_fe65fd97098712dc21c3558659607cb1cecb24e7.dat

**注意**: 方案2是构建产物修改，不记录在patch中，但需在编译报告中说明

### 2. /tmp目录只读问题
**问题描述**: HMDFS上/tmp目录是只读的，无法创建wrapper脚本

**解决方案**: 使用`~/tmp`或`$TMPDIR`替代/tmp

### 3. Bash路径问题
**问题描述**: wrapper脚本的shebang `/bin/bash`不存在

**解决方案**: 使用正确的bash路径 `/data/service/hnp/bin/bash`

## 编译配置参数
```
meson setup build \
  --prefix=/storage/Users/currentUser/usr/local \
  --buildtype=release \
  -Dintrospection=disabled \
  -Dtests=disabled \
  -Dexamples=disabled \
  -Ddoc=disabled \
  -Dnls=disabled \
  -Dptp-helper=disabled \
  -Dbash-completion=disabled \
  -Dlibunwind=disabled \
  -Dlibdw=disabled \
  -Dgst_parse=false
```

## 安装结果
使用DESTDIR模式安装到: `/storage/Users/currentUser/tmp/test-install-gstreamer-1.28.3`

主要产物：
- 库文件：
  - libgstreamer-1.0.so.0.2803.0
  - libgstbase-1.0.so.0.2803.0
  - libgstcontroller-1.0.so.0.2803.0
  - libgstnet-1.0.so.0.2803.0
  - libgstcheck-1.0.so.0.2803.0
  - libgstcoreelements.so
  - libgstcoretracers.so
  
- 可执行文件：
  - gst-inspect-1.0
  - gst-stats-1.0
  - gst-typefind-1.0
  - gst-plugin-scanner
  - gst-completion-helper

## 预编译包
- 文件名: `gstreamer-1.28.3-ohos-aarch64.tar.gz`
- 大小: 15MB
- 路径: `/storage/Users/currentUser/tmp/builds/archives/g/gstreamer/1.28.3/packaging/`

## ELF签名
尝试使用`binary-sign-tool`签名，但工具报错"is not trust command"。这可能需要特殊的权限或信任列表配置。

## 编译日志
- configure.log: meson配置日志
- build.log: ninja编译日志（191个步骤全部成功）
- install.log: meson安装日志

## 补丁文件
- `0001-fix-python-script-execution.patch`: 修复Python脚本执行权限问题

## 后续建议
1. 在编译其他使用glib-mkenums等工具的软件时，需注意同样的权限问题
2. 可考虑在glib编译时创建wrapper脚本作为通用解决方案
3. ELF签名需要进一步调查工具的使用方法和权限要求

---
编译时间: 2026-05-21 18:14-18:15
编译人员: AI编译助手
---

**编译结束**: 2026-08-06 17:19
**最终状态**: built
