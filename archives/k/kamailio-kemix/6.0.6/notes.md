# kamailio-kemix 6.0.6 适配笔记

## 一、基本信息

| 项 | 值 |
|----|----|
| 上游 | kamailio 6.0.6 |
| 源码 | https://www.kamailio.org/pub/kamailio/6.0.6/src/kamailio-6.0.6_src.tar.gz |
| sha256 | `32e4290c6813c9d0289abe9ec2de9138e12e0381179218a7fed374ad813ecc48` |
| 构建体系 | kamailio 经典 Makefile 体系（src/Makefile + Makefile.defs + Makefile.modules） |
| 打包产物 | `kemix.so`（KEMI 扩展模块） |
| 平台目标 | OHOS / aarch64（SDK clang 默认 target 即 aarch64-unknown-linux-ohos） |
| 依赖 | 无（模块 Makefile `LIBS=` 为空，仅引用 kamailio core 符号） |
| 模块性质 | 纯 core 插件：`exports` 描述符零导出，功能经 `mod_register()` 注册 |

## 二、打包口径

- 取官方全量源码包构建，**仅编译打包 kemix 模块**，不依赖 kamailio 本体包。
- 模块 `.so` 由 kamailio 运行时 `loadmodule "kemix.so"` 加载，不作为链接库供消费者使用
  （`cpp_info.libs` 为空，仅声明 `lib/kamailio/modules` 模块目录）。
- 无命令行可执行文件 → **不创建 commands.json**（R38 仅命令行工具需要）。

## 三、构建要点与踩坑

1. 上游同时提供 CMake 与经典 Makefile 两套体系；本配方走经典 Makefile：
   ```
   make cfg include_modules=kemix                 # 生成 src/config.mak，探测 aarch64-unknown-linux-ohos
   make modules modules=modules/kemix -j1         # 产出 src/modules/kemix/kemix.so
   ```
2. **与同族模块的差异点：kemix 无第三方依赖**。`src/modules/kemix/Makefile` 为
   `NAME=kemix.so` / `LIBS=`（空），不含 `LOCALBASE`/`ODBCCFG`（unixodbc）或
   `BUILDER`（snmpstats）一类外部库探测分支，故配方只需注入 `CC`，
   无需传任何 make 变量钉死探测分支，也不涉及 R49 共享前缀注入。
3. 依赖注入只走 `Environment`（`CC`）+ 相对源码树路径，未向任何共享系统前缀写入路径（R49 口径）。
4. `make cfg` 依赖 `src/config.mak`；模块构建必须在其之后，否则报
   `No rule to make target 'cfg-defs'` / `Makefile.cfg: config.mak: No such file or directory`。
5. 本地探索期环境问题（与配方无关，同 unixodbc/snmpstats）：init-build 从 kamailio.org 的断点下载
   被工具超时中断；复用**同源同 sha256** 的已缓存 tarball（`sha256sum` 复核一致）后正常。
6. **KEMI/core ABI 两处易错点（e2e 用例实测纠正，勿凭文档猜）**：
   - kamailio 6.0.6 的 `DEFAULT_DLFLAGS` 是**哨兵值 0**（`src/core/sr_module.h:188`，注释原文
     “value that signals to module loader to use default dlopen flags in Kamailio”），并非
     `RTLD_NOW|RTLD_GLOBAL`；故对 `exports.dlflags` 应断言 `== 0`（初版按其他版本印象写成 `!= 0`，
     本地首跑即失败）。
   - `sr_kemi_t` 字段序为 `{str mname; str fname; int rtype; void *func; int ptypes[SR_KEMI_PARAMS_MAX=6];}`
     —— **`func` 先于 `ptypes`**（src/core/kemi.h）。结构体布局若按错误顺序定义，虽然
     `mname/fname` 偏移仍对（前 32 字节），但 `func` 读取会整体错位。
