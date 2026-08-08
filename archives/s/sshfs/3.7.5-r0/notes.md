# sshfs 3.7.5-r0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-07-29
- 编译器: clang/clang++ (LLVM 15.0.4)
- 状态: built

## 依赖
- glib/2.84.0 — GLib 底层核心库
- libfuse/3.18.2 — FUSE 3.x 用户态文件系统库

## 编译步骤
```bash
source .build-context-sshfs-3.7.5-r0
cd $BUILD_SRC_DIR
meson setup builddir
ninja -C builddir
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ohc-run.py 误判构建系统为 autotools | sshfs 使用 Meson 但目录中有 rst2man 脚本 | 手动指定 meson |
| 2 | test_package 空壳测试 (R34) | 生成的 test.c 仅打印 OK 不调 API | 改为尝试执行 sshfs --version；沙箱禁止 exec 时回退 ELF 头校验 |

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (Meson, application type) |
| conandata.yml | 上游源码 URL + SHA256 |
| test_package/ | 消费者验证测试 (执行 sshfs --version) |
| commands.json | 命令行工具声明 (R38) |

## 注意事项
1. sshfs 是 CLI 工具，package_type = application
2. R32 规范: 所有 settings.os 判断使用 in ("Linux", "OHOS") 格式
3. OHOS 无 FUSE 内核模块，运行时实际挂载不可用，仅验证编译和 --version
