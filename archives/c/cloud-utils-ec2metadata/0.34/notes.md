# cloud-utils-ec2metadata 0.34 适配笔记

## 编译环境
- 构建系统: makefile（纯脚本安装，无编译步骤）
- 编译日期: 2026-09-08
- 编译器: 无（Shell/Python 脚本工具集，不参与编译）
- 状态: built（conan create + W3 本地 CI 通过，待 CI 复核后 published）

## 源码
- 上游: https://github.com/canonical/cloud-utils（tag 0.34，官方 GitHub 发布）
- 类型: Shell/Python 脚本工具，Makefile 仅安装 bin/ 脚本与 man 页
- SHA-256: 0e2d6bb9c738d7016bb8af6780bef74dee263a02963e9c01a6b8331e7cafdf8d
- 主交付物: ec2metadata（Python3，IMDSv1/v2 元数据查询）；随包安装 growpart、
  cloud-localds、mount-image-callback、resize-part-image、vcs-run、
  write-mime-multipart 及 4 个 man 页

## 适配修改（6 个补丁）

### 1. Makefile — install(1) 长选项兼容
- **问题**: HarmonyOS 的 `install(1)` 不支持 `--mode=0644` 长选项
- **修复**: 改用短选项 `-m 0644`
- **补丁**: 0001-Makefile.patch

### 2. Shebang 修复（5 个脚本）
- **问题**: 脚本硬编码 `#!/bin/bash` 与 `#!/usr/bin/python3`，HarmonyOS 无这些路径
- **修复**: 改为 `#!/usr/bin/env bash` / `#!/usr/bin/env python3`
- **受影响文件**:
  - bin/cloud-localds（#!/bin/bash → env bash）
  - bin/ec2metadata（#!/usr/bin/python3 → env python3）
  - bin/mount-image-callback（#!/bin/bash → env bash）
  - bin/vcs-run（#!/bin/bash → env bash）
  - bin/write-mime-multipart（#!/usr/bin/python3 → env python3）
- **补丁**: 0002-0006

## 构建步骤
1. 下载官方 tag 0.34 tarball（SHA-256 与官方 GitHub 发布 tarball 一致）
2. 应用补丁: `apply_conandata_patches(self)`
3. 安装: `make install BINDIR=$PKG/bin MANDIR=$PKG/share/man/man1 DOCDIR=$PKG/share/doc/cloud-utils`
4. test_package: 本地 mock proxy 路由 IMDSv2 token + meta-data 查询，真实功能验证

## OHOS 专项测试（新增）
- `test_package/test_ohos_ec2metadata.py`：
  - ec2metadata --help（env shebang 解析；上游 usage() 写 stderr 且 exit 1 为设计行为，按文本断言）
  - 本地 socketserver mock（同时扮演正向代理 + IMDS），http_proxy 路由
    169.254.169.254 的 token PUT 与 meta-data GET，断言 instance-id/ami-id 返回 mock 值
  - write-mime-multipart --help 冒烟
- 实测结果: `OHOS TEST PASSED`（rc=0），经 conan create 与 W3 门禁真实消费

## 上游测试说明（双口径台账详见最终回报）
- 上游测试入口: test/ 下 7 个独立测试脚本 + run-all 运行器
  （test-growpart / -fsimage / -fsimage-middle / -lvm / -overprovision /
   -start-matches-size / test-mic）
- 本机/CI 环境缺 fdisk/sgdisk/gdisk/qemu-utils/mkfs.ext4/lvm2 等分区镜像工具，
  上游用例不可实例化（上游 CI 亦对 growpart-lvm SKIP）；tox（flake8/pylint/
  shellcheck）为静态检查非测试用例
- 本包新增 OHOS 专项测试作为当前配置可执行集合（4 项断言，全过）

## Conan 配方
- package_type: application
- settings: os, compiler, build_type, arch
- bindirs: ["bin"]；无外部依赖
- commands.json（软件级）: type=tool

## 知识沉淀
- 既有知识复用: env shebang 修复（E037/E049/E165/E143）、install 参数兼容（E087/E174）
- 新增草稿: DRAFT-cloud-utils-ec2metadata-0.34-imds-mock-proxy-test
  （硬编码 169.254.169.254 端点的脚本工具离线功能测试：本地 http_proxy mock 路由法）
- 候选台账: reports/knowledge-candidate-ledger.md

## 注意事项
- ec2metadata 的 IMDSv2 token 端点写死 169.254.169.254（不受 -u 覆盖），
  离线环境直连为 SYN 黑洞，功能测试必须走本地代理 mock 路由
- 上游 usage() 对 --help 也 exit 1，测试断言以输出文本为准
---

**编译结束**: 2026-09-09 09:12
**最终状态**: built
