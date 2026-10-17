# libudev-zero 1.0.4 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **初始化编译环境**: `ohc-run.py init-build libudev-zero 1.0.4`
2. **应用补丁**: 应用2个补丁（Makefile/udev_monitor.c）
3. **编译**: `make CC=clang AR=llvm-ar RANLIB=llvm-ranlib libudev.a -j1`
4. **安装到staging**: `make install-static DESTDIR= PREFIX=$DEFAULT_PREFIX`
5. **Conan配方生成**: `ohc-run.py conan-init libudev-zero 1.0.4`
6. **Conan验证**: `ohc-run.py conan-verify libudev-zero 1.0.4`
7. **收尾**: `ohc-run.py finish libudev-zero 1.0.4 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | PREFIX硬编码为/usr/local | Makefile第4行：`PREFIX = /usr/local`（不接受环境变量） | 修改为`PREFIX ?= /usr/local`（接受环境变量覆盖） |
| 2 | R5 FAIL: ln -fs不支持 | Makefile中使用`ln -fs libudev.so.1 libudev.so`，鸿蒙HMDFS不支持覆盖软链接 | 使用`cp -a libudev.so.1 libudev.so`替换（已在0001-Makefile.patch中） |
| 3 | 头文件冲突 | udev_monitor.c中linux/netlink.h和sys/socket.h都定义sockaddr_storage | 添加OHOS平台检测和宏定义保护（已在0002-udev_monitor.c.patch中） |
| 4 | Conan conf API不兼容 | `tools.build:compiler_executables:c`不存在于OHOS Conan | 改用dict方式获取`tools.build:compiler_executables` |
| 5 | basic_layout构建目录不匹配 | Conan创建build-release子目录，make在错误目录运行 | 使用`cwd=self.source_folder`指定工作目录 |

## 源码修改

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

- conan-verify G2: PASS (conan create)
- conan-verify G3: PASS (R26 system library isolation)
- conan-verify G4: PASS (product integrity)
- conan-verify L2/L4/L5: PASS
- W3 local CI simulation: PASS (setup.sh + build_and_test.sh)

## 注意事项

1. **R26系统同名库**: libudev是系统同名库，Conan配方中仅构建静态库(libudev.a)，不输出.so
2. **PREFIX必须接受环境变量**: 使用`PREFIX ?=`语法，否则Conan构建无法正确安装
3. **无二进制命令**: libudev-zero只提供库文件，无可执行命令
4. **软链接替换**: 鸿蒙HMDFS不支持ln -sf覆盖，必须使用cp -a

---
**编译结束**: 2026-07-15
**最终状态**: built
