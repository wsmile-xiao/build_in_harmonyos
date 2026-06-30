# NSPR 4.37 编译笔记

**编译开始**: 2026-05-23

## 任务背景
NSPR 是 NSS 的必需依赖，需要先编译 NSPR 才能编译 NSS。

## 编译策略
- NSPR 源码已包含在 nss-3.118.1-with-nspr-4.37.tar.gz 中
- 使用传统的 autoconf 构建系统
- 先安装 NSPR，再编译 NSS

