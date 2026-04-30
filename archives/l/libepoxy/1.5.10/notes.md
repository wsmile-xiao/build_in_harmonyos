# libepoxy 1.5.10 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-04-30
- 编译器: clang/clang++
- 状态: published

## 编译步骤

### 1. 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build libepoxy 1.5.10 --url=https://github.com/anholt/libepoxy/archive/refs/tags/1.5.10.tar.gz
```

### 2. Meson 配置
由于 OpenHarmony 上没有 OpenGL/EGL 库，需要禁用这些功能：
```bash
CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ \
AR=/data/service/hnp/bin/llvm-ar NM=/data/service/hnp/bin/llvm-nm \
STRIP=/data/service/hnp/bin/llvm-strip \
meson setup builddir --prefix=$DEFAULT_PREFIX \
  -Dglx=no -Degl=no -Dx11=false -Dtests=false
```

### 3. 修复脚本执行问题
HMDFS 文件系统不支持直接执行 Python 脚本，需要修改 build.ninja：
```bash
sed -i 's|COMMAND = <src>/src/gen_dispatch.py|COMMAND = python3 <src>/src/gen_dispatch.py|g' builddir/build.ninja
```

### 4. 编译
```bash
ninja -C builddir
```

### 5. 安装
```bash
meson install -C builddir --destdir=$TEST_PREFIX
```

### 6. 创建符号链接
```bash
cd $TEST_PREFIX/$DEFAULT_PREFIX/lib
rm -f libepoxy.so.0 libepoxy.so
ln -s libepoxy.so.0.0.0 libepoxy.so.0
ln -s libepoxy.so.0.0.0 libepoxy.so
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 找不到 clang | CC 环境变量未正确传递 | 手动指定 CC/CXX/AR 等环境变量 |
| 2 | gen_dispatch.py Permission denied | HMDFS 不支持脚本直接执行 | 修改 build.ninja 使用 python3 执行 |
| 3 | 缺少 OpenGL/EGL 库 | OpenHarmony 无桌面 GL 库 | 禁用 GLX/EGL/X11 选项 |
| 4 | ln -sf 不生效 | HMDFS 软链接覆盖限制 | 使用 rm -f && ln -s 模式 |

## 源码修改

无源码补丁。所有修改都是构建配置级别的（build.ninja）。

## 依赖版本

- meson: 1.11.1
- ninja: 1.13.0
- clang: 15.0.4

## 验证结果

```bash
pkg-config --modversion epoxy
# Output: 1.5.10

ls -la ~/usr/local/lib/libepoxy*
# libepoxy.so -> libepoxy.so.0.0.0
# libepoxy.so.0 -> libepoxy.so.0.0.0
# libepoxy.so.0.0.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libepoxy-1.5.10-ohos-aarch64.tar.gz | 2.6MB | 预编译包（含库、头文件、pkg-config） |
| libepoxy-1.5.10-ohos-aarch64-debug.tar.gz | 185KB | 调试符号包 |
| install.sh | 564B | 安装脚本 |

## 注意事项

1. 此版本禁用了 GLX/EGL/X11 支持，仅提供基础 GL 函数指针管理功能
2. 运行时需要 OpenGL 实现库（用户需自行配置）
3. HMDFS 上符号链接需要特殊处理（rm -f && ln -s）

---

**编译结束**: 2026-04-30 01:43
**最终状态**: published