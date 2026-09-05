# DRAFT-ccfits-2.7：依赖包自带 .pc 的打包时绝对 prefix 失效 —— 消费方必须用 PkgConfigDeps 重新生成，而不是沿用依赖自带 pc

> Contributor: Awstme | Status: Draft | Updated: 2026-09-05
> Source: ccfits 2.7 适配任务（OHOS aarch64 设备单端验证，feat/ccfits-2.7）
> 关联先例: E468（PkgConfigDeps 不扩展 PKG_CONFIG_PATH）、E348（.pc 多文件转发）

## 背景

CCfits 2.7 上游只用 pkg-config 探测依赖：CMakeLists.txt 走
`PKG_CHECK_MODULES(CFITSIO REQUIRED cfitsio)`。cfitsio/4.6.4 已在
ohpcd registry 发布（静态库，OHOS aarch64 binary 可安装）。

## 错误特征

```text
-- Checking for module 'cfitsio'
--   Found cfitsio, version 4.6.4
[构建进入编译期]
fatal error: 'fitsio.h' file not found
#include "fitsio.h"
         ^~~~~~~~~~
```

注意迷惑点：pkg-config 报告 **Found cfitsio**（configure 成功），错误被推迟到
编译期的 include 阶段，表象是"头文件路径问题"，与 pkg-config 无关的假象。

## 根因

cfitsio Conan 包内的 `lib/pkgconfig/cfitsio.pc` 是上游 CMake `make install`
安装的**依赖包自带 pc**，其头部把路径写死为打包时的绝对目录：

```text
prefix=/storage/<other-machine-cache>/p/b/cfitse<hash>/p
libdir="/storage/.../p/b/cfitse<hash>/p/lib"
includedir="/storage/.../p/b/cfitse<hash>/p/include"
```

该路径在本设备 Conan 缓存中不存在（包目录是内容寻址的，消费端实际目录哈希
不同）。把 `PKG_CONFIG_PATH` 指到包的 `lib/pkgconfig` 后 pkg-config 能"找到"
cfitsio（Name/Version 都正确），但解析出的 `-I`/`-L` 全部指向死路径 → 编译期
`fitsio.h not found`。**即："找到"不等于"路径正确"；依赖包自带的 pc 不可信。**

## 修复（消费方配方）

```python
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import Environment

def generate(self):
    # 1) 用 Conan 重新生成依赖 .pc（prefix 指向本机真实包目录），
    #    而不是沿用依赖包自带的 .pc
    PkgConfigDeps(self).generate()
    # 2) E468 方案：Conan 2.29 不会自动注入，显式把 generators 目录
    #    加入 build 作用域的 PKG_CONFIG_PATH
    env = Environment()
    env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
    env.vars(self, scope="build").save_script("<pkg>_pkg_config_path")
```

要点：`PkgConfigDeps` 生成的 pc 文件落在 generators 目录（配合步骤 2 的
PKG_CONFIG_PATH 前置，保证优先于依赖自带 pc 被解析）；传递依赖（zlib）也会
一并生成，静态链接链（Libs.private）完整。

## 验证/命令

```sh
# 复现：直接用依赖包自带 pc
PKG_CONFIG_PATH="$(conan cache path 'cfitsio/4.6.4:<pkgid>')/lib/pkgconfig" \
  pkg-config --variable=prefix cfitsio    # 输出死路径
# 修复后：PkgConfigDeps 生成的 pc
cat <generators>/cfitsio.pc | grep prefix  # 输出本机真实包目录
```

ccfits 2.7 配方（archives/c/ccfits/2.7/conanfile.py）按此方案后，
conan create（清缓存 G2 干净构建）与 test_package 7 项断言全部通过。

## 与现有条目的关系

- E468 覆盖"生成 .pc 后 PKG_CONFIG_PATH 不注入"这一半；本条补充另一半：
  **为什么必须用 PkgConfigDeps 重新生成**（依赖自带 pc 的 prefix 在打包时
  固化、跨机必死），以及"pkg-config Found ≠ 路径正确"的诊断陷阱。
- 与 E348（多 .pc 体系转发）无冲突，适用面互补。

## 关键词

cfitsio, ccfits, pkg-config, PKG_CONFIG_PATH, PkgConfigDeps, stale prefix,
pc file, fitsio.h not found, PKG_CHECK_MODULES, CMake, OHOS
