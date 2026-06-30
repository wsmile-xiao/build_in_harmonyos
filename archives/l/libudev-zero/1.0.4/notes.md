# libudev-zero 1.0.4 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-15
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. **初始化编译环境**: `ohc-run.py init-build libudev-zero 1.0.4`
2. **应用补丁**: 应用3个补丁（configure/Makefile/udev_monitor.c）
3. **编译**: `make PREFIX=$DEFAULT_PREFIX -j1`
4. **安装到staging**: `make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX`
5. **本地安装验证**: `make install PREFIX=$DEFAULT_PREFIX`（模拟用户部署）
6. **打包**: `ohc-run.py package libudev-zero 1.0.4`
7. **质量门禁验证**: `ohc-run.py verify-build libudev-zero 1.0.4`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G0 FAIL: PREFIX硬编码为/usr/local | Makefile第4行：`PREFIX = /usr/local`（不接受环境变量） | 修改为`PREFIX ?= /usr/local`（接受环境变量覆盖） |
| 2 | G0 FAIL: configure失败（exit 127） | libudev-zero使用纯Makefile，没有configure脚本，clean-verify尝试运行configure导致失败 | 创建空configure脚本作为workaround，添加0000-configure.patch补丁 |
| 3 | R5 FAIL: ln -fs不支持 | Makefile中使用`ln -fs libudev.so.1 libudev.so`，鸿蒙HMDFS不支持覆盖软链接 | 使用`cp -a libudev.so.1 libudev.so`替换（已在0001-Makefile.patch中） |
| 4 | 头文件冲突 | udev_monitor.c中linux/netlink.h和sys/socket.h都定义sockaddr_storage | 添加OHOS平台检测和宏定义保护（已在0002-udev_monitor.c.patch中） |
| 5 | manifest缺少build_system字段 | 原manifest.yaml中build.system错误设置为autotools | 修正为makefile |

## 源码修改

### 0000-configure.patch
添加空的configure脚本，满足clean-verify要求（workaround）

### 0001-Makefile.patch
- 第4行：`PREFIX ?= /usr/local`（接受环境变量覆盖）
- 第63行：`cp -a libudev.so.1 ${DESTDIR}${LIBDIR}/libudev.so`（替换ln -fs）

### 0002-udev_monitor.c.patch
- 第24-28行：添加OHOS头文件冲突处理
```c
#ifdef __OHOS__
#define sockaddr_storage __linux_sockaddr_storage
#endif
```
- 第31-33行：恢复宏定义
```c
#ifdef __OHOS__
#undef sockaddr_storage
#endif
```

## 依赖版本

libudev-zero无外部依赖（纯C库，只依赖libc和libm）

## 验证结果

```bash
# G0干净构建验证
python3 $SKILL_ROOT/scripts/ohc-run.py clean-verify libudev-zero 1.0.4
✅ G0 干净构建验证通过

# 质量门禁验证
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build libudev-zero 1.0.4
✅ G1: PASS（二进制完整性）
✅ G2: PASS ⚠️（功能可用性，警告：无二进制命令可测试）
✅ G3: PASS（可移植性）
✅ G4: PASS（档案完整性）

# 打包验证
ls -lh packaging/
libudev-zero-1.0.4-ohos-aarch64.tar.gz: 224KB
libudev-zero-1.0.4-ohos-aarch64-debug.tar.gz: 76KB
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libudev-zero-1.0.4-ohos-aarch64.tar.gz | 224KB | 预编译包（Release） |
| libudev-zero-1.0.4-ohos-aarch64-debug.tar.gz | 76KB | Debug符号包 |

## 注意事项

1. **纯Makefile项目处理**: clean-verify默认会尝试运行configure，对于纯Makefile项目需要添加空的configure脚本作为workaround
2. **PREFIX必须接受环境变量**: 使用`PREFIX ?=`语法，否则R20 DESTDIR模式无法正确工作
3. **无二进制命令**: libudev-zero只提供库文件（libudev.so/libudev.a），G2警告"无二进制命令可测试"是正常的
4. **软链接替换**: 鸿蒙HMDFS不支持ln -sf覆盖，必须使用cp -a

---
**编译结束**: 2026-06-15 11:23
**最终状态**: published