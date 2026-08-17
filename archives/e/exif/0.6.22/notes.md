# exif 0.6.22 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-08-17
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

1. 下载源码包 exif-0.6.22.tar.xz（官方 GitHub release，sha256=0fe268736e0ca...）
2. 修改 config.guess/config.sub 添加 HarmonyOS 平台识别（aarch64-unknown-harmonyos）
3. 修改 configure 临时目录逻辑（umask 002 + ${HOME}/tmp，规避 uid 权限问题）
4. 执行 configure: `./configure --prefix=/storage/Users/currentUser/usr/local`
   （依赖 libexif + popt，通过 pkg-config 检测，PKG_CONFIG_PATH 指向 /usr/local/lib/pkgconfig）
5. 执行 make: `make -j1`
6. 执行 make check: 12 PASS, 0 FAIL
7. 执行 make install DESTDIR 做 staging 隔离验证
8. conan-init 生成配方 → conan-verify 8 门禁全部通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 2020 旧版 config.guess 无 HarmonyOS 分支 | 添加 `HarmonyOS)` case 返回 aarch64-unknown-harmonyos |
| 2 | config.sub 拒绝 harmonyos | kernel-os 组合验证缺失 | 添加 harmonyos-* 系统类型 + kernel 归一化 |
| 3 | configure/config.status 临时目录 Permission denied | umask 077 创建目录属主与进程 uid 不匹配 | 改 umask 002 + 用 ${HOME}/tmp（E002） |
| 4 | conan create 中 pkg-config 检测 libexif/popt 失败 | 配方未用 PkgConfigDeps 生成依赖 .pc | generate() 增加 PkgConfigDeps(self).generate() |
| 5 | test_package 编译 STDOUT_FILENO 未声明 | test.c 缺 <unistd.h> | 添加 #include <unistd.h> |

## 源码修改

- config.guess: 添加 HarmonyOS 平台识别（echo aarch64-unknown-harmonyos）
- config.sub: 添加 harmonyos-* 系统类型和 kernel-os 组合验证
- configure: 临时目录 umask 002 + ${HOME}/tmp/confXXXXXX

## 依赖版本

- libexif/0.6.26.1（conan 制品仓已发布）
- popt/1.16（conan 制品仓已发布）

## 验证结果

```bash
make check  # 12 PASS, 0 FAIL
exif --version  # 0.6.22
conan-verify exif 0.6.22  # G0-G4 + L2/L4/L5 全部通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/exif | 命令行工具（可执行） |
| share/man/man1/exif.1 | man 手册 |
| commands.json | R38 命令行工具声明（tool 类型） |

## 注意事项

- exif 是 CLI 工具（非库），package_type=application，R38 需 commands.json
- 依赖 libexif + popt 均已在制品仓发布，R36 满足
---

**编译结束**: 2026-08-17 04:14
**最终状态**: published
