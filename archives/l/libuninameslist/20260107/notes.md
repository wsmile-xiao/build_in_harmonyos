# libuninameslist 20260107 适配笔记

任务：7358（开源鸿蒙PC专项积分赛-依赖，声明语言 c）｜分支 feat/libuninameslist-20260107

## 编译环境

- 构建系统: autotools（dist tarball 自带 configure，无需 autoreconf）
- 编译日期: 2026-09-12/13
- 编译器: clang（OHOS aarch64，profile clang 15 / libc++ / Release）
- 状态: built（真机 conan create + test_package 通过）

## 编译步骤

1. 探索构建（上游测试证据，设备本机）：
   `./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu --disable-shared --enable-static CFLAGS="-O1" && make -j1`
   - 老 config.guess 不识别 HarmonyOS 主机（`cannot guess build type`），显式指定三元组解决。
   - configure 生成 config.status 时报 `can't create ./confXXXX/subs1.awk: Permission denied`（HMDFS setgid 临时目录，知识 E126/E011）→ 受控修改 configure 中 2 处 `umask 077`→`umask 022`，经 refresh-patch --auto 固化为 patches/0001-configure.patch。
   - 签名执行上游测试：`binary-sign-tool sign -selfSign 1` 后运行 call-test0/1/2/6。
2. 配方验证：`ohc-run.py conan-verify libuninameslist 20260107`（conan create 全量门禁，见下方验证结果）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cannot guess build type` | 老 config.guess 不认识 HongMeng/HarmonyOS 主机 | 显式 `--build/--host` 三元组（手动构建场景；配方路径由 conan toolchain 注入，不受影响） |
| 2 | `can't create ./confXXXX/subs1.awk: Permission denied` | HMDFS setgid 目录使 umask 077 创建的临时目录不可写（E126/E011） | 受控补丁 umask 077→022（patches/0001-configure.patch，refresh-patch --auto 生成） |
| 3 | lang-preflight 判定 `detected=mixed → env_unsupported`（两次误写终态） | 探测器递归发现 `py/setup.py`（EXTRA_DIST 中可选 Python 绑定，configure 默认 `ENABLE_PYLIB=no` 不构建），manifest 探针误报 python，与源码统计 c:86%（12/14）冲突判 mixed | 误判：任务声明语言 c = 源码主语言 c，构建系统 autotools；按 R47 边界规则"辅助脚本不算主体"继续 C 库适配。两次误写的 `$HOME/ohpcd-ai-worker-result.json` env_unsupported 终态已核实为本任务自产后删除；本条留档为完整证据 |

## 源码修改

- patches/0001-configure.patch：configure 中 2 处 `umask 077`→`umask 022`（config.status 临时目录），无平台宏。

## 依赖版本

无外部依赖（零依赖库）。

## 验证结果

上游测试四维账本（tag 20260107 源码静态统计 + 设备实跑）：

| 维度 | 数值 | 说明 |
|------|------|------|
| 上游静态注册数 N_static | 4 | tests/Makefile.am `noinst_PROGRAMS`：call-test0/1/2/6（WANTLIBOFR 默认关闭，无 call-test3/4/5/7）；上游未注册 make check 的 TESTS 自动运行 |
| 实际执行 N_executed | 4 | 设备签名后全部实跑 |
| 通过 / 失败 / 跳过 | 4 / 0 / 0 | rc=0（call-test1 输出 `Nameslist-Version: 17.0`；call-test2 输出 blockCount=360） |
| 未执行分类 | 0 | 无 |
| 新增消费者测试 N_consumer | 1 | test_package/test.c：uniNamesList_name/annot/blockCount/blockNumber/NamesListVersion 断言（5 个断言分支） |

上游测试断言计数（近似）：23 个测试点（17 个 `test code=` 查询点 + version/blockCount 等校验输出）；消费者测试 5 个断言分支，合计近似 28。

## 路径 B 判断

不走路径 B：本轮命中知识 E126/E011（已有条目，使用记录见上），无跨仓库复用的新知识增量；lang-preflight 误判属框架探测行为，已留档并同步 SKILL_FEEDBACK，不作为适配知识申报。

## 注意事项

- 上游 `py/` 为可选 Python 绑定（默认不构建），勿因 setup.py 误判语言。
- `fr` 法语库（WANTLIBOFR）默认关闭，如启用需同步扩展消费者测试。
---

**编译结束**: 2026-09-13 02:50
**最终状态**: built
