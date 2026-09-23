# libdicom

## 简介
A C library and set of tools for reading DICOM (Digital Imaging and COmmunications in Medicine) files.

libdicom 由 Imaging Data Commons 项目维护，用于高效读取 DICOM 医学影像文件，提供文件元数据/数据集解析、元素值读取（字符串/整数/小数/二进制/序列）、帧数据读取等 API，附带 dcm-dump 与 dcm-getframe 命令行工具。

## OHOS 适配
- 纯 C 库，上游 Meson 构建系统，零运行时依赖（uthash 为 header-only）
- 构建工具链：clang 15.0.4 / aarch64-linux-ohos（musl/libc++）
- 构建工具 meson/1.11.0 与测试框架 check/0.15.2 均来自 ohpcd 制品仓
- 共享库符号链接别名链（libdicom.so → libdicom.so.1 → libdicom.so.1.3.0）物化为实体拷贝

## 依赖
- uthash/2.3.0（header-only，运行时）

## 参考
- 源码: https://github.com/ImagingDataCommons/libdicom
