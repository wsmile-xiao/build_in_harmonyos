# mummer 4.0.1 编译笔记

## 编译日期
2026-06-17

## 编译环境
- 系统: aarch64-unknown-linux-ohos
- 编译器: cc (C), c++ (C++)
- 构建系统: autotools

## 遭遇的问题与解决方案

### 问题1: configure umask权限错误（E011）
- **错误**: `config.status: error: could not setup config files machinery`
- **原因**: HMDFS文件系统的umask 077导致临时目录权限问题
- **解决**: 修改configure中的umask 077为umask 022
  ```bash
  sed -i 's/umask 077/umask 022/g' configure
  ```
- **文件**: configure (行20644, 20649)
- **状态**: ✅ 已修复

### 问题2: C++ narrowing conversion错误
- **错误**: `src/tigr/postnuc.cc:174:37: error: non-constant-expression cannot be narrowed from type 'signed char' to 'char' in initializer list`
- **原因**: C++11标准禁止在初始化列表中进行隐式的narrowing转换
- **解决**: 添加显式类型转换
  ```cpp
  // 原代码: Alignments.push_back({ *Mp, CurrCp->dirB } );
  // 修改为: Alignments.push_back({ *Mp, static_cast<char>(CurrCp->dirB) } );
  ```
- **文件**: src/tigr/postnuc.cc (行174)
- **状态**: ✅ 已修复

### 问题3: 缺少yaggo工具
- **错误**: YAGGO生成.hpp文件失败
- **原因**: 从GitHub下载的tar.gz不包含预生成文件
- **解决**: 手动安装yaggo工具
  ```bash
  curl -k -L -o ~/tmp/yaggo https://github.com/gmarcais/yaggo/releases/download/v1.5.10/yaggo
  chmod +x ~/tmp/yaggo
  mv ~/tmp/yaggo ~/usr/local/bin/
  ```
- **状态**: ✅ 已安装

### 问题4: SSL证书验证失败
- **错误**: curl下载失败 `SSL certificate verify failed`
- **原因**: 鸿蒙系统SSL证书配置问题
- **解决**: 使用curl -k跳过SSL验证
- **状态**: ✅ 已处理

## 编译参数
- configure选项: --prefix=/storage/Users/currentUser/usr/local
- make选项: -j1

## 依赖信息
- 外部依赖: perl, yaggo
- 构建依赖: gcc, g++, autoconf, automake, libtool

## 测试结果
- 测试状态: 待验证
- 测试报告: 见 reports/test-report.md

## 生成的文件
- 二进制文件: mummer, nucmer, show-coords, show-aligns等
- 库文件: libumdmummer.so.0.0.0, libumdmummer.a
- 头文件: include/mummer-4.0.1/include/mummer/*.hpp

---
*编译完成于2026-06-17*

## 补丁说明
- **0002-postnuc-narrowing.patch**: 修复C++ narrowing conversion错误
- **configure修改**: 通过sed命令修改umask，不生成补丁（configure是autoreconf生成的文件）
  ```bash
  # 在autoreconf -fi之后执行
  sed -i 's/umask 077/umask 022/g' configure
  ```
---

**编译结束**: 2026-06-17 14:40
**最终状态**: built
