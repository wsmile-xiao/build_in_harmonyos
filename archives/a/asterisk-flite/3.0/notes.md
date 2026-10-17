# asterisk-flite 3 — HarmonyOS PC (aarch64) 适配笔记

## 结论
- **状态**: built（工作树完成，等待 hmbs 真机预检）
- **交付物**: `app_flite.so`（Asterisk Flite TTS 拨号计划应用模块，zaf/Asterisk-Flite v3.0）
- 上游: https://github.com/zaf/Asterisk-Flite（tag v3.0，commit 2bdc757）
- 源码包: Asterisk-Flite v3.0 tag 归档（仅 app_flite.c + Makefile + flite.conf.sample 等 7 个文件）

## 构建方案（三段式）
上游是纯 Makefile 工程：硬编码 `CC=gcc`、探测 `/etc/asterisk/asterisk.conf`、假设
asterisk/flite 头文件已装入系统路径——均不适用于 OHOS。配方按上游编译/链接规则
等价参数化：

1. **Asterisk 头文件树**（`deps/asterisk-22.10.1`）：与 asterisk-srtp / asterisk-speex
   完全相同的官方源码包。应用同源 OHOS 补丁后 configure（私有 prefix 注入 6 个硬依赖），
   仅生成模块编译所需的派生头：
   - `include/asterisk/autoconfig.h`（configure/config.status 生成）
   - `include/asterisk/buildopts.h`、`build.h`、`defaults.h`
     （`build_tools/make_buildopts_h|make_build_h|make_defaults_h` 显式生成；
     make_buildopts_h 需要 `menuselect.makeopts` 输入 → 从配方根目录注入，
     与 srtp 同一份验证过的排除列表文件）
   不构建任何 Asterisk 模块（无需 menuselect 二进制参与模块选择）。
2. **flite 引擎**（`deps/flite-2.2`，CMU 官方 GitHub v2.2 tag；festvox.org 官方下载页
   声明源码以该 GitHub 仓库为准）：
   - 补丁 0007：flite 内置 config.sub 为 2011 年版本，不认识 `linux-ohos` 三元组
     （实测报 "system 'ohos' not recognized"），补丁在 maybe_os 分派表与 os 校验表
     各加一行 `-linux-ohos*`。
   - `./configure --with-pic --with-audio=none`：PIC 静态库供 .so 链接；
     OHOS 无 ALSA/OSS 头，强制 none 音频驱动。
   - `make VOXES="<五个上游声音>" LANGS="usenglish" LEXES="cmulex" EXTRABINS=`：
     裁剪到上游 Makefile LIBS 精确所需的 8 个库（libflite_cmu_us_kal/kal16/awb/rms/slt/
     usenglish/cmulex/flite），跳过 cmu_time_awb 与 indic/grapheme 语言集，缩短真机
     jobs=1 构建时间。交叉模式下 flite 顶层 Makefile 本就不构建 tools/main/testsuite。
   - 静态库复制到私有 prefix/lib、头文件到 prefix/include/flite（不走 install 目标，
     规避 toybox cp -pd 行为差异）。
3. **app_flite.c**：按上游 Makefile 的完整规则用 clang 编译链接：
   ```
   clang -pipe -fPIC -O2 -Wall -Wextra -Wstrict-prototypes -Wmissing-prototypes \
     -Wmissing-declarations -D_REENTRANT -D_GNU_SOURCE \
     -DAST_MODULE_SELF_SYM=__internal_app_flite_self \
     -I<ast>/include -I<prefix>/include -c app_flite.c
   clang -shared -Xlinker -x -o app_flite.so app_flite.o \
     -lflite_cmu_us_kal -lflite_cmu_us_kal16 -lflite_cmu_us_awb \
     -lflite_cmu_us_rms -lflite_cmu_us_slt -lflite_usenglish \
     -lflite_cmulex -lflite -lm
   ```

