# vbackup 1.0.1 适配笔记

## 编译环境
- 构建系统: autotools（git tag 归档无预生成 configure，build() 内 autoreconf -fi 自举）
- 编译日期: 2026-09-19
- 编译器: clang/clang++（本包为 bash 脚本模块，无 C/C++ 编译产物）
- 状态: built

## 编译步骤

1. `autoreconf -fi`（automake/1.18 + libtool/2.5.4 经 tool_requires 提供，W0 经 conan download 探针确认均已发布）。
2. 剥离生成的 configure 中 `umask 077`（E114：HMDFS setgid 使 0700 临时目录不可写，实测 config.status "subs1.awk: Permission denied"，修后通过）。
3. `./configure --build/--host=aarch64-unknown-linux-ohos`（E007：config.guess 无法识别 HarmonyOS）。
4. `make -j1`（E074）+ `make check -j1`（占位目标，N_static=0，照实记录）。
5. `autotools.install()`（conan 原生 DESTDIR 安装）；conan-verify G0-G4/L2/L4/L5 全部通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: subs1.awk Permission denied | E011/E114：HMDFS UID 映射+umask 077 临时目录不可写 | 生成的 configure 剥离 umask 077（参照 abiword-plugin-clarisworks 的 _drop_umask_077） |
| 2 | 脚本运行时找 //share/vbackup/helpers | 脚本内编译期 @prefix@ 被替换为空/绝对路径，包不可重定位 | patches/0002：prefix 等改为从脚本自身位置推导（$0/BASH_SOURCE），包可重定位 |
| 3 | 脚本 shebang /bin/bash 不存在 | OHOS bash 不在 /bin | patches/0001：shebang → /usr/bin/env bash（脚本用 [[ ]]、=~、BASH_REMATCH，必须 bash，仅改定位方式） |
| 4 | conan create 复用缓存二进制 | test_package 改动不影响 package_id | `conan remove "vbackup/*" -c` 清缓存强制重编 |

## 源码修改

- patches/0001-vbackup-env-bash-shebangs.patch：scripts/bin/{vbackup,vbackup-wizard,run,common}.in 四文件 shebang 改 env bash（sb_edit.in 本为 /bin/sh 无需改）。
- patches/0002-vbackup-relocatable-prefix.patch：scripts/bin/{vbackup,vbackup-wizard,run,sb_edit}.in 与 common.in 的编译期路径变量改为运行时按脚本位置推导。
- 上游 tarball docs/_static/rtd 存在指向 Debian 系统字体路径的悬空符号链接（2016 年上游即如此），不参与构建/安装，未修改。

## 依赖版本

- tool_requires：automake/1.18、libtool/2.5.4（制品仓已发布，conan download 探针通过）。
- 运行时依赖：bash（PATH 可解析）。

## 验证结果

```bash
autoreconf -fi && ./configure && make -j1 && make check -j1   # 全 rc=0（check 为占位）
make install                                                   # bin/vbackup + share/vbackup + man
conan-verify vbackup 1.0.1                                     # 全门禁通过
test_package: vbackup --version                                # 断言 "vbackup v1.0.1" 输出（1/1）
```

## 注意事项

- 上游无任何测试（N_static=0）：make check 为 automake 占位目标；消费者测试（test_package）补位并在 MANIFEST.yml 申报。
- 包内脚本运行时依赖 bash；init-build 双轨目录对无 configure 的包会反复重解压（悬空链接+copytree ENOENT），探索期直接手工 .work 即可。
---

**编译结束**: 2026-09-19 05:12
**最终状态**: built