7. **KEMI 表返回类型不是单一 XVAL**：`sr_kemi_kx_exports` 69 项实测分布
   `SR_KEMIP_XVAL=57 / SR_KEMIP_INT=10 / SR_KEMIP_BOOL=2`——INT 10 项为
   `get_send_sock_port/get_protoid/get_status/get_bodylen/get_timestamp/get_conid/get_msglen/get_msgtype/get_defn/get_envn`，
   BOOL 2 项为 `ifdef/ifndef`，另有 6 项含 `SR_KEMIP_STR` 参数。`SR_KEMIP_*` 常量须照
   `src/core/kemi.h:31-39` 原值定义（NONE=0 / INT=1 / STR=2 / BOOL=4 / LONG=8 / XVAL=16 / NULL=32）。
8. **core 符号桩规模**：kemix.so 独立 dlopen 时未定义符号 45 个（其中 33 个为 core 符号，含
   KEMI 注册/sr_kemi_xval_null/SIP 解析器/dprint 等），桩层 `kamailio_core_stub.c` 逐符号给出
   同语义最小实现（`sr_kemi_modules_add` 记录函数表供用例观察），随 e2e 一次 clang 调用编译。

## 四、上游测试清点与真实执行（R51 三步法）

### 1. 清点（源码包文档级全量清点，N=17）

`kamailio-6.0.6_src.tar.gz` 内 `test/`、`tests/` 目录共 **4 个、文件共 17 个**（与同族两个子包同源同口径）：

| 组 | 文件（源码包内路径） | 所属 | 角色 | 可独立执行 |
|---|---------------------|------|------|-----------|
| 1–10 | `utils/kamctl/dbtextdb/tests/{bad_table_*,unsorted_table*,subscriber,test}` | kamctl dbtextdb | unittest 用例数据（无执行位） | 否（由 11 号脚本消费） |
| 11 | `src/modules/janssonrpcc/test/run-tests.sh` | janssonrpcc | jsonrpc-c 冒烟脚本 | 否（需同树构建的 kamailio 主程序） |
| 12 | `src/modules/janssonrpcc/test/mem-test.sh` | janssonrpcc | valgrind 泄漏检查 | 否（需 kamailio 主程序 + valgrind） |
| 13 | `src/modules/janssonrpcc/test/test.cfg` | janssonrpcc | 上述脚本用配置 | 否（配置文件） |
| 14 | `src/modules/rtpproxy/test/kamailio.cfg` | rtpproxy | 手工联调配置样例 | 否（配置文件） |
| 15 | `src/modules/rtpproxy/test/exec_rtpproxy.txt` | rtpproxy | 启动命令行记录 | 否（无执行位、无断言） |
| 16 | `src/modules/rtpproxy/test/exec_pjsua.txt` | rtpproxy | 客户端命令行记录 | 否（无执行位、无断言） |
| 17 | `src/modules/tm/test/kill_sem.sh` | tm | 开发期 IPC 清理脚本 | 否（需 root，`ipcrm` 会删除宿主全部 SysV IPC） |

清点命令（可复现）：

```bash
tar tzf kamailio-6.0.6_src.tar.gz | grep -E '/(test|tests)/' | grep -v '/$' | wc -l   # → 17
```

补充：**`src/modules/kemix/` 内无任何测试文件**（仅 `kemix_mod.c`、`doc/`、`README`、`Makefile`、
`CMakeLists.txt`），无 check/ctest 目标注册。上游 git 仓库另有 `test/unit/` 冒烟套件
（需 sipp/sipsak + 运行中的 kamailio 实例），**不随官方发布包分发**，不计入发布包清点面。

### 2. 运行（真实执行，层 1 门禁，`conanfile.py` build() 末尾）

17 个文件中唯一自包含、无需运行中 kamailio 实例的上游测试是
`utils/kamctl/dbtextdb/dbtextdb_test.py`（上游自带 unittest 入口，3 个用例，
仅依赖 Python 标准库），已在本包 build() 末尾真实执行，退出码 0（非零即构建失败）。

### 3. 回填

