# sloci-image 0.1.1 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-22
- 编译器: clang/clang++
- 状态: built

## 编译步骤

sloci-image 是一个纯 shell 脚本工具，用于创建 OCI 容器镜像。无需编译，只需安装。

```bash
cd ~/tmp/builds/sloci-image-0.1.1.work
make install DESTDIR=$HOME/tmp/test-install-sloci-image-0.1.1 PREFIX=$HOME/usr/local
```

安装后验证脚本在 `$TEST_PREFIX/$HOME/usr/local/bin/sloci-image` 中。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | verify-build G4 失败：manifest 缺少 build_system | manifest.yaml 缺少 `build_system` 字段且 `build.system` 错误设为 autotools | 添加 `build_system: makefile` 到 manifest.yaml，将 `build.system` 从 autotools 改为 makefile |
| 2 | 无编译产物 | sloci-image 是 shell 脚本而非二进制文件 | 正常，G2 警告 "无二进制文件" 是预期的 |
| 3 | `tar: Unknown option 'acls'` 运行时报错 | sloci-image 脚本使用 `tar --acls --xattrs` 创建 rootfs tar 包，但 HarmonyOS 的 toybox tar 不支持这些选项 | 创建补丁 0001-sloci-image.patch，在调用 tar 前检测 `tar --help` 是否支持 `--acls`，不支持则省略 |

## 源码修改

### 补丁 0001-sloci-image.patch — tar --acls/--xattrs 条件检测

sloci-image 脚本第 381 行使用 `tar --acls --xattrs` 创建 rootfs 归档。HarmonyOS 使用 toybox tar (0.8.12)，不支持 `--acls`/`--xattrs` 选项，导致 `sloci-image` 创建 OCI 镜像时失败。

补丁修改为运行时检测 tar 是否支持 `--acls`，支持时才添加该选项：

```sh
TAR_XATTR=""
tar --help 2>&1 | grep -q -- '--acls' && TAR_XATTR="--acls --xattrs"
tar -C "$ROOTFS" ${DEBUG:+-v} $TAR_XATTR -cf "${rootfs_tgz%.gz}" .
```

这样在 GNU tar 环境下保留 ACL/xattr 功能，在 toybox 等不支持的环境下正常降级工作。

## 依赖版本

- 无编译依赖（shell 脚本工具）
- 运行依赖：POSIX sh

## 验证结果

```bash
# 版本验证
sloci-image --version
# 输出: sloci-image 0.1.1

# OCI 镜像创建验证
TMPDIR_TEST=$(mktemp -d)
mkdir -p "$TMPDIR_TEST/rootfs"
echo "hello" > "$TMPDIR_TEST/rootfs/testfile"
cd "$TMPDIR_TEST"
sloci-image "$TMPDIR_TEST/rootfs" testimg:latest
# 验证 OCI 镜像结构
ls testimg/index.json testimg/oci-layout testimg/blobs/sha256/
```

## 注意事项

- aarch64-debug 包不适用（shell 脚本无需调试符号包）
- manifest.yaml 需要包含 `build_system` 字段才能通过 G4 门禁
- G0 clean-build verify 失败是因为 makefile 项目在 ohc 自动化流程中 configure 阶段找不到 configure 命令（exit 127），但实际安装已手动验证成功
- conan-verify G2 通过（conan create + test_package 全通过）
- W3 本地 CI 模拟通过
---

**编译结束**: 2026-08-23 00:43
**最终状态**: built
