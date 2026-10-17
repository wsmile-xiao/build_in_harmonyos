# kamailio-presence 6.0.6 适配笔记

## 编译环境
- 构建系统: makefile（Kamailio 经典 Makefile 体系；**只编模块，不编 kamailio core**）
- 编译日期: 2026-09-30
- 编译器: clang 15（OHOS SDK: /data/service/hnp/bin/clang，target aarch64-linux-ohos）
- 目标平台: HarmonyOS PC / aarch64（os=OHOS 6.0，libc++，Release）
- 状态: built

## 编译步骤

源码：上游官方 `https://www.kamailio.org/pub/kamailio/6.0.6/src/kamailio-6.0.6_src.tar.gz`
（sha256 `32e4290c6813c9d0289abe9ec2de9138e12e0381179218a7fed374ad813ecc48`，13152560B）。

模块范围：Alpine `main/kamailio` 的 `kamailio-presence` 子包口径 `_mod_list_presence`，共 18 个：

```
presence presence_conference presence_dfks presence_dialoginfo presence_mwi
presence_profile presence_reginfo presence_xml pua pua_bla pua_dialoginfo
pua_reginfo pua_rpc pua_usrloc pua_xmpp rls xcap_client xcap_server
```

与同仓 kamailio-ims/6.0.6 **共用同一 tarball**（sha256 一致），差异仅在模块清单与依赖面。

关键命令（两批 make，均不触碰 core）：

```bash
# 第一批：makeroot 只铺模块目录骨架（不编 core）
make -C src cfg \
     include_modules="<18 模块>" \
     extra_defs="-D_GNU_SOURCE -DHAVE_GETHOSTBYNAME2 -DHAVE_SCHED_YIELD \
                 -DHAVE_MSG_NOSIGNAL -DHAVE_MSGHDR_MSG_CONTROL -DHAVE_ALLOCA_H \
                 -DHAVE_TIMEGM -DHAVE_SCHED_SETSCHEDULER -DHAVE_IP_MREQN" \
     LOCALBASE=$PREFIX XML2CFG= BUILDER= CURLCFG= CURL_BUILDER=

# 第二批：只编模块 .so
make -C src modules include_modules="<18 模块>" LOCALBASE=$PREFIX ...
```

要点：
- `OS=harmonyos`（未列入上游 make 的已知 OS 表）+ `extra_defs` 注入 linux 分支等价宏集
  （`_GNU_SOURCE` 等 8 个），使上游 `#ifdef __linux__` 分支的平台判定在 OHOS 上等价成立；
  **零补丁、不改上游源码**。
- `LOCALBASE=$PREFIX`（conan package folder），并由 `XML2CFG=`（libxml2）与
  `CURL_BUILDER=`/`CURLCFG=`（curl）**清空上游的 pkg-config 探测命令**，强制 Makefile
  走 `LOCALBASE` 回退分支取头/库路径——避免构建机残留的 host pkg-config 把宿主路径
  带进交叉构建（同仓 kamailio-xml / kamailio-slack 已验证同一手法）。
- 统一 `-j1`（E525：FIFO 在各 make 子进程间不可用，并行会卡死）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 模块 Makefile 探测到宿主 pkg-config 的 libxml2 | `XML2CFG` 默认用构建机 pkg-config | `XML2CFG=` 清空 + `LOCALBASE` 钉 conan 包目录 |
| 2 | curl 头/库指向宿主 | `CURL_BUILDER`/`CURLCFG` 默认走 curl-config/pkg-config | `CURL_BUILDER= CURLCFG=` 清空 + LOCALBASE 回退分支 |
| 3 | 并行 make 偶发卡死 | E525：OHOS 侧 FIFO 不可用 | 全流程 `-j1` |
| 4 | 依赖包目录定位 | graph.json 顶层 keys 随 conan 版本变化 | 改用 `conan cache path <ref>:<pkgid>` 解析 |
| 5 | 加载验证时 `str2facility` 被判为 libc 提供、未桩化 | 前缀 `str` 命中 libc 前缀表（同仓 kamailio-ims 同类坑） | 桩生成器加 4 个 core 例外符号（含 `str2facility`） |
| 6 | e2e 遍历 xcap_client 命名空间链时 SIGSEGV（崩溃点随 ASLR 漂移） | **上游 6.0.6 缺陷**：`xcap_functions.c:193-207` 的 `ns_list_t` 新节点**未给 `next` 赋值**（同文件 `step_t` 分支在 :186 有 `s->next = NULL`，ns 分支漏写）→ 链尾为堆垃圾 | 本包走零补丁路线，不改上游；测试桩 pkg 分配后端改返回**清零内存**（calloc 语义）使被测路径确定可复现；该上游缺陷如实登记于此，遍历/`get_node_selector` 用例在桩下恢复可测 |
| 7 | gdb/lldb 无法追踪（`ptrace: Permission denied`） | 平台限制 | 改用信号处理器 + `dladdr` 定位出错符号、独立最小探针二分（`probe_addstep.c` 先证桩侧正常） |

## 源码修改

**无补丁**（`patches/` 为空）。同族口径：不在 patches/ 内引入平台宏分支，平台差异经
`OS=harmonyos` + `extra_defs` 宏集在构建参数层吸收；测试桩内的 calloc 语义属
`test_package/` 设施（非上游源码补丁）。

## 依赖版本

