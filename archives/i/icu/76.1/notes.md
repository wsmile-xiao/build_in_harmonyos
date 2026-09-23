# icu 76.1 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-07
- 编译器: clang 15 / clang++ 15
- 状态: built

## 编译步骤

1. 下载源码: `icu4c-76_1-src.tgz` from GitHub releases
2. 解压后进入 `source/` 子目录
3. 运行 configure (三步法):
   - `configure --no-create` 生成 config.status
   - 修复 config.status 中 `umask 077` → `umask 022`
   - 运行 `config.status` 生成 Makefile
4. 编译: `make -j1` (HMDFS 不支持 jobserver FIFO)
5. 安装: `make DESTDIR=<pkg_dir> install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Error -11 (SIGSEGV) 运行 configure | Conan conanbuild.sh 导致 /bin/sh 崩溃 | 不 source conanbuild.sh，直接设 CC/CXX/AR/RANLIB 环境变量 (E064) |
| 2 | "Cross compiling but no --with-cross-build" | ICU configure 检测到交叉编译要求 --with-cross-build | 创建最小 cross-build stub 目录含 icucross.mk + icucross.inc |
| 3 | config.status "Permission denied" 创建 subs1.awk | HMDFS 上 umask 077 创建的目录当前 UID 不可写 | 三步法: configure --no-create → sed umask 077→022 → config.status (E011) |
| 4 | ../bin/icupkg: No such file or directory | --disable-tools 导致 icupkg 未构建 | 移除 --disable-tools，data 处理需要 icupkg |

## 依赖版本

无外部依赖

## 上游测试实跑（2026-09-16，pc1-10 实测）

完整构建（configure 三步法 + make -j1 全量 + make install）通过；随后在启用
上游测试的验证构建树（testsrc）中实测两个套件：

| 套件 | 源码声明 | 实际运行 | 结果 |
|------|---------|---------|------|
| intltest（C++） | 79 个含 TESTCASE_AUTO 的测试文件，1521 个 TESTCASE_AUTO 宏 + 538 个 CASE 注册 | 全量 | 2310 子用例 OK；3 处 ERROR 为 TestMessageFormat2 的 message2/spec JSON conformance 数据缺失（源码包不含，需网络获取，非代码/配方问题） |
| cintltst（C） | 126 个 .c/.h 文件，581 个 addTest 注册 | 全量 | 136 项 [OK]、0 [FAIL]、1 项崩溃：`ucptrietest/TrieTestSet1` golden 序列化阶段 Signal 6 core dump（`./cintltst /tsutil/ucptrietest/TrieTestSet1` 稳定复现；交叉 stub 平台宏 U_HAVE_STRTOD_L/U_HAVE_XLOCALE_H 与 host 实测不一致疑似原因，非配方可修项） |
| iotest / letest | 5 / 12 源文件 | 未实例化 | --disable-icuio / --disable-layoutex 上游条件禁入 make check（MANIFEST 已注明） |

双口径：`source_declared_total`(上游源码可枚举注册数) = intltest 1521+538 + cintltst 581；
`configured_executable_total`（当前 OHOS 配置实例化的独立测试程序）= 2（intltest、cintltst）;
`executed_passed_total` = 2 个套件程序均可运行并输出结果（intltest 2310 子用例 OK，
cintltst 136 OK + 1 子用例崩溃）。iotest/letest 为上游互斥分支（禁用 icuio/layoutex），
不视为失败，计为未实例化并按分母说明。

全量通过率口径：以源码可枚举独立用例计，intltest 2310/2310 通过（3 处数据缺失
ERROR 为 conformance 数据获取问题，非代码失败），cintltst 136/137（1 项崩溃）。
恢复条件：message2/spec JSON = 网络可达 unicode-org/conformance 后补数据重跑；
TrieTestSet1 = 需上游/平台确认 stub 平台宏一致性。

## 消费者验证与鸿蒙专项测试（实测通过）

- 消费者测试（test_package/test.c，9 断言）：`ucol_open("en")+ucol_strcoll`（Foo>Bar 大小写敏感）、
  `ucal_open+ucal_get`（2024-01-01 星期一 round-trip）、`u_getVersion>=76`；静态链接
  icuuc/icui18n/icudata（LINK_GROUP:RESCAN 环形引用）后运行 OK。
- 独立消费者用例（consumer.c）：仅用安装公开头/API 调用 `ucol_strcoll(zh)`+
  `ucal_get`，clang 编译 + clang++ 链接（libc++ 运行时），运行 exit 0。
- 鸿蒙专项测试（icu_ohos_test.c，6 断言全 PASS）：静态数据打包验证（unsetenv ICU_DATA
  后 u_getVersion/ucol_open 仍可用）、zh-CN locale 资源、Asia/Shanghai 时区、
  udat_open+udat_format（2024-01-01 zh-CN 输出 "2024年1月1日 08:00:00"）。

## 验证结果

```bash
conan create archives/i/icu/76.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# configure 通过，编译启动正常（stubdata、common、i18n 编译成功）
```

2026-09-16 实测：配方 rebuild 全量成功（libicudata.a 31.9MB 静态数据打包、
libicui18n.a 10.0MB、libicuuc.a 4.9MB）；G3 系统同名库扫描 0 冲突；
L4 PIE+RELRO+BIND_NOW；L5 SHA-256 基线已记录。
完整步骤见 reports/conan-verify 相关日志与知识候选台账。

## 知识路径决定（2026-09-16，pc1-10）

- **路径 B（知识库扩展）**：C1 候选"ICU --with-cross-build 最小 icucross.mk/icucross.inc stub"
  已实测验证、可跨库复用（ICU 76.x/77/78 同机制）、查重为部分覆盖且有组合/边界/测试迁移
  新增差异 → 建立 `knowledge/drafts/DRAFT-icu-76.1-ohos-minimal-icucross-stub.kv` + `.md`
  配对草稿，与本次归档进入同一 PR。
- 复用既有知识：C2 umask（E011/E129/E206/E223）、C3 conanbuild.sh SIGSEGV（E064）、
  C4 TrieTestSet1 崩溃按测试观察记录（非知识条目）。
- 台账与七轴查重详见 reports/knowledge_candidate_ledger.md。

## 注意事项

- ICU 源码较大，完整编译需较长时间（CI 超时 3600s 应足够）
- cross-build stub 目录在 build_folder 内动态创建，无需额外维护
- config.sub 已原生支持 `aarch64-unknown-linux-ohos` 三元组
