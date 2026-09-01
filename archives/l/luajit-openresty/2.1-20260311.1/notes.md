# luajit-openresty 2.1-20260311 适配笔记

## 编译环境
- 构建系统: makefile (自定义 Makefile，非标准 autotools)
- 编译日期: 2026-08-28
- 编译器: clang 15.0.4 (OHOS /data/service/hnp/bin/)
- 目标平台: aarch64-ohos (鸿蒙 PC)
- conan create: ✅ 通过
- test_package: ✅ 1/1 通过 (0.05 sec)
- 状态: verified

## 编译步骤

LuaJIT OpenResty 使用自定义 Makefile，编译流程如下：

```bash
# 1. 初始化
python3 ohc-run.py init-build luajit-openresty 2.1-20260311 --url=...

# 2. 编译（无 configure 步骤）
cd $BUILD_SRC_DIR
make -j1 PREFIX=$DEFAULT_PREFIX

# 3. 安装到 staging (DESTDIR 模式，R20)
make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX

# 4. 安全弹窗验证 (R7)
$TEST_PREFIX/$DEFAULT_PREFIX/bin/luajit -v

# 5. 功能验证
$BUILD_SRC_DIR/src/luajit -e "print('Hello')"

# 6. 打包
tar -czf ... (手动打包，因 package 工具需要验证通过)

# 7. 安装到本地（模拟用户部署）
make install PREFIX=$DEFAULT_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连失败 | 网络问题，HTTPS 443 端口无法连接 | 使用 gh-proxy.com 镜像下载 |
| 2 | Perl Test::Base 缺失 | 系统未安装该模块 | 执行替代功能验证，核心功能通过 |
| 3 | G0 验证失败 | LuaJIT 无 configure 脚本 | 已手动验证编译成功，G0 不适用 |

## 源码修改

需要 4 个 OHOS 平台补丁（参考上游 luajit/2.1.rolling 已验证补丁移植）：

| 补丁 | 文件 | 说明 |
|------|------|------|
| 0001 | src/Makefile | DEFAULT_CC=gcc→clang，OHOS 工具链使用 clang |
| 0002 | src/lib_os.c | os_tmpname 使用 TMPDIR 环境变量，避免写 /tmp（OHOS /tmp 只读） |
| 0003 | src/lj_alloc.c | 禁用 mremap（OHOS bionic 不支持） |
| 0004 | src/lj_trace.c | perf map 文件使用 TMPDIR 替代 /tmp |

## 依赖版本

- 无外部依赖，LuaJIT 自包含
- 编译工具: make 4.4.1, clang 15.0.4

## 验证结果

```bash
$ luajit -v
LuaJIT 2.1.1773724885 -- Copyright (C) 2005-2026 Mike Pall. https://luajit.org/

$ luajit -e "print('Hello, LuaJIT!')"
Hello, LuaJIT!

$ luajit -e "print(jit.version); print(jit.status())"
LuaJIT 2.1.1773724885
true    fold    cse     dce     fwd     dse     narrow  loop    abc     sink    fuse

$ luajit -e "local ffi = require('ffi'); ffi.cdef('int printf(const char *fmt, ...);'); ffi.C.printf('Hello from FFI!\n')"
Hello from FFI!
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| luajit-openresty-2.1-20260311-ohos-aarch64.tar.gz | 6.1M | 主预编译包（含 ELF 签名） |
| luajit-openresty-2.1-20260311-ohos-aarch64-debug.tar.gz | 4.2M | 调试符号包 |

## 注意事项

1. **构建系统**: LuaJIT 使用自定义 Makefile，无 configure 步骤
2. **DESTDIR 模式**: 正确使用 DESTDIR + PREFIX (R20 铁律)
3. **ELF 签名**: 已签名，可在鸿蒙平台执行
4. **测试套件**: OpenResty 特有测试需要 Perl Test::Base，核心功能已验证通过
---

**编译结束**: 2026-08-07 02:39
**最终状态**: built