## 依赖（全部已在 ohpcd 发布，与 asterisk-speex/srtp 同集合去掉可选依赖）
| 依赖 | 版本 | 作用 |
|------|------|------|
| libedit | 20240808 | Asterisk configure 硬依赖（pkg-config 探测） |
| libxml2 | 2.15.3 | menuselect 子 configure 硬依赖 |
| ncurses | 6.6 | libedit.pc Libs.private=-ltinfo |
| e2fsprogs | 1.47.4 | libuuid（uuid_generate_random 硬依赖） |
| jansson | 2.15.1.1 | Asterisk configure 硬依赖（>= 2.11） |
| sqlite3 | 3.49.1 | Asterisk configure 硬依赖（内部数据库） |

> flite 未作为 conan 依赖引入（制品仓无此包），改为配方内自包含 vendor 构建：
> conandata.yml 记录官方源 URL+sha256，构建产物只进 build_folder 私有 prefix，
> 五个声音静态链入 app_flite.so 后即无外部运行时依赖。

## API 兼容性核验（v3.0 tag ↔ asterisk-22.10.1 头文件 ↔ flite-2.2）
| 上游调用 | 核验结果 |
|---|---|
| `ASTERISK_REGISTER_FILE()` | Asterisk 22 头文件中已不存在（grep 全树无定义）→ 补丁 0006 删除该调用；上游 master 分支做了相同修复 |
| `ast_register_application(app, exec, syn, desc)` | asterisk 22 module.h 中仍为宏（→ ast_register_application2 + AST_MODULE_SELF），可用 |
| `AST_MODULE_INFO(ASTERISK_GPL_KEY, ...)` | module.h 现行接口，可用 |
| `flite/flite.h`: flite_init/flite_text_to_wave/delete_wave | flite-2.2 include/flite.h、cst_wave.h 均有声明 |
| `cst_wave_save_raw_fd(wave, FILE*)` | flite-2.2 cst_wave_io.c 存在；POSIX 下 `cst_file = FILE*`，签名兼容 |
| `register_cmu_us_*(void)` 声明 vs flite 定义 `(const char*)` | C 符号层面兼容；flite 2.2 实现忽略 voxdir 参数（声音数据静态编入），Debian 同样以此组合发布 |

## 补丁清单（7 个）
| 补丁 | 应用于 | 内容 |
|------|--------|------|
| 0001-configure.patch | asterisk 树 | OHOS clang 无 BlocksRuntime → 禁用 blocks 而非 as_fn_error（与 srtp/speex 同源码包逐字节一致） |
| 0002-include-asterisk-astmm.h.patch | asterisk 树 | ASTMM_LIBC 默认 ASTMM_IGNORE，astmm.h 不再毒化 libc 分配器名（app_flite.c 含 utils.h 直接受益） |
| 0003-include-asterisk-utils.h.patch | asterisk 树 | RAII_VAR blocks 分支仅在 __BLOCKS__ 下启用 |
| 0004-menuselect-config.guess.patch | asterisk 树 | menuselect config.guess 识别 HarmonyOS triplet |
| 0005-menuselect-config.sub.patch | asterisk 树 | menuselect config.sub 识别 ohos-linux triplet |
| 0006-app-flite-drop-register-file.patch | 主源码 | 删除已废弃的 ASTERISK_REGISTER_FILE() 调用（difflib 生成，git apply 对原始 tarball 验证通过） |
| 0007-flite-config-sub-ohos-triplet.patch | flite | config.sub 接受 aarch64-unknown-linux-ohos（本机实测打补丁前后行为变化验证） |

## HMDFS / CI 沙箱规避（沿用 asterisk-srtp 已验证方案，E052/E060）
1. 构建目录 = build_folder/worktree（conan 缓存源码目录跑 config.status 会间歇性
   Permission denied）。
2. `_drop_umask_077` 把两个 autotree 的 configure 里 `umask 077` 改为 022
   （HMDFS 拒绝 0600 临时文件）。
3. configure 失败重试 ×3 + 补跑 config.status；成功判据显式检查
   `makeopts >1000B 且 include/asterisk/autoconfig.h >500B`（flite 检查
   config/system.mak）。
4. `ac_cv_prog_cc_works=yes` 跳过 CI 沙箱禁止的 conftest 运行。
5. 工具链解析优先 `/data/service/hnp/bin/{clang,llvm-ar,llvm-ranlib,bash}`，
   回退 PATH；make 用 `HMBS_MAKE` / `user.hmbs:make_path` 注入值。

