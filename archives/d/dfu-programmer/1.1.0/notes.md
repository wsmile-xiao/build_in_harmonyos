# dfu-programmer 编译笔记

软件: dfu-programmer  
版本: 1.1.0  
日期: 2026-06-09  
状态: published

## 环境
- OpenHarmony (HongMeng Kernel 1.12.0)
- clang / clang++
- Autotools

## 问题解决
1. HMDFS权限 → TMPDIR=/data/storage/el2/base/cache
2. 无configure → bootstrap.sh
3. libusb → LDFLAGS/CPPFLAGS

## 质量门禁
G1-G4 PASS
