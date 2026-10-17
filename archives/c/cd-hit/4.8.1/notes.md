# cd-hit 4.8.1 适配笔记

## 编译环境
- 构建系统: makefile（纯 make，无 configure 脚本）
- 编译日期: 2026-09-05
- 编译器: clang/clang++ (OHOS 工具链 clang 15.0.4，-fopenmp 可用)
- 状态: built

## 编译步骤
1. 源码: 官方 tag https://github.com/weizhongli/cdhit/archive/refs/tags/V4.8.1.tar.gz
   （SHA-256 f8bc3cdd… 经 gh-proxy 与 codeload 双路交叉验证；init-build 阶段 github.com 直连超时，
   经 gh-proxy 镜像完成本地拉取）
2. 直接 `make CC=clang++ CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib -j2`：
   Makefile 硬编码 `CC = g++`，命令行覆盖为 OHOS clang 工具链（R33）
3. 默认 `-fopenmp` + `-DWITH_ZLIB`（上游默认，clang++ 可正常编译链接 OpenMP）
4. `make install` 语义：上游 install 目标把 PROGS + *.pl 安装到 PREFIX；
   本配方只打包 6 个可执行程序到 bin/（tool 包，R38 commands.json 声明）
5. zlib/1.3.1 由 Conan 依赖注入（generate() 里 CPPFLAGS/LDFLAGS 指向 Conan 缓存包目录，R49）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 https://github.com/weizhongli/cdhit 超时 (Errno 110) | 本机到 github.com 直连不可达/极慢 | 经 gh-proxy 镜像下载官方 V4.8.1 tag tarball 到 ~/tmp/builds，init-build 复用已有 tarball；conandata.yml 仍声明官方源 URL（R39），CI 有镜像 fallback |
| 2 | lang-preflight 判 mixed（perl:57 占 80%）并写 env_unsupported 终态 | 语言统计把 57 个 .pl/.py 辅助脚本当主体 | 实际主体为 `*.c++`（9 个源码 + 2 头文件）+ Makefile `CC = g++` 纯 C++ 构建；perl/py 为辅助工具脚本，按 R47 边界规则"辅助脚本不算主体"应判 cpp，与任务 cpp 兼容族一致；继续适配并在终态报告说明 |
| 3 | 冒烟测试 /tmp/smoke.faa 创建失败 | 平台 /tmp 只读（SKILL §7 E002） | 输入/输出改用 ~/tmp（$TMPDIR） |
| 4 | `conan download cd-hit/4.8.1 -r=ohpcd` 报 "system acceleration policy not enabled" | 该错误 = 制品仓无此配方（abx/aesfix 先例），非网络故障 | 确认首次适配，版本号 4.8.1 无需后缀（R37） |

## 源码修改
无补丁（patches/ 为空）。适配仅需配方层面处理：命令行 CC 覆盖 + zlib 依赖注入。

## 依赖版本
- zlib/1.3.1（已发布，ohpcd 制品仓）

## 验证结果
```bash
# .work 探索性编译: 6 个二进制全部编译链接成功
./cd-hit -h   # CD-HIT version 4.8.1 (+OpenMP) 正常输出
# 功能冒烟: 3 条微型序列聚类
./cd-hit -i ~/tmp/smoke.faa -o ~/tmp/smoke.out -c 0.9 -n 5
# → 3 sequences finished, 2 clusters；seq1+seq2 同簇 (100%)，seq3 独立簇
# test_package: conan create 内真实调用 cd-hit 聚类并断言 .clstr 含 2 簇
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | make 型 tool 配方（zlib 依赖注入、CC 覆盖） |
| conandata.yml | 官方源 URL + 交叉验证 SHA-256 |
| test_package/ | 真实功能测试（R34：实际执行 cd-hit 并断言聚类结果） |
| commands.json | R38 tool 类型声明（6 个可执行程序） |
| manifest.yaml | 版本元数据 |

## 注意事项
- cd-hit 是 tool 包（application），无库文件，package_info 无 libs
- 上游无测试套件（无 make check/ctest）；质量证据 = test_package 功能冒烟
- 知识快照位于 worktree 外只读目录，HEAD 29f3623763（knowledge 540 条正式 + 337 草稿）
---

**编译结束**: 2026-09-05 17:54
**最终状态**: built
