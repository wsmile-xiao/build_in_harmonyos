# libsz 1.1.6 适配笔记

## 1. 上游身份

- 软件：libsz（SZIP 兼容压缩库），随 libaec 同源发布。
- 上游版本：1.1.6（tag v1.1.6，2026-02-24）。
- 上游仓库：https://github.com/Deutsches-Klimarechenzentrum/libaec
  （README 指定的官方下载位置之一；GitLab 主仓为
  https://gitlab.dkrz.de/k202009/libaec）。
- 源码包：`v1.1.6.tar.gz`，2,785,733 字节，
  SHA256 `87c1e4ec6ec5157283434f5d707832eabea30cb2efe0c571118f3c1eb05faceb`
  （2026-09-18 下载实测；单根目录 `libaec-1.1.6`，含 CMakeLists、tests、
  data/121B2TestData 及 LICENSE.txt）。
- 许可证：BSD-2-Clause。语言：C（C99）。构建系统：CMake（≥3.26）。
- 依赖：无第三方依赖。

选用 GitHub 官方 tag 包的原因：仓库 CI 的镜像兜底逻辑
（`ci/conan/build_and_test.sh`）仅对 github.com 等域名自动追加镜像回退，
GitLab 域名不在其中；GitHub 包与 GitLab 包内容同源（同一 tag）。

## 2. 上游测试审计

`tests/CMakeLists.txt`（v1.1.6）注册的 CTest 用例共 7 个：

| 用例 | 内容 | 夹具 |
|------|------|------|
| check_code_options | 编码选项组合 round-trip | 无 |
| check_buffer_sizes | 边界 buffer 尺寸 | 无 |
| check_seeking | seek/随机访问 | 无 |
| check_long_fs | 长文件系统相关检查 | 无 |
| check_szcomp | sz 压缩文件 round-trip | `data/121B2TestData/ExtendedParameters/sar32bit.dat`（随包发布） |
| check_rsi_block_access | RSI 块访问 | 无 |
| sampledata.sh | graec 编解码 CCSDS 样本数据 | `data/121B2TestData`（随包发布，仅 UNIX 注册） |

结论：上游存在测试（7 个），必须在真机完整执行，不做任何删减与修改。
`sampledata.sh` 的下载目标（`update-sampledata`）只是维护用 target，
测试本身只读随包数据，无需联网。

## 3. 构建设计

- 标准 CMake 流程：`cmake.configure()`、`cmake.build()`、
  `cmake.install()`，无补丁（`patches/` 不创建）。
- `shared=True`（默认）时仅构建 shared（`BUILD_SHARED_LIBS=ON`、
  `BUILD_STATIC_LIBS=OFF`）；`shared=False` 时仅构建 static。
  上游要求两者至少其一为 ON，映射关系已覆盖。
- `BUILD_TESTING=ON` 固定开启，保证测试目标一定被构建。
- 上游 configure 期检查（`__builtin_clzll` 编译探测、`snprintf`
  符号探测）均为只编译不运行，对交叉/OHOS 安全。
- 上游 `cmake --install` 只安装库与头文件（`graec` 工具不在安装目标中），
  因此本包为纯库包，不声明 `commands.json`。
- 同一份源码同时产出 `sz` 与 `aec` 两个库（`sz` 静态链接了 `aec` 对象），
  `package_info` 声明 `libs = ["sz", "aec"]`，对外提供统一的
  `libsz::libsz` CMake 目标与 `libsz` pkg-config 名。

## 4. 上游测试执行设计（conanfile build 阶段）

- 先 `ctest -N` 发现用例数（期待 7），再 `ctest --output-on-failure`
  实跑并捕获全部输出。
- 通过判据（缺一即失败）：退出码 0、在输出中找到
  `100% tests passed, 0 tests failed out of 7` 摘要、摘要总数等于发现数、
  每个发现的用例名都在输出中有 `Passed`  verdict、输出非空。
  该设计可拦截“退出码 0 但实际静默跳过”类假阳性。
- 失败时输出尾部日志并打 `status:"failed"` 标记后抛异常，
  `conan create` 不会带病变绿。
- 标记：`HMBS_UPSTREAM_TEST_RESULT`（framework 为 `ctest`）。

## 5. test_package 设计

两个安装包消费者（各 5 个 CHECK 断言，共 10 个，见 MANIFEST.yml）：

1. `test_sz_roundtrip`：8 位合成低熵样本，
   `SZ_BufftoBuffCompress` → `SZ_BufftoBuffDecompress`，
   断言压缩成功、输出更小、解压成功、长度一致、字节一致。
2. `test_aec_roundtrip`：8 位合成相关有符号样本，
   `aec_encode` → `aec_decode`（README 示例流程），
   断言初始化与编解码成功、有输出、回环前缀与输入一致
   （解码器对块对齐输入可能产生填充，故按前缀比较，上游 README 有载明）。

两个程序仅在全部断言通过后打印唯一的 `LIBSZ_TEST ... PASS` 行，
任一失败即返回非零。`test()` 用 `can_run` 守卫（不可运行直接报错，
不静默跳过），以 `conanrun` 环境实跑两个二进制后输出
`HMBS_TEST_PACKAGE_RESULT`（discovered=2/passedCount=2）。

