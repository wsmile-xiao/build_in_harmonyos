# osip 5.3.2 适配笔记（GLM-32，2026-09-15 夜跑）

## 编译环境

- 构建系统: autotools（release tarball 自带 configure，无需 autoreconf）
- 编译日期: 2026-09-15
- 编译器: clang/clang++（OHOS 15.0.4，aarch64）
- 状态: built（conan-verify G1/G2/G0/G3/G4 全部通过，见 reports/conan-verify-report.md）
- Conan 2.29.1（OHOS 适配版），profile ci/conan/profiles/ohos-aarch64

## 编译步骤（探索阶段实测，最终固化为配方）

```bash
# 关键 configure 参数（由 AutotoolsToolchain 注入 + 配方显式添加）
./configure --prefix=<pkg> \
  --enable-static --disable-shared \
  --build=aarch64-unknown-linux-gnu \
  --host=aarch64-unknown-linux-ohos \
  --enable-test
make -j1
make check                 # 空转（上游无 TESTS 注册）
make -C src/test           # --enable-test 后 noinst_PROGRAMS 构建 torture 工具
./torture_test res/torture_hgs    # 42 条 OK
./torture_test res/torture_msgs2  # 93 条 OK
./tst res -c                      # 122 条 OK（sip0-98 + sip-malformed0-22）
```

## 踩坑与解决（时间线）

1. **`cannot guess build type`**：上游 scripts/config.guess 为 2014 版，
   uname 输出 `HarmonyOS`/`HongMeng Kernel` 无法识别。解决：升级到 GNU
   config 新版 config.guess/config.sub，并给 config.sub 补 `linux-ohos*`
   与 `ohos*` 条目（python 精确替换，固化为 0002/0003 补丁）。参考先例
   aalib/1.4p5（0001-config.sub-ohos.patch 同模式）。
2. **`can't create ./confXXXXXX/subs1.awk: Permission denied`**（E011）：
   config.status 的 umask 077 临时目录在 HMDFS 上不可写。解决：configure 内
   `umask 077`→`022`（0001 补丁，a52dec 同型）。
3. **HMDFS FUSE getcwd 间歇故障**：设备内存压力时段（MemFree<1000MB）HMDFS
   对 getcwd 系统调用返回失败（"Not supported"/"Bad file descriptor"），
   导致 conan create 内 bash shell-init 报错、configure 的 ac_pwd 解析失败。
   属环境时间窗问题（同窗内 osip 探索构建、aalib 先例均可复现成功）；等
   gate/MemFree 恢复后重试即过。知识 E386（noexec 构建树 shell 探测）同族。
   处置：构建前过 ~/tmp/uc2/gate.sh，失败择窗重试。
4. **`cannot guess build type` 在配方阶段复发**：AutotoolsToolchain 不会
   自动注入 OHOS build/host triplets（aalib 归档注释同证）。解决：generate()
   显式追加 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`。
5. **make check 在 out-of-source 构建下 Error 127**：上游 src/test/Makefile.am
   的 check 目标写死 `./$(top_srcdir)/src/test/tst`，top_srcdir 为绝对路径时
   `./` 前缀拼出无效相对路径。解决：去除 `./` 前缀（0004 补丁，+2/-2），
   测试逻辑零改动。修复后 tst 驱动在 conan create 内真实执行 122 条全过。
6. **test_package Call-ID 断言失败**：osip 将 `Call-ID: <number>@<host>` 拆为
   number 与 host 两个字段，消费者测试断言需分别比较（首版断言整串失败后
   修正）。

## 上游测试四维账本（与 manifest.yaml / PR 正文 / test_package/MANIFEST.yml 同源）

| 维度 | 数值 | 说明 |
|------|------|------|
| N_static（静态注册） | 0 | 全树无 TESTS 变量；src/test 测试程序为 COMPILE_TESTS 条件下的 noinst_PROGRAMS；`make check` 实测空转 |
| N_executed（实际执行） | 257 | tst 驱动 122（sip0-98、sip-malformed0-22，passed 122/failed 0，其中 sip-malformed22 为预期失败样例 expected=-5）+ torture_hgs 42 + torture_msgs2 93 |
| 跳过/未执行 | 0 | torture_sdps 为纯 SDP 样例数据，非 torture_test 的 SIP 消息输入格式，不构成有效测试输入（喂入会因缺少 SIP start-line 报 FAILED），已在 PR 正文说明 |
| N_consumer（新增消费者） | 1 | test_package/test_osip：真实 API 解析 INVITE + 6 项字段断言，1/1 通过 |

## 路径 B 判断

判断不成立，按纯路径 A 申报。依据：本次遇到的三个主要问题（config.sub ohos
支持、umask 077、out-of-source check 路径）在知识库/归档中已有成熟方案
（E011、E386、aalib/1.4p5、a52dec/0.7.4 先例），本次为既有知识的组合应用，
无跨仓库复用的新知识增量；查重未发现可沉淀的新错误签名。

## 遗留与限制

- 上游 platform/vsnet（VS 工程）与 help/ 手册不在适配范围
- make check 无注册用例为上游事实（如实申报），配方 build() 已集成上游
  测试资产的真实执行
---

**编译结束**: 2026-09-15 04:30
**最终状态**: built