## 上游测试审计（no_tests 结论依据）
- v3.0 tag 归档仅 7 个文件：app_flite.c、Makefile、flite.conf.sample、README、
  ChangeLog、authors、COPYING。
- Makefile 目标只有 all/install/samples/clean；无 check/TESTS/check_PROGRAMS。
- 无 tests/ 目录、无测试框架配置、上游仓库未配置 Actions 测试。
- 故 test_package/MANIFEST.yml 写入 `upstream_tests_exist: false` 与上述审计，
  evidence 输出 `status:"no_tests"`、discovered/executed=0 及 reason。

## test_package 设计（R34 实质验证）
check_app_flite.py 对安装产物做 10 项可失败断言：
ELF 魔数 / ELF64 / 小端 / e_machine=aarch64(183) / DT_NEEDED 含 libc.so /
load_module 定义 / unload_module 定义 / flite 引擎符号静态链入（flite_init、
flite_text_to_wave、cst_wave_resample、cst_wave_save_raw_fd ≥3）/ 上游五个声音
register_cmu_us_* 全部存在 / 产物体积 >1MB（证明声音数据链入，非空壳 .so）。
另附进程外 dlopen 的诚实说明（模块由 asterisk 进程加载，核心符号进程外不可解析
属预期）。断言计数由脚本真实执行后输出 HMBS_TEST_PACKAGE_RESULT。

## 已知限制
1. 模块需配合 asterisk 二进制加载使用（本包不含 asterisk 核心）。
2. flite 音频输出走 wave 文件路径（--with-audio=none）；模块本身把合成波形经
   ast_streamfile 播放，不直接访问音频设备，功能不受影响。
3. 缓存机制（flite.conf usecache）写入目录默认 /tmp，部署时可经 flite.conf 配置。

## 文件清单
| 文件 | 说明 |
|------|------|
| conanfile.py | 三段式构建配方（头文件树/flite/模块编译）、依赖注入、HMDFS 规避 |
| conandata.yml | 三组源 URL+sha256 与三组补丁声明 |
| patches/0001~0007 | 平台适配补丁（0001~0005 与 asterisk-srtp 同源一致） |
| menuselect.makeopts / menuselect.makedeps（配方根目录） | make_buildopts_h 输入（与 srtp 同份；放根目录规避 .gitignore 的 packaging/ 规则） |
| test_package/ | R34 实质检查 + MANIFEST.yml + no_tests 审计 |
| manifest.yaml | 版本归档元数据 |
## 2026-08-26 修复轮（真机预检 evidence incomplete：无法读取当前 archive 代码树）

### 本轮诊断与处置
1. **packaging/ 两个输入文件为 0 字节**：menuselect.makeopts / menuselect.makedeps
   上一轮只建了空文件，与 notes 声称的"与 srtp 同份验证文件"不符。
   已从 `archives/a/asterisk-srtp/22.10.1/packaging/` 复制（同一 asterisk-22.10.1
   源码包，字节级一致，17,016B / 12,145B）。注意 .gitignore 第 2 行 `packaging/`
   规则会忽略该目录——若 hmbs 按 git 清单同步工作树，这两个文件可能不随行；
   make_buildopts_h 仅依赖 work 树内拷贝，配方在 build() 内用
   _find_exported("packaging/<fn>") 显式读取，缺失会硬报错而不是静默出错。
2. **source() deps 解包路径 bug（P0）**：conandata 两组附加源都用
   `get(destination=deps, strip_root=True)` —— strip_root 会把包内唯一顶层目录
   的内容直接展开进 destination，两组源会混写进同一个 deps/，build() 随后按
   deps/asterisk-22.10.1、deps/flite-2.2 寻址必然落空（打补丁阶段即失败）。
   已改为各自显式子目录 destination。
