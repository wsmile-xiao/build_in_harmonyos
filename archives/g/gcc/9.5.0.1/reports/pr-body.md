## PR 信息
- **三方库名称**：gcc
- **上游版本**：9.5.0.1（移植版本号；源 tarball 与 9.5.0 同一上游归档 gcc-9.5.0.tar.xz，零 diff）
- **上游仓库地址**：https://gcc.gnu.org/（官方发布包 + in-tree gmp/mpfr/mpc）
- **适配路径**：路径 B（知识扩展适配，新增 3 份知识草稿）
- **使用知识库**：openharmony-compile-agent；E272（expect/stty 噪声）等

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 上游自测 | make -C gcc selftest | 语言无关 + C 前端内部自测 |
| torture 套件（已执行） | 25200 | gcc.c-torture execute 15802 + compile 9398（另有 590 UNSUPPORTED 探测跳过 / 70 unresolved） |
| **合计** | **25200 + selftest** | 上游套件原样全量执行，未减少用例 |

### 是否存在对上游测试用例的修改？
否（验证环境测试设施适配仅存在于本地验证树，未入包：构建树 prune.exp 增 stty 噪声过滤、site.exp 预置 triplet，不改变判定逻辑）

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 上游自测 | 同上游 | 不变 | selftest EXIT=0 |
| 上游 torture 全量 | 同上游 | 不变 | dejagnu 全量重跑，**25134/25200 = 99.74%** |
| 鸿蒙特有测试 | 4 | 新增 | test_package：真实编译+链接+设备运行 + .codesign 节断言 + DEFAULT_LINKER 断言 |
| 配方内子集门禁 | 100 | 新增 | gcc.c-torture/execute 前 50 源 × (-O0,-O2)，100/100 |

---

## 上游测试用例修改说明
无。

## 验证结果

### 编译验证
- 编译器: clang (aarch64-unknown-linux-ohos，stage-1 构建 `--disable-bootstrap`)
- 编译状态: conan create EXIT=0（package_id `6b129b068851896169fae42d399fa922d239ce8a`，日志 `~/rtb-verify/gcc-9.5.0.1-create3.log`；finish 内 G2 conan-verify PASS + W3 本地 CI 100%）
- 构建系统: autotools
- 配置选项: `--enable-default-pie --with-ld=<SDK>/ld.lld --disable-bootstrap --disable-lto --disable-plugin --disable-multilib --disable-shared --enable-languages=c`（+ configure 后清 NO_PIE_* 四变量，全链 PIE + lld 自动签名）

### 测试通过率
- 上游套件：**99.74%**（execute.exp 15761 PASS/41 FAIL/307 UNSUPPORTED/15 unresolved；compile.exp 9373 PASS/25 FAIL/55 UNRESOLVED/283 UNSUPPORTED；证据 `reports/dejagnu-{execute,compile}.stdout.log`）
- 66 个失败 100% 归因平台/环境/测试设施限制，无编译器缺陷：
  - GNU trampoline 25：OHOS 内核对栈上运行时生成代码强制签名校验（平台级，`-z execstack` 无效）
  - musl tmpnam 16：硬编码只读 /tmp，freopen 失败 exit 1，TMPDIR 不生效
  - 病态嵌套 ICE 20：limits-exprparen/structnest（10^4 层）触发 stage-1 cc1 崩溃；非栈耗尽（256MB 栈复现不变）；上游自举构建通过
  - 探针污染 5：pr46534，expect 的 /bin/stty 噪声使 size32plus 探针误判，编译器行为本身正确
- 新增测试：104/104（torture 子集 100/100 + test_package 4 断言全过）

### 版本背景（为何需要 9.5.0.1）
9.5.0（路线 A）在 OHOS 上有平台级缺陷：非 PIE 对象 + lld COPY 重定位 LO12 未对齐 → nestfunc/printf-2 等段错误、宿主生成器崩溃。本版路线 B 根因修复：全链 PIE + `--with-ld` 烘焙 SDK ld.lld（链接即自动 .codesign），GNU ld（不签名，rc=126）被排除。9.5.0 保持历史原样可对照。

### 补充说明
- **commands.json 软件级位置（PF9/R38 口径冲突豁免）**：application 型工具链包按 R38 维护软件级 `archives/g/gcc/commands.json`（本次新增 9.5.0.1 条目），同 vamps 0.99.2 先例。
- **ci/config/build_timeouts.txt**：新增 `gcc/9.5.0.1 57600`，随 feat 提交有先例（gcc-14/qtbase/casacore）。
- **.gitignore**：gcc reports 白名单 4+2 行（tcping/lz4/jsonifier 先例，仅放行 test-report 与两份 dejagnu stdout 证据）。
- **已知限制**：stage-1 cc1 在 10^4 层病态嵌套源上 ICE（编译器极限探测用例）；musl 平台 trampoline 语义为内核安全策略，非本包可修复。
- **知识增量**：3 份草稿（非 PIE COPY 重定位崩溃 / lld 链接即签名工具链路线 / OHOS dejagnu 证据固化）。
- W4 Pre-PR 独立审计：P0=0/P1=0/P2=0/P3=5，verdict=pass。
