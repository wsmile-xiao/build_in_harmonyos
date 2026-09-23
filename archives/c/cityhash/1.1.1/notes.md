# cityhash 1.1.1 — OpenHarmony 编译记录

## 基本信息
- 软件: cityhash
- 版本: 1.1.1
- 构建系统: autotools（libtool 库，AC_INIT [CityHash] [1.1.1]，C++）
- 目标: ohos-aarch64 (os=OHOS, arch=armv8, clang 15 / clang++ 15)
- 上游: https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/cityhash/cityhash-1.1.1.tar.gz
  （Google Code 官方归档托管，是 v1.1.1 发布物的唯一正源；GitHub
  google/cityhash 仓库无任何 release tag，master 分支不能代表 1.1.1）
- SHA256: 76a41e149f6de87156b9a9790c595ef7ad081c321f60780886b520aecb7e3db4
- License: MIT（src/city-test.cc 头部 MIT 许可证文本；COPYING 随包打入
  licenses/）

## 编译指导
- E544（平台知识，已验证）: tarball 内 config.sub 逻辑为 2005 年版本，
  不识别 aarch64 CPU 名。conanfile.py 在 OHOS 上显式追加
  `--build=aarch64-unknown-linux-gnu`，并且不传 `--host`（本机构建 host
  缺省等于 build），绕开老 config.sub 对 host 三元组的 CPU 校验；本实例
  因显式给定 build 三元组不需要修改 config.guess，E160 仅作为相关的
  一般性 guess 层经验，未作为本补丁的一部分应用。
- E011（平台知识，已验证）: configure 中 `umask 077` 临时目录在 HMDFS 上
  不可写，同一 patch 将两处 `umask 077` 改为 `umask 022`。
- SSE4.2 选项（--enable-sse4.2）依赖 x86 `_mm_crc32_u64` 内建函数，
  aarch64 上保持默认关闭；此时 citycrc.h 不安装、CRC 相关测试不编译。
- 库为 libtool 管理（libcityhash.la → .so + .a），现代 automake 支持
  DESTDIR，package() 使用 autotools.install() 正常 staging。

## 上游测试统计（口径）
- 上游源码静态声明：src/Makefile.am `TESTS = cityhash_unittest`，1 个
  测试程序（automake test harness）。
- cityhash_unittest（src/city-test.cc，1335 行）为自含式测试：自带 main()
  与 Check() 断言函数，对 CityHash64/32/WithSeed/WithSeeds/Uint128/CRC256
  输出与固定参考向量比对，共 14 处 Check() 调用点。不依赖 Google Test。
- 实际执行：`make check` 输出 "PASS: cityhash_unittest / 1 test passed"
  （设备探索构建与 conan create 各执行一次，均通过）。程序级 1/1，无跳过。

## 补丁清单
- 0001-configure.patch：仅含 E011 的两处 configure 临时目录
  `umask 077→022` 修改；E544 通过显式 `--build`、不传 `--host` 处理，
  未修改 config.guess（platform_only）。

## 已知限制
无。

## 功能验证
- make check: 上游 1 项测试（含 14 个向量断言）全部通过。
- test_package（消费者测试，1 个 C++ 程序 4 项断言）:
  编译并链接打包后的 cityhash 库与 city.h 头文件，调用真实 API：
  1. CityHash64("abc") = 2640714258260161385
  2. CityHash64WithSeed("abc", 12345) = 13914286602242141520
  3. CityHash32("abc") = 795041479
  4. CityHash64("hello ohos cityhash test") = 14920966190624787894
  参考值取自同一 release 的上游测试向量，跨平台一致。
---

**编译结束**: 2026-09-09 01:39
**最终状态**: built


## 路径 B 判断与依据（2026-09-09）

- **判断**：走路径 B，沉淀知识草稿 `knowledge/drafts/E544-draft-B4CT.kv/.md`（2005 年代 config.sub 连 aarch64 现代三元组也不识别：本实例仅传 `--build=aarch64-unknown-linux-gnu`、不传 `--host`，绕开 config.sub 对 host 三元组的 CPU 校验；E160 是相关但未应用的 guess 层经验）。
- **证据门槛核对**：可复现症状（cityhash conan create G2 日志两形态：`cannot guess build type; you must specify one` 与 `Invalid configuration 'aarch64-unknown-linux-ohos': machine 'aarch64-unknown-linux' not recognized`）+ 稳定错误签名（入草稿）+ 根因（aarch64 CPU 名 2012 年前后才进入 config.sub 词汇表，老版连 aarch64-unknown-linux-gnu 都拒绝，属 CPU 层而非 ohos 后缀层问题）+ 真实验证（E011 补丁 + 仅 --build 后 configure/构建/上游测试/消费者测试全通过）+ 跨仓库复用（发布早于 2012 年的 autotools 软件在 OHOS aarch64 原生构建时普遍适用）。
- **查重结论**：draft-review 相似 TOP3 为 E007(0.44)/E205(0.32)/E122(0.29)，灰区、无等价条目；E007 是 config.guess 无 HarmonyOS 分支（guess 层），E122/E072 是较新 config.sub 对 ohos 后缀的校验（OS 层），本条是 CPU 名层 + 处置为"只传 --build"，层次与方案均不同，已在草稿 similar_to 中标注关联。
- **关联**：知识库扩展 Issue（链接见 PR 正文"路径 B 知识贡献说明"）；本 PR 原子携带草稿文件。
