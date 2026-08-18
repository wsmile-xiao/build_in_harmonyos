# 适配笔记 — xclip 0.13.1

- 软件名: xclip
- 版本: 0.13.1（上游 tag 0.13 + 适配修复后缀，R37）
- 构建系统: autotools
- 编译日期: 2026-08-15
- 状态: built（PR 阶段尚未 upload，合并后由 release 流水线发布）

## 编译步骤

```bash
# 1. 生成 configure（codeload 源码包不含 configure；configure.ac 为纯 autoconf 项目，
#    直接 autoconf 生成即可，无需 autoreconf -i / aclocal / automake）
autoconf
# 2. E011 修复：HMDFS 上 config.status 临时目录因 umask 077 不可写
sed -i 's/umask 077/umask 022/g' configure
# 3. configure（X11 为 conan 依赖 libx11，路径由 conan 解析；--prefix=/ + DESTDIR 安装）
./configure --prefix=/ \
  --x-includes=$CONAN_LIBX11_ROOT/include --x-libraries=$CONAN_LIBX11_ROOT/lib
# 4. 构建 + staging 安装
make -j1 && make install DESTDIR=$TEST_PREFIX
```

## 补丁

- `0001-xclip.c.patch`: xclip.c 添加 `#include <X11/Xresource.h>`（新版 libX11 6.4.0 将 Xrm 类型移入独立头文件）

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| libx11 | 6.4.0 | conan 依赖（制品仓，含 XCB 传输层） |
| libiconv | 1.17 | conan 依赖（制品仓） |
| xorgproto | 2025.1 | conan 传递依赖（X11 协议头，X11/X.h） |
| libxcb | 1.16 | conan 传递依赖（libX11 运行时传输层） |

> 依赖均为 conan 依赖（从制品仓拉取），CI worker 无需本机预编译 X11 路径（R36 依赖必须发布后可拉取）。

## 验证结果

```bash
xclip -version            # → xclip version 0.13（无需 X server）
ohc-run.py conan-verify xclip 0.13.1   # G0-G4 + L2/L4/L5 全部 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（application 类型，R38） |
| conandata.yml | 源码 + 补丁声明 |
| test_package/ | R34 实质测试（执行 xclip -version） |
| packaging/ | release + debug tar.gz |
| commands.json | 命令行工具声明（R38，软件级） |

## 注意事项

1. **源码 URL**: 上游 savannah 源已 404，改用 GitHub 官方 codeload（R39 官方源）。
   codeload URL 无 `.tar.gz` 扩展名，`get()` 需显式 `filename="xclip-0.13.tar.gz"`。
2. **运行时依赖 libxcb.so.1**: libX11 6.4.0 基于 XCB 传输层，目标系统需提供 libxcb。
3. **Xmu/Xt stub**: configure.ac 检测 `X11/Xmu/Atoms.h`、`X11/Intrinsic.h` 与
   `XmuClientWindow`，但 xclip 实际未直接调用，用最小 stub 满足检测。
4. **版本策略 (R37)**: 0.13 已由 PR1470 合并 main（status=built，从未 upload）。
   本 0.13.1 为适配修复版本，合并后将由 release 流水线发布到制品仓。
---

**编译结束**: 2026-08-16 11:30
**最终状态**: built