## 8. 真机预检 round 1（2026-09-17，upstream_test 失败）复盘

- 现象：`ctest --output-on-failure` 实跑约 54s（`Total Test time` 已打印，
  退出码 0），但 harness 报
  `exit 0 but no ctest summary line in harness output`
 （discovered=7，executed=0）。
- 排查：上游 7 个用例源码（`tests/*.c`、`sampledata.sh`、`src/graec.c`）
  均未硬编码 `/tmp`（sampledata 中间文件写在 ctest 工作目录），
  `/tmp/...Read-only file system` 来自 preflight.sh 自身 306 行，
  属平台噪声；真正的门禁失败是 harness 摘要正则过严
  （单空格字面匹配，不容忍 ANSI 着色/多空格/`\r`），把已通过的套件误判为失败。
- 修复（仅 `conanfile.py`，上游测试零改动）：
  1) 子进程改按字节捕获后 `errors="replace"` 解码；
  2) 先剥 ANSI、去 `\r` 再用空白容忍正则
     `(\d+)%\s+tests?\s+passed\s*,\s*(\d+)\s+tests?\s+failed\s+out\s+of\s+(\d+)`
     匹配摘要，per-test `Passed` 判定同样走归一化后输出；
  3) 失败日志从尾部 4000 字符扩到结构化诊断
     （ctest 路径/目录/rc/字节数/摘要行/每用例 verdict/尾部 20000 字符），
     下轮若仍失败可直接定位；
  4) `_subprocess_env` 补 `TEST_TMPDIR` 并确保
     `HMBS_AUTOCONF_MKTEMP_FALLBACK` 目录真实创建。
- 证伪：本地 `py_compile` 通过；新正则对标准/双空格/ANSI 三种摘要均匹配。
  待 HMBS 下一轮真机预检验证。

## 9. 真机预检 round 2（2026-09-17，同一指纹第 2 次）策略切换

- 对比：round 1 的 stdout 正则加固（ANSI 剥离/空白容忍）已同步上真机
  （报错行号 513→549），但同一 `exit 0 but no ctest summary` 复现，
  说明不是简单的空格/着色问题，不能原样重复 stdout 解析路线。
- 新策略：改用 CTest 落盘结果文件作证——跑前删除陈旧
  `Testing/Temporary/LastTest*.log`，跑后若 stdout 无摘要则读
  `LastTest.log`（同样 tolerant 正则找摘要）+ `LastTestsFailed.log`
  为空 + `Total Test time > 0` + 全部 7 个用例名有 `Passed` verdict
  （stdout 与文件合并交叉验证），四者齐备才判 pass，否则继续 fail-closed。
  该证据仍是框架自身 verdict，不跳过任何测试、不删断言。
- 待 HMBS 下一轮真机预检验证；若文件亦无摘要，则需全量日志定位
  ctest/shim 是否吞掉了汇总行。

## 10. 真机预检 round 3（2026-09-17，同一指纹第 3 次）根因确认

- 决定性证据（本轮日志首次完整透出 harness 诊断行）：
  `ctest summary-line: 100% tests passed out of 7`——真机 ctest
  （`~/.harmonybrew/bin/ctest`）的汇总行根本没有 `, 0 tests failed`
  中段！前两轮的正则（即使空白/ANSI 容忍）都强制要求该中段，
  故 exit 0 + Total Test time 俱在仍永不匹配。
  另见 `raw_bytes=876`（shim 把 1.8MB 详细输出收进 LastTest.log，
  stdout 只留精简汇总），故 file 侧 `passed_in_file=0` 只是格式差异，
  `failed_file=empty` 反而佐证全过。
- 修复（仍是 harness 解析层，上游测试零改动）：
  1) stdout 与 LastTest.log 两处摘要正则把 `, N tests failed`
     改为可选组，同时接受长短两种格式；短格式下以 percent==100
     判定零失败（percent<100 照旧判失败）；
  2) stdout 摘要通过但个别用例缺 Passed 行时，先用 LastTest.log
     做交叉复核再判失败（shim 精简 stdout 可能省略逐用例行；
     严格性不变——每个用例仍需框架来源的真实 Passed）。
- 本地 `py_compile` + 长短/失败三种摘要解析自测通过。
  待 HMBS 下一轮真机预检验证。

## 6. OHOS 相关说明

- 纯计算 C 库，无平台相关代码、无系统调用依赖，无需补丁，
  无 `__OHOS__` 分支（R8 不涉及）。
- 与系统库无同名冲突（OHOS 无 libsz），默认 shared 动态包合规。
- `validate()` 限定 `os in ("Linux", "OHOS")`。

## 7. 证据状态

- 本轮为首轮工作树：配方已按上游源码与仓库规范完成，
  尚未经过真机预检。
- `manifest.yaml` 的 `status: built` 表示配方完整可构建，
  最终状态与 PR 正文通过率以 HMBS 真机预检日志为准，
  预检返回后按实测更新。
