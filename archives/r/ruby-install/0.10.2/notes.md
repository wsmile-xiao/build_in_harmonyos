# ruby-install 0.10.2 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-29
- 编译器: N/A（纯 shell 脚本项目）
- 状态: published

## 编译步骤

1. 下载源码：从 GitHub releases 下载 ruby-install-0.10.2.tar.gz
   - GitHub 直连不可达，使用 ghfast.top 镜像
   - sha256: 65836158b8026992b2e96ed344f3d888112b2b105d0166ecb08ba3b4a0d91bf6
2. 解压源码：tar -xzf ruby-install-0.10.2.tar.gz --strip-components=1
3. 安装到 staging 目录：make install PREFIX=/storage/Users/currentUser/usr/local DESTDIR=$TEST_PREFIX

注：此项目为纯 shell 脚本，无需编译步骤，直接安装即可。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | 系统 CA 证书问题 | 使用 ghfast.top 镜像 + conan E017 镜像注入 |
| 2 | make install SHELL=/usr/bin/env bash 失败 | OHOS 无 /usr/bin/env，bash 在 /data/service/hnp/bin/bash | conanfile.py 中 override SHELL=os.environ.get("SHELL", "/data/service/hnp/bin/bash") |
| 3 | conanfile.py 缺少 export_sources() 和 apply_conandata_patches() | G1 门禁要求 | 添加这两个方法（即使无补丁也需要声明） |

## 源码修改

无补丁，无需修改源码。

## Conan 配方

- package_type: application（命令行工具，非库）
- settings: os, arch（纯 shell 脚本，不需要 compiler/build_type）
- build(): 空操作（无编译）
- package(): make install with SHELL override + PREFIX= + DESTDIR
- package_info(): bindirs=["bin"], resdirs=["share"], libs=[]（无可执行库）
- test_package: 运行 ruby-install --version 验证安装

## 依赖版本

- bash >= 3.x (OHOS: /data/service/hnp/bin/bash)
- wget 或 curl（运行时使用，非构建依赖）
- grep, tar, bzip2, xz, patch（运行时使用）

## 验证结果

conan-verify 全部通过：
- G1: 配方完整性 PASS
- G2: conan create 成功 PASS
- G3: 系统同名库隔离 PASS
- G4: 产物完整性 PASS
- L2/L4/L5: smoke test/安全扫描/基线对比 PASS（跳过，纯脚本无 ELF 产物）

## 注意事项

1. ruby-install 是一个 shell 脚本工具，用于安装各种 Ruby 实现（Ruby, JRuby, TruffleRuby, mruby）
2. 此工具本身不需要编译，只需要简单的 make install
3. Makefile 的 SHELL=/usr/bin/env bash 在 OHOS 上不可用，需要 override
4. commands.json 已创建（R38，命令行工具声明）
---

**编译结束**: 2026-08-29 00:30
**最终状态**: published
