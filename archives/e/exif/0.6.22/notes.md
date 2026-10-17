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

---

## 2026-08-30 适配修复记录（PR #7215）

| # | 修复项 | 说明 |
|---|--------|------|
| 1 | test_package/MANIFEST.yml upstream_tests 补全 9→12 | 原声明仅列 9/12 个上游测试脚本（漏 check-add-tags.sh、check-create-tags.sh、check-help.sh），按源码 test/Makefile.am 的 check_SCRIPTS 全量补全；2026-08-30 重新编译实测 make check **12/12 全部 PASS**（0 FAIL / 0 ERROR） |
| 2 | conandata.yml 与制品仓已发布配方对齐 | 制品仓 exif/0.6.22 配方的 conandata.yml 为镜像 fallback 形态（gh-proxy.com 优先 + 官方 GitHub 源），git main 为官方单 URL 形态，两者不一致导致 CI L0j 版本占用检查（R37）拦截本 PR。按 L0j 判定口径（本地配方须与制品仓完全一致）将 conandata.yml 对齐为制品仓形态，sha256 不变 |

> 说明：conandata.yml 对齐是**保持版本号 0.6.22 不递增**的必要条件（L0j：已发布版本配方有差异必须递增版本号；对齐后配方与制品仓一致，无需递增）。官方源仍在 URL 列表内（R39），镜像 fallback 为 CI 构建机制的一部分。

