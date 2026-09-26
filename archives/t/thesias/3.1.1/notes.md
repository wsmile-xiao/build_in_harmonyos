# thesias 3.1.1 适配笔记

任务号 11123 ｜ 分支 feat/thesias-3.1.1 ｜ 主理 DS-8 ｜ 适配路径 A+B（本文底部 B 判定）

## 编译环境
- 构建系统: makefile（上游自含 Makefile，配方按 R33 直接取 tools.build:compiler_executables 的 clang 编译 src/*.c，不走 make）
- 编译日期: 2026-09-21
- 编译器: clang 15（/data/service/hnp/bin/clang，OHOS aarch64）
- 状态: built
- JDK: bishengjdk-17.0.13-ohos-aarch64（build() 纯 Python 自举，jna/5.19.0 先例 E084）

## 编译步骤
1. conan create 拉取官方源（github.com/daissi/thesias tag 3.1.1，sha256 0a6d09b8…f864）
2. `_install_jdk()`：无系统 JDK 时从 cmd-pkgs releases 纯 Python 下载解压 bishengjdk17（取 jni.h/javac/jar）
3. 逐个编译 src/*.c（-O2 -fPIC -I$JAVA_HOME/include -I$JAVA_HOME/include/linux）
4. 链接 -shared -Wl,-soname,libthesiaslib.so → libthesiaslib.so（SONAME=文件名同形）
5. javac -d class java/*.java + jar cfe thesias.jar GraficT（上游 all 目标的 Java GUI 半边）
6. package(): libthesiaslib.so→lib/、thesiaslib.h→include/、thesias.jar→res/
7. test_package: 编译 test.c → test_thesias，self.run(env="conanrun") 真实运行

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan source() 下载失败（ghfast.top 镜像超时） | 网络劣化 | 按共享 dlcache 播种先例：s/<内容sha256> + sidecar（references 覆盖官方与镜像两种 URL 形态），字节取本地已下 tarball 并 sha256sum 复核 |
| 2 | 消费者测试报 Error loading shared library libthesiaslib.so.0 | SONAME(.so.0)≠包内文件名(.so)，DT_NEEDED 按 SONAME 找不到 | SONAME=文件名同形（-Wl,-soname,libthesiaslib.so，jna/libjnidispatch.so 先例） |
| 3 | SONAME 修复后 ctest 仍找不到库 | conan 2 CMakeDeps/CMakeToolchain 不注入 rpath，ctest 无 conanrun env | test() 改 self.run(二进制, env="conanrun")，仍为真实运行（非只链接） |
| 4 | 编译输出接 head 管道导致误判"符号未导出" | head 触发 SIGPIPE 截断编译链，部分 .o 未生成 | 编译日志重定向文件；nm -D 复验 11 个 .o 全部参与链接 |

## 源码修改
无补丁、无源码改动（patches: {}；上游源码原样编译通过）。

## 依赖版本
- 无 conan 依赖（Cephes 内嵌；JDK 为构建期自举工具，非包依赖）

## 上游测试账本（五维，AGENTS §10.1）
- `N_static` = **0**：上游 3.1.1 仅一份自含 Makefile（目标 all/clean/install/uninstall），
  无 check/test 目标、无 tests/ 目录；examples/ 为数据集（dataset1-3）非注册用例；
  java/ 为 GUI 源码无测试。静态清点按 Makefile 目标与目录树逐项核对（MANIFEST.yml 同源）。
- `N_registered` = 0（无测试目标可注册）
- `N_executed` = 0（上游确无自动化测试，如实申报；"上游无测试须附清点证据"——
  证据即上游 Makefile 全文 + 源码树清单，见 reports/conan-create.log 的构建目标）
- 未执行分类数 = 0（无用例可分）
- `N_consumer` = **1**：test_package/test.c（7 个数值断言：ndtri(0.975)=1.959963984540054、
  lgam(5)=ln24、igam(0.5,1)=erf(1)、igamc(0.5,1)=erfc(1)、chdtr(1,χ²₁@95%)=0.95、
  chdtri(3,0.05)=7.81472790325118、igami(0.5,erfc(1))=1；直调导出符号 igam/igamc/
  igami/chdtr/chdtri/ndtri/lgam，链接 libthesiaslib.so 并真实运行）

## 路径 B 判断（A+B 申报）
- **查重**：知识图谱检索 JNI/JDK/java 命中家族条目 E084（jna，JDK 自举）；draft-review
  相似 TOP3 = E492/E274/E316（最高 0.42 灰区）；按"组合型知识不判重"在草稿中列明
  组分清单（E084 自举 / E083 签名链解除条件 / E274 SONAME 机制引用）。
- **探针**（≤30 分钟，§6.2 家族命中规则）：OHOS clang 编 src/*.c 后 `nm -D` 实测——
  igam/igamc/igami/chdtr/chdtrc/chdtri/ndtri/lgam 与 Java_thesiaslib_thesiasRun 全部
  T 导出 → C 层可直调，消费者测试无需 JVM，E083 签名链整体跳过（jna 当年必须走
  JVM+签名，本例行为有实质偏差 → 升路径 B）。
- **拟沉淀主题**：JNI 共享库消费者测试选型探针（nm -D 判 C 层可测性）+ SONAME 同形
  + conanrun 直跑三件套；草稿 `knowledge/drafts/DRAFT-11123-thesias-jni-c-level-
  consumer-test-skip-jvm.{kv,md}`，已过真实 YAML 解析器与 draft-review。
- **知识库扩展 Issue**：随 PR 建立互链（Issue 号回填处见 PR 正文路径 B 节）。

## 验证结果

```bash
# conan-verify（干净构建）全绿：G1-G4 + L2/L4/L5
ohc-run.py conan-verify thesias 3.1.1
# 消费者测试真实运行输出（reports/conan-create.log）：
ok   ndtri(0.975) = 1.959963984540054
ok   lgam(5.0) = 3.1780538303479458
ok   igam(0.5, 1.0) = 0.84270079294971512
ok   igamc(0.5, 1.0) = 0.15729920705028497
ok   chdtr(1, 3.841458820694124) = 0.95000000000000007
ok   chdtri(3, 0.05) = 7.8147279032511801
ok   igami(0.5, erfc(1)) = 0.99999999999999889
test_thesias: 7/7 Cephes assertions passed
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | 配方（JDK 自举 + 显式 CC 编译 + jar 构建） |
| conandata.yml | 官方 URL + sha256 |
| test_package/ | 消费者测试 test.c（7 断言）+ MANIFEST.yml + conanfile.py |
| manifest.yaml | 版本级 manifest（status: built） |
| knowledge/drafts/DRAFT-11123-*.kv/.md | 路径 B 知识草稿 |

## 编译结束
status: closed
COMPLETED
---

**编译结束**: 2026-09-21 09:11
**最终状态**: built