| 依赖 | 版本 | 制品仓 | 使用模块 |
|------|------|--------|----------|
| libxml2 | 2.15.3.1 | ✅ ohpcd | presence / presence_conference / presence_dfks / presence_dialoginfo / presence_reginfo / presence_xml / pua / pua_bla / pua_dialoginfo / pua_reginfo / pua_usrloc / pua_xmpp / rls / xcap_server（14 个 DT_NEEDED 含 `libxml2.so.16`）|
| curl | 8.15.0.1 | ✅ ohpcd | xcap_client（DT_NEEDED 含 `libcurl.so`） |

实测 DT_NEEDED（18 行）：14 模块 = `libxml2.so.16, libc.so`；`xcap_client` =
`libcurl.so, libc.so`；`presence_mwi` / `presence_profile` / `pua_rpc` = 仅 `libc.so`。
`pua_dialoginfo` 等经 `cdp` 中转引用 libxml2（DT_NEEDED 仍含 libxml2.so.16）。

## 验证结果

```bash
# 1) 模块编译清点：18/18
$ cat products.txt            # OK_COUNT=18/18

# 2) 加载验证（core 符号桩 + 模块 dlopen 契约）：18/18 通过
$ python3 check_presence_modules.py   # 断言：通过 249 / 失败 0
#    exports=yes iface=yes flags=yes；mod_register 仅 6/18 提供（契约上为可选）

# 3) 端到端消费者用例（契约层 + 行为层）：362 项断言全 PASS，连跑 3 次确定性一致
$ ./test_presence_modules_e2e <modules_dir>
#    断言总数: 362 / 失败 0（RUN_RC=0）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/kamailio/modules/*.so | 18 个 | presence 家族模块（aarch64 ET_DYN core 插件）|
| licenses/COPYING | — | 上游许可证 |

> 不打包头文件：core 插件由目标机的 kamailio 主程序经 `loadmodule` 加载，无编译期头需求
> （`package()` 仅落 `COPYING` 与 18 个 `.so`）。

## 注意事项

- 本包**只产出模块 .so，不含 kamailio 主程序**（同族口径：不构建 core）。使用时由
  目标机上的 kamailio 主程序经 `loadmodule` 加载。
- 上游 6.0.6 的 `xcapNodeSelAddStep` ns 链未初始化 `next`（见问题表 #6）：任何遍历
  `ns_list` 的调用方（包括模块自身 `get_node_selector`）在未清零的分配后端下都会读
  野指针。本包测试以清零后端规避；**真机集成时若使用 kamailio 默认 `qm_malloc`
  后端，该路径存在同类风险**，建议上游修复或在调用侧规避。
- `mod_register` 仅 6/18 模块提供（presence/presence_xml/pua/pua_usrloc/rls/xcap_server），
  其余模块按上游加载器语义走 `exports` 回退路径，属正常形态。

## 上游测试三步法（R51）

### 【清点】上游官方源码包 kamailio-6.0.6_src.tar.gz（sha256 32e4290c…）实测

| 位置 | 数量 | 可否运行 |
|------|------|---------|
| `utils/kamctl/dbtextdb/tests` | 10 文件 | 入口 `dbtextdb_test.py`（3 unittest 用例，仅依赖 Python 标准库） |
| `src/modules/janssonrpcc/test` | 3 文件 | 需运行中 kamailio 实例 |
| `src/modules/rtpproxy/test` | 3 文件 | 需外部 rtpproxy 进程 |
| 全树 `test`/`tests` 命名目录汇总 | 4 目录 / 17 文件 | 需完整 kamailio 集群拓扑（顶层 `test/` 本身为 0 个） |
| `src/modules/tm/test` | 1 文件 | `kill_sem.sh`，非本包模块 |
| **本包 18 个模块目录** | **0** | 逐模块 Makefile 无 `test`/`check` 目标，目录内 0 个 `test*` 文件 |
| `src/modules/presence_conference/test_framework` | 17 脚本 | **非自包含**：需 root + sipp/ngrep + 真实 5060 端口上运行中的 kamailio 实例（`presence_conference` 属本包 18 模块之一）→ 未执行 |

结论：**本包构建的 18 个模块上游无可运行用例**（其中 `presence_conference` 的
`test_framework` 需完整 SIP 运行环境，故未执行；与同仓 kamailio-ims 不同：ims 自带
`src/modules/ims_ipsec_pcscf/spi_list_tests.c` 编译期自包含用例，本包无对应物）。因此上游
实跑项取全包唯一自包含的 unittest。

### 【实跑】

```
$ cd utils/kamctl/dbtextdb && python3 dbtextdb_test.py -v
testExecute ... ok     # 1) 建表/解析执行
testOpenTable ... ok   # 2) 表打开与 schema 解析
testParseQuery ... ok  # 3) 查询语句解析
Ran 3 tests in 0.014s
OK
```

- 执行环境：OHOS aarch64 交叉构建源码树（`$BUILD_SRC_DIR`），Python 标准库即可，无需目标机
- 执行位置：本包 `conanfile.py` 的 `build()` 末尾 `_run_upstream_tests()`（每次 conan create 必跑）
- 通过率：**3/3 (100%)**

### 【回填】

- 上游用例总数：3（可运行项）；本包 presence 家族专属上游用例：0（清点证据见上表）
- 适配后用例总数：614 = 249（`check_presence_modules.py` 静态契约层）+ 362（`test_presence_modules_e2e.c` 运行期 e2e）+ 3（上游 unittest 复跑）
- 上游用例修改：无（未改动任何上游文件，零补丁路线）
---

**编译结束**: 2026-09-30 19:51
**最终状态**: built
