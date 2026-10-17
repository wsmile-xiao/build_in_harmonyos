# input-utils 1.3 适配笔记

## 编译环境
- 构建系统: makefile (GNUmakefile + mk/*.mk, 无 configure)
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 上游清点（R51）
- 官方 tarball: https://www.kraxel.org/releases/input/input-1.3.tar.gz (kraxel.org 发布索引 HTTP 200, 2025-05-30, 最高版本 1.3)
- sha256: 9142c34d508f2da4cd53d6348fee77e30b69c35c8dabfadfc5a6db09c4bd8087
- 上游测试: 0 项。证据: tarball 无 tests/ 目录; GNUmakefile 目标仅 all/install/clean/realclean/distclean (无 check/test); mk/*.mk 无测试基础设施; 上游无 CI workflow 配置。NO_TESTS 结论基于官方源码全量文件清单 (reports/upstream-filelist.txt)。

## 编译步骤

    export OHOS_INPUT_CODES=<ohos-sdk sysroot>/usr/include/linux/input-event-codes.h
    export OHOS_INPUT_BUS_CODES=<ohos-sdk sysroot>/usr/include/linux/input.h
    make CC=clang -j1

补丁 0001 使 name.sh/lirc.sh 支持 OHOS_INPUT_CODES / OHOS_INPUT_BUS_CODES 环境变量: OHOS 设备无 /usr/include (musl sysroot 位于 ohos-sdk native/sysroot/usr/include), 而这两个脚本硬编码从 /usr/include/linux/*.h 读取事件码定义生成 EV/KEY/BUS 等头文件与 lircd.conf。环境变量未设置时回退上游原逻辑, 不破坏其他平台。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | name.sh 报 cannot open /usr/include/linux/input.h | OHOS 无 /usr/include; sysroot 在 ohos-sdk 下 | name.sh/lirc.sh 支持 OHOS_INPUT_CODES/OHOS_INPUT_BUS_CODES 注入 (补丁 0001) |
| 2 | BUS.h 为空 | BUS_* 宏不在 input-event-codes.h, 而在 input.h | name.sh 对 BUS 类型使用 OHOS_INPUT_BUS_CODES (input.h) |
| 3 | make install: No such file or directory | OHOS 设备无 install(1) 工具 | 打包改由 Conan recipe package() 用 copy() 完成等价文件集; 验证阶段用 busybox install 做 DESTDIR 装载 |
| 4 | BTN_TRIGGER_HAPPY / SW_RADIO 初始化覆盖告警 | 上游生成头文件对别名宏重复定义, 上游已知行为 | 不修改 (仅 -Winitializer-overrides 告警, 不影响产物) |
| 5 | 官方 CI L0c no_test_sources (round-15 返工) | 候选 tree 的 test_package/ 只有 conanfile.py + MANIFEST.yml (纯脚本型消费者, 无 .sh/.c 源文件)。本地 round-14 CI 因目录残留 conan 生成的 conan*env*.sh 而被 L0c 的 find -name "*.sh" 误判为有测试源, 官方 CI 在干净 checkout 上找不到 → 门禁 fail | 新增真实测试源 test_package/test.sh (L0c 认可扩展名), conanfile.py test() 经 conanrun env 用 bash 真实执行 test.sh; 断言数 4→5 |

## 源码修改

- patches/0001-name-lirc-ohos-input-codes.patch: name.sh, lirc.sh 各增加 OHOS 环境变量头文件路径支持; 无平台宏 (纯 shell env 分支), 未设置变量时与上游行为完全一致。

## 依赖版本

- clang 15.0.4, GNU Make 4.4.1; 无第三方库依赖 (仅 libc + linux-input uapi 头)。

## 验证结果

> 口径澄清: 「busybox install DESTDIR」一行为历史手动验证记录（复制上游 GNUmakefile install 的目标布局）；Conan recipe package() 的实际交付产物为 bin/ 6 工具 + share/input-utils/lircd.conf + share/man/man8/ 3 页手册（copy *.man）+ licenses/COPYING，两套口径不应混读。另: input-recv 未纳入 test_package（其监听/连接路径需网络栈交互），仅在本地验证阶段单独运行。

    make CC=clang -j1          # 6 个工具全部链接成功
    ./lsinput                  # exit 0 (设备无 /dev/input 读取权限, 空扫描)
    ./input-events             # usage 提示, exit 非 0
    ./input-kbd                # usage 提示
    ./input-send               # usage 提示
    ./input-recv <port>        # 正常进入监听/连接错误路径 (网络栈可用)
    ./emulate-key              # usage 提示
    busybox install DESTDIR    # bin 5 工具 + man8 3 页全部安装
    lircd.conf                 # 617 行正确生成

### round-15 L0c 返工

- 官方 CI (AtomGit buildbot, build_and_test.sh, profile ohos-aarch64) 对 PR #12966 执行 L0 门禁返回 `[fail] L0c: No test source files in test_package/` → `no_test_sources` → `L0_RESULT=fail`, L1/L2/L4/L5 全 blocked_by_L0。
- L0c 实际规则 (ci/conan/build_and_test.sh, test_package 内 `find -maxdepth 2 -name ".*ext" -not -name conanfile.py`, 扩展名 c/cpp/cc/cxx/sh/py 任一命中即过; docs/TEST_QUALITY_SPEC.md §5.1)。
- 返工: 参考同类 application/tool 库先例 (i/icon/9.5.25a、i/idutils/4.6 — test.sh + conanfile.py `self.run("bash test.sh", env="conanrun")`; i/i2util/1.2 — CMakeLists + test.c), 新增真实测试源 `test_package/test.sh` 并在 `test_package/conanfile.py` test() 中真实执行, 断言数 4→5。
- test.sh 5 条断言均针对打包产物 ELF 真实行为: ①lsinput 空扫描 exit 0; ②input-events 9999 须把参数格式化为 /dev/input/event9999 并在 stderr 报告 open 失败 (上游 main 无条件 return 0, 按源码口径断言错误信息而非退出码); ③emulate-key 无 keyname usage 被拒 (exit 非 0); ④input-send 无 device usage 被拒 (exit 非 0); ⑤lsinput 若列出设备则输出须引用 /dev/input (CI 无设备则为有效空结果)。test.sh 经 conanrun env 的 VirtualRunEnv PATH 解析工具, 非硬编码 pass。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2.x 配方 (package_type=application, copy 打包) |
| conandata.yml | 官方 URL + sha256 + 1 个补丁 |
| patches/0001-name-lirc-ohos-input-codes.patch | name.sh/lirc.sh OHOS 头文件路径注入 |
| test_package/conanfile.py | 消费者测试入口, test() 真实执行 test.sh (conanrun env) |
| test_package/test.sh | 真实测试源 (L0c 认可 .sh), 5 条断言针对打包工具行为 |
| test_package/MANIFEST.yml | 上游测试声明 (upstream 0 项) + test_package 测试清单, assertion_count=5 |
| commands.json (软件级) | R38 可执行文件声明 |

## 注意事项

- lircd.conf 归档在 prefix/share/input-utils/lircd.conf (上游默认生成于源码根目录, 无安装规则)。
- lsinput/input-kbd 需要真实 /dev/input 设备节点才能产生完整输出; test_package 仅验证可执行性 + usage/错误路径, 不伪造设备测试。

## 三级 sysroot 获取契约（round-19 官方 CI L1 回退修复）

- 官方 buildbot 环境不导出 OHOS_SDK_SYSROOT / OHOS_SDK_NATIVE（ci/conan/ 全目录 grep 零命中；官方 CI 调用形态为 CI_PACKAGES / CI_BRANCH / CI_PR_NUMBER / CI_REPO_ROOT / CI_USE_NSPAWN=0 / CONAN_PROFILE=ohos-aarch64 等，无手工 sysroot 注入）。官方入口模拟（reports/builder/official-entry-sim.md Run A）精确复现：name.sh[27] can't open /usr/include/linux/input.h → 官方 L1 必挂。
- 修复：build() 在 env 两级均缺失时新增第三级回退——取 profile 已声明的 cc（tools.build:compiler_executables 整体键查询 + isinstance(dict) 守卫；若无则 shutil.which("clang")/which("cc") 依序兜底），探测 sysroot 并注入 OHOS_INPUT_CODES / OHOS_INPUT_BUS_CODES：
  1. `<cc> -print-sysroot`（clang 16+ / gcc 支持）；
  2. 设备 clang 15.0.4 不支持该 flag，回退 `<cc> -print-file-name=include` 取资源 include 目录，逐级向上（最多 8 级）查找兄弟 `sysroot/`，且仅当 `<sysroot>/usr/include/linux/input-event-codes.h` 实际存在才采纳。
- 探测成功输出 conan info 行 "OHOS sysroot auto-detected via <cc>: <path>"；失败保持原行为（name.sh 走上游 /usr/include 默认）并输出 info 日志。env 优先级不变：OHOS_SDK_SYSROOT / OHOS_SDK_NATIVE 设置时行为与修复前完全一致（Run B 口径双跑验证 rc=0）。无任何设备私有路径硬编码；ci/ 文件未改动。
