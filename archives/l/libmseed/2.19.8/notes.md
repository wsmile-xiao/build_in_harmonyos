# libmseed 2.19.8 — 适配记录

> 分支: feat/libmseed-2.19.8
> 最后更新: 2026-09-16
> 申请人: yinuoguo / 队伍: 干

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libmseed |
| 版本 | 2.19.8 |
| 状态 | built (待真机预检复核) |
| 构建系统 | makefile (无 configure) |
| 源码 URL | https://github.com/EarthScope/libmseed/archive/refs/tags/v2.19.8.tar.gz |
| sha256 | 10ac972cb4e76c8d6aa27bf9f56fc59d1922991477d9ddefd375b89dba9e93f6 |
| 依赖 | 无 |
| 许可 | Apache-2.0 |
| 包类型 | library (cpp_info.libs=["mseed"]) |
| 上游仓库 | https://github.com/EarthScope/libmseed |

## 二、上游测试套件审计 (hmbs 机器证据门禁)
审计对象: 官方源码包 v2.19.8 (2026-09-16 下载验证,
sha256 与 GitHub tag 包一致, 大小 322524 字节)。

- 顶层 Makefile 定义 `test check: static`, 即 `make check` 先构建静态库再执行
  `make -C test test`。
- test/ 目录: 2 个 C 程序 (lmtestpack.c 打包测试, lmtestparse.c 解析测试,
  编译出可执行文件即通过) + 31 个 `*.test` shell 脚本
  (7 个 pack-*: Float32/Float64/Int16/Int32/Steim1/Steim2/text;
  24 个 read-*: CDSN/DWWSSN/Float32/Float64/GEOSCOPE163/Int16/
  Int32-1024/128/2048/256/4096/512/8192/SRO/Steim1-be/Steim1-le/
  Steim2-be/Steim2-le/detection-record/invalid-blockette-offset/
  mixed-order-mixed-length/no-blockette1000/text/unapplied-timecorrection)。
- 每个 `*.test` 有配套非空 `*.test.ref`; 测试机制为运行脚本、输出存
  `*.test.out`、diff 对照 `.ref`, 一致打印 PASSED, 不一致打印 FAILED。
- 无 ctest/gtest/pytest 框架; `make check` 即唯一官方入口。
- 证伪要点: 上游 `FAILED` 分支 `exit 0`, 不能看退出码, 必须数 PASSED/FAILED;
  `.ref` 非空已在配方 build() 中做前置校验, 空 fixture 对空参照的假通过会被拦截。

结论: 上游存在测试, 共 33 个用例 (2 构建 + 31 diff),
test_package/MANIFEST.yml 已声明 `upstream_test_in_build: true`,
配方 build() 真实运行 `make check` 并解析输出产生
`HMBS_UPSTREAM_TEST_RESULT` 证据。

## 三、补丁清单
| 补丁 | 内容 | 类型 |
|------|------|------|
| (无) | 零补丁: Makefile 的 CC/AR/RANLIB/SHELL 均为命令行可覆盖 | — |

补丁来源: 无需补丁。纯 Makefile 项目, 无 config.guess/config.sub
(非 autotools), 无生成文件修改 (R6), 无平台宏注入 (R8/PF5)。

## 四、配方要点 (conanfile.py)
- CC/AR/RANLIB 从 Conan conf (`tools.build:compiler_executables`) 获取 (R33),
  经 `make -j1 CC=... AR=... RANLIB=...` 命令行传入; SHELL 取 CONFIG_SHELL
  (回退 /data/service/hnp/bin/bash)。
- `static` 目标必构建; `shared` 目标仅在 `shared=True` 时构建
  (非系统同名库, 保留 .so, R26 不适用)。
- 上游测试: 单次 `make check` 经 subprocess 真实运行, 输出逐行进日志
  (满足 CI L1b/L1c 的 `make.*check` 与 PASSED 痕迹要求); PASSED/FAILED 计数
  来自真实输出, `executed < discovered` 或 `failed > 0` 直接判 failed 并抛异常。
- 双通道输出 (`print` + `self.output.info`) + 落盘
  `build_folder/upstream_test_result.json`, package() 转存
  `<package>/res/upstream_test_result.json`, test_package 逐轮重发
  (conan 缓存命中跳过 build() 时证据不丢失)。
- package(): 头文件 libmseed.h -> include/; libmseed.a 与 libmseed.so*
  -> lib/; mseed.pc 由 mseed.pc.in 生成 (prefix 重定位为
  `${pcfiledir}/../..`); LICENSE*/COPYING* -> licenses/。
- package_info(): libs=["mseed"], cmake_file_name/libmseed,
  cmake_target_name libmseed::libmseed, pkg_config_name mseed,
  PKG_CONFIG_PATH 同时进 buildenv/runenv。
- validate(): 仅允许 Linux/OHOS (R32 口径)。