- 上游台账：清点 N=17、实测执行 N′=3、通过率 3/3、未执行 14（逐项技术原因登记在
  `test_package/MANIFEST.yml` 的 `upstream_tests[].not_executed_reason`，非"无环境"一句豁免）
- 本包另有 `test_package/check_kemix.py` 产物结构断言 + `test_kemix_e2e` 鸿蒙端到端消费者用例，
  作为消费者视角（层 2）验证，详见 `reports/test-report.md`

## 五、验证记录（W3 通过后回填）

- 交叉编译产物：`kemix.so`（ELF 64-bit LSB, AArch64, ET_DYN）
- 动态依赖：libc.so（无第三方库依赖，与打包口径一致）
- 导出符号：`exports`（module_exports 描述符）、`mod_register`（KEMI 注册入口）；
  KEMI 函数表 `sr_kemi_kx_exports` 为 `static`（不导出），函数名形如 `(kx, get_ruri)`，
  与 `doc/kemix_admin.xml` 文档一致
- 上游测试真实执行（层 1）：`utils/kamctl/dbtextdb/dbtextdb_test.py -v` → 3/3，退出码 0
- 本机（OHOS/aarch64，clang 15.0.4 target aarch64-unknown-linux-ohos，conan 2.29.1）全流程验证：
  `conan create` + `conan test` rc=0 —— 产物结构校验 `check_kemix.py` **12/12**、
  鸿蒙端到端消费者用例 `test_kemix_e2e` **25/25**（`ALL OHOS E2E PASSED`）、上游 unittest 3/3；
  完整证据见 `reports/test-report.md`（连同 W3 本地 CI 结果 `.ci-result.json`，二者均为
  `.gitignore` 忽略的本地证据，不入库）
- 适配前预检：`bash ci/scripts/preflight_check.sh kamailio-kemix/6.0.6` → `[OK] 预检通过（无依赖需要检查）`，rc=0
- 本地源获取：kamailio.org 的 tarball 下载被服务端反复重置，验证用副本改指 127.0.0.1 提供的
  **同 sha256** 官方 tarball（`sha256sum` 复核一致，`get()` 完整性校验通过）；提交配方保持官方 URL 与 sha256

## 六、流程观察（供 SKILL 迭代参考）

- kamailio 子包适配的公共成本集中在核心对象编译，模块自身的构建/打包是常量级工作；
  `kemix` 无依赖（模块 Makefile `LIBS=` 为空），配方显著更短。
- OHOS/musl 加载器不做惰性绑定（`dlopen` ≡ `RTLD_NOW`），core 插件模块**独立加载必然失败**
  （未定义 core 符号需全部可解析）→ 端到端消费者用例必须随用例编译最小 core 符号桩，并以
  `-Wl,--export-dynamic` 导出供 dlopen 解析。

## 七、W4 Pre-PR 独立审计记录

- 执行方式：按 `.gitcode/code-style.md` 与 `.gitcode/review-memory.md` 独立审计本包全部变更文件
  （10 个文件，由上下文隔离的独立子代理执行；结果落 `reports/audit-result.json`，该目录被 `.gitignore` 忽略）
- 结论：**pass**（P0=0 / P1=0 / P2=1 / P3=3，无阻断项）。首轮审计判 fail（P1/R19：e2e 编译产物
  落在被跟踪目录且未被 `.gitignore` 覆盖，`git add archives/` 会连带入库），已修复为写入
  `test_package/build/`（仓库 `.gitignore` 任意层级 `build/` 覆盖）并清理既有残留二进制；
  同时移除对未合入 main 的同族包作为依据的引用，改为自洽可核验表述。

## 八、最终状态

- 状态：`published`（`conan create` 本地验证通过后确定；上游测试清点 17 项、真实执行 3/3）
- 测试：上游 unittest（层 1）+ 本包产物校验与鸿蒙端到端消费者用例（层 2），详见 `reports/test-report.md`
- 结束标记：编译结束（档案已关闭 `.build-closed`）
---

**编译结束**: 2026-09-27 10:50
**最终状态**: published
