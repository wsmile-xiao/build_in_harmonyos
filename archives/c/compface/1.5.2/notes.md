# compface 1.5.2 — OpenHarmony 编译记录

## 基本信息
- 软件: compface
- 版本: 1.5.2
- 构建系统: autotools (autoconf configure + Makefile.in, C)
- 目标: ohos-aarch64 (os=OHOS, arch=armv8, clang 15)
- 上游: 原始发布位 ftp.xemacs.org/pub/xemacs/aux/compface-1.5.2.tar.gz（已 404 下线）
- 实际下载源: https://ftp.mirrorservice.org/sites/download.salixos.org/i486/extra-15.0/source/libraries/compface/compface-1.5.2.tar.gz
- SHA256: a6998245f530217b800f33e01656be8d1f0445632295afa100e5c1611e4f6825
- MD5: 62f4f79c0861ad292ba3cf77b4c48319（与 SlackBuilds compface.info 记录的
  原始 xemacs 上游 tarball MD5 完全一致，证实为未重打包的原始上游源码；
  Debian libcompface_1.5.2.orig.tar.gz 为重打包版，字节数不同，未采用）
- License: MIT（上游 README 自述"MIT captures the original author's intent"，
  原文为 James Ashton 1990 的宽松分发声明；README 随包打入 licenses/）

## 编译指导
- 真正的 autoconf configure（4114 行，AC_PROG_CC 正常读取 $CC 环境变量），
  AutotoolsToolchain 的 CC 注入原生生效，无需命令行参数式 workaround。
- E011（平台知识，已验证）: HMDFS 无法写入 configure 中 `umask 077` 创建的
  临时目录（confstatXXXXXX Permission denied），patch 0001-configure.patch
  将两处 `umask 077` 改为 `umask 022`（多用户场景无写入需求，安全）。
  补丁由 refresh-patch --auto 基于 track-edit 记录生成（+2/-2 行）。
- 老 Makefile.in（2005）不支持 DESTDIR：`make install DESTDIR=...` 会绕过
  staging 直接写入 --prefix。package() 按上游 install 规则手动拷贝
  bin/compface、bin/uncompface、lib/libcompface.a、include/compface.h、
  man1/compface.1、man3/compface.3（uncompface 的 man 为指向 compface.1/3
  的符号链接，打包时省略链接本身）、README → licenses/。
- 探索阶段 `make install DESTDIR=` 曾直接装入 ~/usr/local，误装文件已全部
  清理（bin/compface、bin/uncompface、lib/libcompface.a、include/compface.h、
  man1、man3 共 8 项），不影响后续构建。
- 上游 `make install` 依赖的 host 工具：configure 探测到 ginstall
  （~/usr/local/bin/ginstall）或回退随包 install-sh；man 符号链接用
  `rm -f && ln -s`（符合 HMDFS S1 惯例），实测 RC=0。

## 上游测试统计（口径）
- 上游源码静态声明：0。Makefile.in 仅定义 all/install/clean/dist 等目标，
  无 check/test 目标；源码树无 testsuite/ 目录、无任何测试框架注册入口。
- 实际执行：0（上游无自动化测试可执行）。
- 消费者测试补全：test_package/test_compface.sh（1 个脚本 4 项检查）：
  1. compface 压缩固定 fixture（res/test.dat，48 行 "0x%04X,0x%04X,0x%04X,"
     的上游原始输入格式）产出可打印 X-Face（结构校验：全行可打印字符）；
  2. uncompface 逆变换结果与原文件 cmp 逐字节一致（man 页声明无损）；
  3. uncompface -X 渲染 XBM 位图（≥48 行十六进制像素）；
  4. 对还原数据再次压缩输出与首次完全一致（确定性）。

## 补丁清单
- 0001-configure.patch：E011 HMDFS umask 077→022（仅 configure 临时目录
  权限位，不改变任何构建产物行为；platform_only）。

## 已知限制
无。

## 功能验证
- 探索构建：configure + make 在 OHOS aarch64 clang 15 一次通过（仅旧式
  K&R 函数定义的编译警告，clang 15 默认警告级别，不影响产物）。
- compface/uncompface 往返实验（fixture 即消费者测试所用）：压缩→解压
  cmp 逐字节一致；X-Face 输出 6 行可打印文本。
---

**编译结束**: 2026-09-09 00:44
**最终状态**: built


## 路径 B 判断与依据（2026-09-09）

- **判断**：走路径 B，沉淀知识草稿 `knowledge/drafts/E544-draft-B4CT.kv/.md`（2005 年代 config.sub 连 aarch64 现代三元组也不识别：config.guess 打 E160 分支后仅传 `--build=aarch64-unknown-linux-gnu`、不传 `--host`，绕开 config.sub 对 host 三元组的 CPU 校验）。
- **证据门槛核对**：可复现症状（cityhash conan create G2 日志两形态：`cannot guess build type; you must specify one` 与 `Invalid configuration 'aarch64-unknown-linux-ohos': machine 'aarch64-unknown-linux' not recognized`）+ 稳定错误签名（入草稿）+ 根因（aarch64 CPU 名 2012 年前后才进入 config.sub 词汇表，老版连 aarch64-unknown-linux-gnu 都拒绝，属 CPU 层而非 ohos 后缀层问题）+ 真实验证（补丁 + 仅 --build 后 configure/构建/上游测试/消费者测试全通过）+ 跨仓库复用（发布早于 2012 年的 autotools 软件在 OHOS aarch64 原生构建时普遍适用）。
- **查重结论**：draft-review 相似 TOP3 为 E007(0.44)/E205(0.32)/E122(0.29)，灰区、无等价条目；E007 是 config.guess 无 HarmonyOS 分支（guess 层），E122/E072 是较新 config.sub 对 ohos 后缀的校验（OS 层），本条是 CPU 名层 + 处置为"只传 --build"，层次与方案均不同，已在草稿 similar_to 中标注关联。
- **关联**：知识库扩展 Issue（链接见 PR 正文"路径 B 知识贡献说明"）；本 PR 原子携带草稿文件。
