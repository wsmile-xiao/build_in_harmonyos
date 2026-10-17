# deltarpm 3.6.5 适配笔记

## 上游信息
- 名称: deltarpm 3.6.5
- 上游仓库: https://github.com/rpm-software-management/deltarpm
- 版本 tag: 3.6.5 (commit b559d700, "Relese 3.6.5")
- 源码包: https://github.com/rpm-software-management/deltarpm/archive/refs/tags/3.6.5.tar.gz
- sha256: f3fba9b96c55be21696466bbfc3b2a623a4fb35646ff9a135f5c29406b412f22 (573411 字节, 实测下载计算)
- License: BSD-3-Clause (LICENSE.BSD)
- 构建系统: 纯 Makefile (无 configure / CMake / meson)

## 上游测试审计 (R51 三步法第 1 步: 清点)
- 顶层 Makefile 目标: all / python / perl / clean / install, 无 check / test / check_PROGRAMS 目标
- 全包 266 个文件: `TEST(` / `TEST_F` 出现 0 次, `def test_` 出现 0 次
- 无 tests/ / test/ / t/ 目录; 仅 zlib-1.2.2.f-rsyncable/contrib 下有示例性质的 test 样例,
  未被任何构建目标引用 (与 deltarpm 自身功能无关)
- `make -n check` 展开为空 (无此目标)
- 结论: 上游确无测试套件 → test_package/MANIFEST.yml 写入 upstream_tests_exist: false 及完整审计,
  构建与 test_package 按规范输出 `status:"no_tests"`、`discovered:0`、`executed:0` 及具体 reason