3. **_build_flite 重试判据修正**：循环内误查 prefix/lib（拷贝发生在循环之后），
   导致 make 必然跑两遍；改为直接判定 build/*/lib 下 8 个 libflite_*.a 是否齐。
4. **工作区瘦身**：上一轮遗留在 .hmbs/tmp 的 11 份源码解包副本 + 3 个 tarball
   共约 637MB 全部清除（校验已完成：sha256 三包全对、7 个补丁 git apply --check
   全过、YAML/Python 全部可解析）。hmbs 快照读取器不走 git 排除规则，
   大体量临时目录疑似触发"无法读取当前 archive 代码树"超时。

### 离线核验记录（本轮）
| 项 | 结果 |
|---|---|
| Asterisk-Flite-v3.0.tar.gz sha256 | 与 conandata 一致 |
| asterisk-22.10.1.tar.gz sha256 | 与 conandata 一致 |
| flite-2.2.tar.gz sha256 | 与 conandata 一致 |
| 0001~0005 对 asterisk-22.10.1 | git apply --check 通过 |
| 0006 对 v3.0 app_flite.c | git apply --check 通过 |
| 0007 对 flite-2.2 config.sub | git apply --check 通过 |
| 上游 Makefile CFLAGS/LIBS vs 配方编译链接行 | 参数一致（含 -DAST_MODULE_SELF_SYM） |
| flite VOXES/LANGS/LEXES 裁剪 | lang/Makefile BUILD_DIRS=\$(LEXES) \$(LANGS) \$(VOXES) 支持覆盖 |
| flite --with-pic | configure 全局 CFLAGS += -fPIC，静态库对象为 PIC，可链入 .so |
| 头文件闭包 | autoconfig.h(asterisk.h)、buildopts.h(options.h/time.h) 均可由 -I<ast>/include 解析 |
## 2026-08-26 第二修复轮（同一指纹第 2 次：evidence 无法读取 archive 代码树）

### 与第一轮的差异策略
第一轮修的是配方内容缺陷（deps 解包混写、空数据文件、工作区 637MB 瘦身）。
本轮针对同步可见性这一独立失败面：仓库 `.gitignore` 第 2 行的 `packaging/`
规则会忽略任意层级的同名目录——asterisk-srtp/speex 的
`packaging/menuselect.*` 是维护者 force-add 才进入 git 的；本任务执行器禁止
commit，未跟踪且被忽略的文件既不会进 hmbs 的 git 类工作树同步，也不会进
HMBS 通过后的统一提交，真机上 `_find_exported("packaging/<fn>")` 必然
FileNotFoundError。**处置：把两个数据文件移到配方根目录**
（`menuselect.makeopts`、`menuselect.makedeps`），conanfile 的
exports_sources 与 _configure_asterisk 同步改为根目录寻址。该两文件名不命中
任何忽略规则。

### 本轮核验
- 配方树 16 个文件 os.walk 与 `git ls-files --others --exclude-standard`
  完全一致（0 个被忽略、0 缺失）→ git 类同步器可完整读取整树。
- conanfile.py/test_package 脚本 AST、三个 YAML 全部解析通过。
- exports 引用的 9 个数据/补丁文件全部存在且非空。

### 若下次预检仍报同指纹
配方树已排除内容缺陷与同步可见性两类原因；届时应按环境故障上报
（hmbs 快照/同步服务侧问题），不应继续改动配方。

## 2026-08-28 第三修复轮（CI R40 分支名门禁）

诊断：CI #33581 L0n 报 `branch name mismatch (R40)`，分支 `feat/asterisk-flite-3` 去前缀后 `asterisk-flite-3` 不包含 `asterisk-flite-3.0`。归档路径与版本 3.0 正确，分支漏写 `.0`。

处置：本地 `git branch -m feat/asterisk-flite-3.0` 并同步 `.hmbs/pr.json` 的 branch 为 `feat/asterisk-flite-3.0`，保持配方与归档不变，等待 HMBS 基于正确分支重新推送与触发 CI。

## 2026-08-30 第四修复轮（CI R40 二次触发 — 策略差异）

诊断：CI #33734 仍报 R40，CI_BRANCH=feat/asterisk-flite-3。本地已为 feat/asterisk-flite-3.0 且 .hmbs/pr.json 亦为 3.0，但 origin 仅有 feat/asterisk-flite-3（a82e21c），origin/feat/asterisk-flite-3.0 不存在。上一轮零工作树变更，未产生新提交故 HMBS 未对新分支执行推送。

与上一轮差异：本轮主动产生可提交的工作树变更（本节），迫使 HMBS 预检通过后生成新 head 并推送至 feat/asterisk-flite-3.0，从而在远端创建正确分支。