## 五、test_package 设计 (R34)
- test_libmseed.c (6 项真实 API 检查, 非空壳):
  1. LIBMSEED_VERSION == "2.19.8";
  2. msr_init/msr_free 生命周期;
  3. mst_initgroup/mst_freegroup 生命周期;
  4. ms_time2hptime/ms_hptime2btime 往返 (2022/087 12:34:56.123456);
  5. ms_samplesize('i')==4 且 ('a')==1;
  6. ms_encodingstr(DE_STEIM2) 非空 + ms_genfactmult/ms_nomsamprate(100Hz) 往返。
- test() 经 `cmake.test()` + `self.run(test_libmseed)` 真实执行,
  `HMBS_TEST_PACKAGE_RESULT` discovered=6/passedCount=6 与 MANIFEST
  assertion_count=6 一致。

## 六、验证记录
- 本机: 源码下载 + sha256 校验通过 (322524 字节);
  上游文件结构 (Makefile/test/*.test/*.ref/mseed.pc.in) 已核对。
- 真机: 待 HMBS 预检 (conan create + test_package + 上游 33 用例门禁)。
- 预检通过后由 HMBS 统一提交、推送并创建 PR, 正文测试表以真机 evidence 为准。

### 真机预检轮次
- 第 1 轮 (2026-09-16, pending): 等待 HMBS 预检。配方已就绪:
  零补丁 Makefile 构建, 上游 `make check` 真实运行并计数,
  test_package 执行 6 个真实 API 检查。
  状态: 工作树未提交, 等待 HMBS 预检。
- 第 2 轮 (2026-09-16, failed/compile): 真机 `build()` 在 `_tool("ar")`
  处抛 `ConanException: [conf] 'tools.build:compiler_executables:ar'
  does not exist`。根因为 OHOS conan 不支持冒号子键语法, 修复为整
  dict 读取 (`self.conf.get("tools.build:compiler_executables",
  default={}, check_type=dict)` 后取键, 回退 clang/llvm-ar/llvm-ranlib),
  与 bzip2/zsv 已验证模式一致。readonly_tmp 平台诊断为 preflight.sh
  自身 /tmp 噪声, 配方/测试均未写 /tmp (产物落 build_folder/package),
  故不做替换。本轮仅改 conanfile.py `_tool`, 未提交, 待 HMBS 复检。
- 第 3 轮 (2026-09-16, failed/compile): 上一轮 conf 异常已消除, 新失败为
  `make: /data/service/hnp/bin/clang: No such file or directory`
  (profile 的绝对编译器路径在该 preflight worker 上不存在)。
  与上一轮"只读 dict"策略不同, 本轮给 `_tool` 增加存在性校验与可发现
  工具链回退: conf 绝对路径先验存在可执行, 缺失则告警并按
  PATH(clang/cc/gcc)、CC 环境、同编译器目录派生 llvm-ar/llvm-ranlib
  逐级回退, wrapper 脚本解析到同目录真 ELF。ar/ranlib 从已解析 cc 同
  目录优先派生, 其次 PATH 查找。本轮仅改 conanfile.py, 未提交,
  待 HMBS 复检。
- 第 4 轮 (2026-09-16, failed/test_package): 主包 build 已通过, 新失败在
  test_package 的 `cmake.configure()`:
  `CMAKE_C_COMPILER: /data/service/hnp/bin/clang` 不存在
  (CMakeToolchain 把 profile 绝对路径写入 toolchain, 另 CMake 4.4 无
  Platform/HarmonyOS 模块)。与前两轮"主包编译器发现"策略不同, 本轮按
  dhcpoptinj/0.5.3 经验改 test_package: 删除 CMakeDeps/CMakeToolchain
  与 cmake_layout/CMake 调用, 改用 VirtualRunEnv; build() 用 PATH 的
  clang 直接编译单文件 test_libmseed.c (按 dep.cpp_info 组装 -I/-L/-l),
  test() 直接执行该二进制。6 用例口径与 MANIFEST assertion_count=6 不变,
  上游证据重发逻辑不变。本轮仅改 test_package/conanfile.py, 未提交,
  待 HMBS 复检 (CI 轮)。
- 第 5 轮 (2026-09-16, CI #48558 编译失败): CI 在 `fileutils.o` 处报
  `clang-check: Unknown command line argument '-o'`。根因为 `_real_binary`
  的同目录前缀启发式把文本 wrapper `clang` 解析成同名前缀 ELF
  `clang-check` (排序紧随 clang 且 startswith 成立), CC 被错配成静态分析
  工具。修复为 wrapper 直接使用 (删除同目录替换), 另对 c 编译器加
  clang-check/tidy/format 否决与 build() fail-fast。本轮仅改 conanfile.py,
  未提交, 待 HMBS 预检/CI 复检。

## 七、遗留问题
- test/*.test 脚本 shebang 为 `#!/bin/sh`; 若真机 /bin/sh 缺失导致
  ENOENT, 下一轮改用 SHELL 显式调用或最小补丁修复 (本轮未假设, 等预检证据)。
- 上游 `install` 目标引用未定义的 `$(LIB_SO_NAME)` 且捆绑文档/示例安装,
  本配方未复用上游 install, 改为精确 copy + 自生成 mseed.pc。