## 依赖 (W0)
- lzma/5.6.2 (published, 包名仅 ohpcd 有, 解析确定; 自带完整头文件与静态 liblzma.a)
- bzip2 1.0.8 / zstd 1.5.6: 不再走 Conan 依赖, 改从官方源码树内静态构建
  (conandata.yml `vendored` 节, sha256 校验; 原因见下表 #8; lzma 切换见 #9)
- zlib: 使用上游自带 rsyncable 副本 (zlib-1.2.2.f-rsyncable) 树内静态构建 libz.a, 不引入外部依赖
- rpm: 不依赖。rpmdumpheader.c 链接 -lrpm -lrpmio, 而 rpm/6.0.2 在制品仓状态为 built (未发布),
  按 R36 不得依赖未发布包, 故配方只构建其余 6 个工具 (makedeltarpm/applydeltarpm/combinedeltarpm/
  makedeltaiso/applydeltaiso/fragiso), 均只用自带 rpmhead.c 解析 RPM 头, 无需 librpm

## 编译步骤 (OHOS aarch64 真机执行, 待预检)
```sh
cd archives/d/deltarpm/3.6.5
conan create . --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 默认 `make all` 会构建 rpmdumpheader 并链接 -lrpm | 该二进制需 librpm, rpm 包未发布 | 配方显式构建 6 个 librpm-free 目标, 跳过 rpmdumpheader; notes 与 PR 补充说明如实声明 |
| 2 | 子 make (`cd zlib-*-rsyncable; make CFLAGS=... libz.a`) 不透传 CC | 上游 Makefile 硬编码, 真机默认 cc 不存在 | build() 从 conf 取 CC/CXX/AR/RANLIB, 以 os.environ 注入 (R33 合规来源), 父子 make 均生效 |
| 3 | `make install` 会安装 rpmdumpheader 且用固定 prefix | 与“跳过 rpmdumpheader”决策冲突 | 不用上游 install, 改用 conan copy() 安装 6 二进制 + drpmsync + man8 + LICENSE.BSD |
| 4 | 上游无测试套件, `make check` 为 no-op | 纯工具包, 上游未提供测试 | test_package 以 2 个行为冒烟脚本覆盖 6 个二进制, 输出 HMBS 双标记 (no_tests 审计) |

| 5 | 真机预检卡在bzip2依赖CMake配置失败，早于本配方build执行 | 预检同时启用conancenter与ohpcd，bzip2解析到conancenter的CMake配方，其try_compile在只读/tmp下失败；本配方此前无generate阶段 | 上轮已加conf路径存在性回退与TMPDIR透传；本轮补generate()+VirtualBuildEnv+Environment固化TMPDIR，不改依赖版本 |
| 6 | 本配方缺generate()，构建环境未聚合 | 纯Makefile配方此前无generate，conanbuild环境缺失 | 新增generate(): VirtualBuildEnv聚合+Environment定义TMPDIR/TMP/TEMP并save_script |
| 7 | xz依赖在双远端环境下可能解析到非OHOS配方 | 上游cfile.h无条件include lzma.h，不可裁剪；xz/5.8.3.1为ohpcd已发布的OHOS加固版（mktemp wrapper+umask修复，同上游5.8.3） | requirements改 pin xz/5.8.3.1，同步manifest/README/notes；bzip2/zstd保持不变（无已发布的ohpcd-only后缀版，转版本违反R36） |
| 8 | 连续三轮预检compile失败于同一位置且指纹不变：bzip2/1.0.8 取到conancenter的CMake配方（`cmake.configure … line 62`、`CMakeToolchain generated`、`System is unknown to cmake / Platform/HarmonyOS`），早于本配方build()执行 | 双远端下普通版本号按远端顺序解析到conancenter配方，其try_compile在OHOS上必然失败；本配方侧任何build()/generate()改动都对此无效（依赖先构建）；ohpcd又无已发布的bzip2/zstd独有版本可钉选。另发现本配方缺失source()方法（此前被依赖失败掩盖） | 换路线：依赖图层面消除歧义——仅保留ohpcd独有的xz/5.8.3.1；bzip2 1.0.8与zstd 1.5.6改从官方源码树内直编静态库（conandata新增`vendored`节，source()显式下载，build()用已验证conf编译器直编+ar归档，无configure/CMake；bzip2取7个库单元，zstd取lib/{common,compress,decompress}/*.c），LDLIBS改按路径链接；cfile.h/cfile.c已审计：zstd全程受WITH_ZSTD守卫、bzip2/lzma为硬依赖，故两者都就地提供以保留完整功能；LICENSE按目录收入licenses/ |
| 10 | applydeltarpm.o 编译报 20 个 error：`#define RPMDUMPHEADER /usr/local/bin/rpmdumpheader`（宏展开后无引号，`execlp(RPMDUMPHEADER, ...)` 全错） | 配方以单层转义传递字符串宏：Python 单引号字面量中的 `\"` 在运行时只剩裸 `"`，外层 `CPPFLAGS="..."` 的 shell 解析提前闭合引号；即使补到单反斜杠，make 变量得到裸引号，第二层编译 shell 仍会剥掉引号，宏依然是裸路径——共两层 shell 引用，而非一层 | 改用 `chr(92)*3 + chr(34)` 逐字符构造运行时 `\\\"`（每侧 3 反斜杠+引号，源码零字面转义）：L1 外层双引号解析后 make 变量持有 `\"`，L2 编译 shell 解析后编译器 argv 持有标准字符串字面量；已用双层 POSIX shell 解析模拟验证端到端 argv，并加注 L1/L2 注释防回归 |
| 9 | 上轮vendoring后预检推进到本配方编译但止步于`makedeltarpm.c:18: fatal error: 'lzma.h' file not found`——而CPPFLAGS已含xz/5.8.3.1包的include目录 | xz/5.8.3.1的已发布二进制头文件缺失（其配方目录亦已不在树内，仅manifest留痕），非本配方-I传参问题；该包不可修复，只能绕行 | 再换路线：liblzma提供方由`xz/5.8.3.1`改为`lzma/5.6.2`（包名级ohpcd独有，conancenter无`lzma`包，解析确定性更强；published且产物清单明确含`lzma.h`+`lzma/*.h`+静态liblzma.a；dpkg/1.23.7已如此消费）。仅改requirements()一行，头文件/库目录经_dep_flags()自动拾取。CVE说明：5.8.3修复的CVE-2026-34743是lzma_index_append空索引溢出，deltarpm仅用流式编解码API（cfile.c已审计无index调用），无可达路径，且上游评估真实应用基本不可达 |
## test_package 设计 (R34 实质调用)
- test_iso_tools.sh: 无参运行 makedeltaiso / applydeltaiso, 断言退出非零 + 输出含
  `usage: makedeltaiso` / `usage: applydeltaiso` + 日志非空
- test_rpm_tools.sh: 无参运行 makedeltarpm / applydeltarpm / combinedeltarpm / fragiso,
  断言退出非零 + 输出非空且自标识 (combinedeltarpm/fragiso 匹配精确 usage 行,
  makedeltarpm/applydeltarpm 匹配程序名, 因其 usage 措辞未经源码审计确认)
- 证伪能力: 若二进制为 `exit 1` 桩, 将输出空内容, grep 断言失败 → conan test 失败,
  harness 可捕获 (退出码 0 且无标记/零执行同样被 HMBS 门禁拒绝)
- 未做 makedeltaiso/applydeltaiso 真实往返的原因: rpmoffs() 要求 ISO9660 主卷描述符
  (非 ISO 输入直接 `primary volume descriptor missing` 退出 1), 手工构造最小 ISO 镜像
  脆弱易错, 已在 PR 补充说明如实声明

## 验证结果 (待 HMBS 真机预检回填)
- conan create: 待回填
- test_package 2/2: 待回填
- 上游测试: 不适用 (上游无套件, no_tests 审计见 MANIFEST.yml)

## 注意事项
- 本轮仅完成未提交工作树, 未执行 commit/push/PR, 待 HMBS 后台完整真机验证
- 真机为内部基建, 相关地址与命令仅记于此, 不写入 PR 正文
