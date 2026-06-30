# util-linux 2.39 编译笔记

## 编译日期
2026-05-26

## 编译状态
built（手动编译成功）

## 编译目标
只编译libblkid、libuuid、libmount三个库，禁用其他工具。

## 配置参数
```bash
./configure --prefix=$DEFAULT_PREFIX \
  --disable-all-programs \
  --enable-libblkid \
  --enable-libuuid \
  --enable-libmount
```

## 遇到的问题

### 1. config.guess/config.sub 平台识别问题 (E007)
**错误**: `configure: error: cannot guess build type`
**原因**: GNU config.guess 不包含 HarmonyOS/__OHOS__ 检测分支
**解决方案**:
- 使用 `patch-autotools-ohos.pl` 应用补丁
- 手动添加 `linux-ohos*` 到 config.sub 的内核-OS组合验证列表（行1781）

### 2. mktemp临时目录创建问题
**错误**: `config.status: error: could not setup config files machinery`
**原因**: toybox的mktemp不支持相对路径模板 `./confXXXXXX`
**解决方案**:
- 修改configure/config.status脚本，使用绝对路径 `$TMPDIR/confXXXXXX`
- 在非HMDFS目录构建（$HOME/tmp-non-hmdfs）

### 3. versionsort未定义问题
**错误**: `error: use of undeclared identifier 'versionsort'`
**原因**: `versionsort` 是GNU扩展函数，musl libc/鸿蒙未实现
**解决方案**: 将 `versionsort` 替换为标准函数 `alphasort`
**文件**: libmount/src/tab_parse.c

### 4. HMDFS硬链接限制
**错误**: `ln: cannot create hard link`
**影响**: libtool 创建 .libs/libblkid.lax/ 目录时的硬链接操作
**解决方案**: 无需处理，不影响最终产物（动态库/静态库正确生成）

## 修改的文件
1. config/config.guess - HarmonyOS系统识别
2. config/config.sub - ohos-linux三元组 + linux-ohos*内核列表
3. libmount/src/tab_parse.c - versionsort → alphasort

## 安装验证

### 关键产物位置
- **blkid.h**: ~/usr/local/include/blkid/blkid.h ✅
- **blkid.pc**: ~/usr/local/lib/pkgconfig/blkid.pc ✅
- **uuid.h**: ~/usr/local/include/uuid/uuid.h ✅
- **uuid.pc**: ~/usr/local/lib/pkgconfig/uuid.pc ✅
- **mount.pc**: ~/usr/local/lib/pkgconfig/mount.pc ✅

### pkg-config验证
```
blkid版本: 2.39.0
uuid版本: 2.39.0
mount版本: 2.39.0
```

### 库文件
- libblkid.so.1.1.0
- libblkid.a
- libuuid.so.1.3.0
- libuuid.a
- libmount.so.1.1.0
- libmount.a

## 知识提取
- E007（config.guess）已匹配并应用
- versionsort问题：新发现，需创建草稿条目

---
*编译完成时间: 2026-05-26 15:35*
---

**编译结束**: 2026-05-26 15:36
**最终状态**: built
