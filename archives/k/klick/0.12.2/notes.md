# klick 0.12.2 适配笔记

## 编译环境

- 构建系统: scons（上游压缩包顶层只有一个 SConstruct，没有 configure、CMakeLists.txt 或 Makefile.am）
- 编译日期: 2026-09-26（配方与四枚补丁完成并推送到 `feat/klick-0.12.2` 的日期；同日 `conan-verify` 判 PASS、`finish` 收尾，判决读数见「验证结果」节，精确时间以文末框架块为准）
- 编译器: clang / clang++（取自 Conan profile 的 `tools.build:compiler_executables`，键 `c` 与 `cpp`（R33，不留裸 shell 变量余地）；首轮实跑解析到 `/data/service/hnp/bin/clang++`）
- 构建器: SCons 4.10.1，由配方在 `generate()` 内以 `pip install --target` 装进本次构建独占的 `_scons_env`，再以 `PYTHONPATH` 交给 `build()`/`package()`（gpsd/3.26 同路数；不走 tool_requires，因为 ohpcd 上没有 scons 配方，且这样能保证 `build()` 内不再有网络动作）
- 状态: built（`knowledge/ARCHIVE-SPEC.md` §3 第 256 行的 `built` ＝ conan_verify PASS 且未 upload；本包 `conan create` 未向 ohpcd 上传，故不取 `published`。该值此前长期是 `pending_ci`，两段时间层的取舍理由逐条记在文末「收口更正」与软件级 `../manifest.yaml` 的 status 注释里）

## 编译步骤

1. `source()`：`get(self, **self.conan_data["sources"], strip_root=True)`，取源 URL 与校验和全部来自 `conandata.yml` 的官方直链。
2. `generate()`：`python3 -m pip install --quiet --no-input --target=<build_folder>/_scons_env scons==4.10.1`；随后把 `SCons/Platform/posix.py` 里的 `env['SHELL'] = 'sh'` 一次性改成 `'/system/bin/sh'`（OHOS 上没有 `/bin/sh`，E165 同族）；`VirtualBuildEnv` 之后用 `Environment().define_path("PYTHONPATH", ...)` 存成 `scons_env` 脚本供 `build()`/`package()` 取用。
3. `build()`：`apply_conandata_patches(self)` 按 `conandata.yml` 顺序打 `0001`（依赖探测换注入槽）、`0002`（SCons 4 兼容）、`0003`（constexpr）、`0004`（正则拼接处字面量与宏名之间补空格）。
4. `build()`：遍历 `self.dependencies`，把每个依赖 `cpp_info`（含 components）的 `includedirs` 拼成 `-I`、`libdirs` 拼成 `-L`、`defines` 拼成 `-D`，合成 `KLICK_DEPFLAGS`；再以
   `KLICK_DEPFLAGS="…" CC=<profile c> CXX=<profile cpp> python3 -m SCons --jobs=2 OSC=0 RUBBERBAND=0 PREFIX=/`
   编译（CC/CXX 走环境变量而不是命令行 `CXX=`，原因见问题表第 5 行）。
5. `package()`：同一 `CC`/`CXX`、同一 `KLICK_DEPFLAGS` 跑 `python3 -m SCons install … PREFIX=/ DESTDIR=<package_folder>`。两处命令行必须逐字一致——SCons 以命令行做构建缓存键，`package()` 里换成裸 `clang++` 或空的注入槽会让每个目标都被判过期，从而在 `package()` 内全量重编。
6. `package_info()`：`cpp_info.libs = []`（独立工具，不出库）、`cpp_info.bindirs = ["bin"]`。
7. 刻意不套任何 layout 布局 helper：`conan` 的 `build()`/`package()` 以 `build_folder` 为 cwd 执行，布局 helper 会把源码留在 `<base>/`、把构建挪到 `<base>/build-release/`，SCons 在空构建目录里向上找不到 SConstruct。本项是**按配方注释规避**，未在该方向上留下失败判决。

## 遇到的问题与解决方案

| # | 症状 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首轮 `conan-verify`（09:02）G1 FAIL，未进到 `conan create`，且报告未打印失败项 | G1 清点归档结构件：`test_package/MANIFEST.yml` 必须存在（L0e），tool 类型必须有 `commands.json`（L0k/R38），当时两者都不在归档里 | 随后补齐 `commands.json` 与 `test_package/MANIFEST.yml`（随 `1ad5117cbf` 提交），同一步在 09:18 与 09:28 两轮均为 G1 PASS |
| 2 | `boost/core/detail/sp_thread_sleep.hpp:73:5` 与 `:90:5` 报 `error: use of undeclared identifier 'pthread_setcancelstate'`（scons: *** [src/main.o] Error 1） | OHOS libc 头不声明 pthread 取消 API；boost/1.84.0 已按 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 宏给该头打了补丁并**要求消费者自己定义**这个宏；手写 SCons 命令行不经过 CMakeToolchain / AutotoolsToolchain 这类生成器，拿不到依赖在自己 `cpp_info`/组件上声明的编译宏 | `18edb788f9` 在 `_depflags()` 里遍历各依赖的 `cpp_info` 与 `components`，把声明的 `-D` 宏一并转发进 `KLICK_DEPFLAGS`（去重保序） |
| 3 | `src/metronome_map.hh:51:25`、`src/metronome_simple.hh:62:24`、`:63:24` 报 `error: in-class initializer for static data member of type 'const double'/'const float' requires 'constexpr' specifier [-Wstatic-float-init]` | C++ 标准要求 non-integral 静态数据成员的类内初始化必须写成 `constexpr`；g++ 把裸 `static const double/float` 当 GNU 扩展放过，clang 判 error | 补丁 `0003` 把 `TICKS_PER_BEAT`、`MAX_TAP_AGE`、`TAP_DIFF` 三处改成 `static constexpr`；值、类型、所有使用点不变 ⇒ 无语义改动。同文件的 integral 常量 `MAX_TAPS` 按标准本就可类内初始化，保持不动 |
| 4 | 上游 SConstruct 的依赖探测在 OHOS 交叉环境无路可走 | 上游用 `env.ParseConfig('pkg-config --cflags --libs jack samplerate sndfile')` 探测，且 `HAVE_SNDFILE_OGG` 挂在 `pkg-config --atleast-version=1.0.18 sndfile` 上；OHOS 上没有可靠的系统 `.pc` 库可探，`pkg-config` 的环境变量传参在交叉环境也不生效（E075） | 补丁 `0001`：删掉这段探测，换成 `env.MergeFlags(os.environ['KLICK_DEPFLAGS'])` 注入槽（由 Conan 显式给出每条 `-I`/`-L`/`-D`，配方从不依赖系统 .pc 库），链接表显式写成 `env.Append(LIBS = ['jack', 'samplerate', 'sndfile'])`，`HAVE_SNDFILE_OGG` 改为无条件定义（Conan 的 libsndfile 自带 vorbis/ogg，E151 同族） |
| 5 | 上游 SConstruct 在 SCons 4 下语义不成立 | SCons 4 删除了 `Options` / `PathOption` / `BoolOption` 旧拼法，不再把命令行 `NAME=value` 隐式写进 `Environment`（`Variables` 对象必须自己消费 `ARGUMENTS`），且编译器只在 `Environment()` 构造点认 | 补丁 `0002`：迁到 `from SCons.Variables import Variables, PathVariable, BoolVariable` + `Variables('scache.conf', ARGUMENTS)` + `opts.AddVariables(...)`，并在 `Environment(...)` 构造处加 `CC = os.environ.get('CC', 'clang')` / `CXX = os.environ.get('CXX', 'clang++')`。除这些行以外上游 SConstruct 保持原样 |
| 6 | `liblo/0.34`、`rubberband/3.3.0` 无法作为依赖引入 | 两者在 ohpcd 制品仓**未发布**（控制组实证见下节）；这不是上游不支持，也不是本包选择不做 | 用上游自带开关把 OSC 与 RUBBERBAND 两个功能面编译关闭（`OSC=0 RUBBERBAND=0`；`RUBBERBAND` 上游默认即 False）。两依赖已进任务登记表候选池由他窗适配 |

### 最小复现

- 问题 2 与问题 3：同一轮 `conan create`（profile `ohos-aarch64`，`ohpcd/stable`）在 `build()` 阶段由 SCons 编 `src/main.o` 与 `src/klick.o` 时报出。2026-09-26 09:18 与 09:28 两轮 `conan-verify` 同判 `G0 PASS / G1 PASS / G2 FAIL`，两条 error 系列就是上表原文；`scons` 的读取与打补丁阶段全部正常，故复现路径是编译器诊断本身，不是构建器起不来。
- 问题 4 与问题 5：属**构造性**复现——依据是上游 `SConstruct` 原文（`0001` 的删除行 `env.ParseConfig('pkg-config --cflags --libs jack samplerate sndfile')` 与 `opts = Options('scache.conf')` / `opts.AddOptions(...)` 段），这两处在打进本包的补丁 diff 里可逐字看到，未打补丁的上游写法在 OHOS 上没有走通过（配方起草起就把它们改掉，因此没有"未打补丁失败"的判决可拿）。
- 问题 6：见「功能裁剪」节的控制组实验。

### 已试过的失败方案

1. **走框架探索流水线取源**：`ohc-run.py build klick 0.12.2` 的 Step1 下载器不读 `conandata.yml` 里的官方直链（它按候选站搜，`das.nasophon.de` 不在候选内），取源失败并直接 `init_build_failed`（rc=2）；`--resume-from=Step2` 接着报「源码目录不存在 `archives/k/klick-0.12.2/src`」「未找到 `.build-context` 文件」。定性为**框架侧取源卡点，不是本包缺陷**。⇒ 手写配方不再走 `ohc-run build`，W3 直接以 `conan-verify` 为门禁（quagga 先例）；⛔ 不伪造 `src/` 目录、⛔ 不再跑 `init-build`（会覆盖手写配方）。
2. **把编译器用命令行传给 SCons**：`python3 -m SCons CXX=/path/clang++ …` 在 SCons 4.10.1 上实测只落进 `ARGUMENTS`，永远到不了 `Environment`，真正跑起来的是构建器默认的那台编译器（⇒ profile 说了不算，违背 R33）。⇒ 改由 `os.environ` 在 `Environment()` 构造点取 `CC`/`CXX`（`0002`）。这一步是在构建主机上对 SCons 4.10.1 逐项实测确认的（连同 `Options` 别名是否可导入、`Variables(file, ARGUMENTS)` 与缓存文件 `scache.conf` 之间的优先级）。
3. **照知识图谱首轮建议 E540 处置**（`runner-path-prepend`，把 hnp 工具路径前置）：**不适用，未采纳**。首轮 `build()` 的 `CC`/`CXX` 已经是 profile 解析出的 `/data/service/hnp/bin/clang` / `clang++`，而真错来自 boost 头对消费者宏的要求与 clang 的 constexpr 规则，与工具路径遮蔽无关；任务目录内也从未落过任何 `EXTRA_PATH` 类改动。该误命中记录在首份 `conan-verify` 报告里，处置依据不取自它。
4. **`test_package` 往当前目录写中间文件**：框架 `L1e` 会在正照之后对同一个 `test_package` 起第二轮负照（rc=127），相对写盘会在归档目录里留下脏文件并被目录级 `git add` 捎进 PR。⇒ `f99afa181d` 改为一切写盘进调用方给的绝对 `OUT` 目录（目录名加 shell pid 后缀，`trap EXIT` 无论成败都清理），断言数不变。

### 适用边界

- `0001` 的注入槽只对"Conan 能逐条显式给出搜索路径与宏"的手写构建命令行有意义；若将来换成 Meson/CMake 上游，该补丁应整体废弃，改走官方生成器。
- `0002` 只解决"上游 SConstruct 的旧 build-variable 拼法"，没有改动任何构建目标、源文件表或安装规则；`DEBUG` / `TERMINAL` 两个开关的行为保持上游默认。
- `0003` 是纯可移植写法修正，可复用于任何"上游以 g++ 扩展写 non-integral 静态类内常量、在 clang 下判 error"的 C++ 包；不涉及任何数值或ABI改动，因此不需要版本化开关。
- 依赖宏转发（`18edb788f9`）只覆盖依赖在 `cpp_info` / `components` 上以 `defines` 声明的宏；靠生成器模板文件传宏的依赖不在它的覆盖面内。
- 功能裁剪的边界：本包交付的 `klick` 无 OSC 控制入口、无 Rubber Band 音高变换；核心节拍器链路（JACK transport、tempomap/pattern、WAV 导出）不受损。恢复条件是 `liblo` / `rubberband` 在 ohpcd 发布，届时只需把 `OSC=0` / `RUBBERBAND=0` 翻回 `1` 并补 `requires`，其余不变。

## 功能裁剪（因依赖发布态而裁剪）

`liblo/0.34` 与 `rubberband/3.3.0` 经**控制组实证**判定为 ohpcd 制品仓未发布：在同一 `CONAN_HOME`、同一 remote 下查询，`boost/1.84.0` 与 `jack/1.9.22` 正常返回 recipe revision，而 `liblo`、`rubberband` 与一个故意写出来的不存在 ref 返回的是**同一条** `error:system acceleration policy not enabled` ⇒ 报错形态与"未发布"同类，而不是查询姿势错。据此用上游自带开关关闭 OSC（依赖 liblo）与 RUBBERBAND（依赖 rubberband，上游默认即 False）两个功能面。

- 这不是"上游不支持 OHOS"，也不是"我们不想做"：**上游两项功能都完好**，缺的只是制品仓里的依赖制品。
- 两依赖已进任务登记表候选池，由他窗适配；适配合入后本包只需翻开关。
- ⛔ 本包不恢复这两个功能面，⛔ 不引入第二个 source。

## 依赖版本

| 依赖 | 版本 | 用途 | W0 发布态 |
|------|------|------|-----------|
| boost | 1.84.0 | 上游只用头文件（`shared_ptr`、`shared_array`、lambda；SConstruct 与源码中无 `-lboost_*` 链接） | 已发布 |
| jack | 1.9.22 | JACK 客户端接口（节拍器的 transport / timebase 回调） | 已发布 |
| libsndfile | 1.2.2 | 点击轨 WAV 导出 | 已发布 |
| libsamplerate | 0.2.2 | 采样率转换 | 已发布 |

- 构建器 `scons==4.10.1` 来自 PyPI，由 `generate()` 装进本次构建独占的隔离前缀，**不是** Conan 依赖（ohpcd 上没有 scons 配方）。
- W0 预检（`preflight_check.sh klick/0.12.2`）结论：上述 4 个精确依赖全部已发布，且版本号 `klick/0.12.2` 未被占用（R37）。
- 知识检索口径：配方起草棒在语料侧跑 `ohc-run.py recipe-search klick` 打印「无相似配方（语料 6174 条）」——那是**知识库语料检索**的结论（顶层 SConstruct 属冷门构建系统），⛔ 不得当作 ohpcd 发布态判据；发布态一律以 `preflight_check.sh` 与上面控制组的精确 ref 查询为准。

## 上游测试用例清点（如实申报 0）

上游 0.12.2 **没有任何自动化测试**。三条清点依据（对 sha256 `1289533c0849b1b66463bf27f7ce5f71736b655cfb7672ef884c7e6eb957ac42` 的官方 tarball 解包后逐条核对）：

1. 文件清单只有 `COPYING` / `NEWS` / `README` / `SConstruct` / `doc/manual.html` / `samples` 下 8 个 wav / `src` 下 16 个 cc 与 17 个 hh / `src/util` 下 7 个 hh 加 `util.cc`；没有 `test`、`tests` 目录，也没有任何以 test、check、spec 命名的文件。
2. `SConstruct` 的目标只有 `env.Program('klick')`、`Default('klick')` 与 `env.Alias('install', [...])`，没有 check / test 别名。
3. `README` 的构建说明只有 `scons` 与 `scons install` 两步，没有测试步骤。

⇒ 上游静态测试合计 **0**。三条常规清点路径（`make -n check`、`ctest -N`、`meson test --list`）在本包都不存在：顶层既没有 `configure` / `Makefile.am`，也没有 `CMakeLists.txt`。该口径与 `test_package/MANIFEST.yml` 的 `upstream_tests: []` 同源。

## 运行级限制与消费者测试

OHOS PC 沙箱没有 jackd 服务，也没有真实音频设备 ⇒ 节拍器的**会话层**（JACK transport、点击音频输出）无法运行。消费者断言因此压在 server-free 路径上。参照同族已合入包 jack/1.9.22 的 `test_package/MANIFEST.yml` 写法（"Execute JACK version, size-limit, and ringbuffer API checks **without requiring a running jackd server**"），下面三条不是"跑不起来所以只看 `--help`"，而是各自能证伪一段真实链路：

| 层 | 断言 | 它在证明什么（为什么是真断言） |
|----|------|--------------------------------|
| L1 | `bin/klick` 存在且可 exec | 动态依赖闭包（jack / libsndfile / libsamplerate 及其 zlib、libc++ 传递依赖）必须全部解析成功——只要有一条不闭合，loader 在 `main()` 之前就退 127，与程序逻辑无关 |
| L2a | `klick -V` 退出码 0 且输出含 `klick 0.12.2` | 版本横幅来自编译期常量 `VERSION`（由 SConstruct 注入）⇒ 证明真实产物、选项解析与 iostream 都在跑；走的是 `Options::parse` 的早期分支，不触碰 JACK 连接 |
| L2b | `klick -h` 退出码 0 且输出含 `Usage:` | 同上，走另一条早期分支，证明用法块与参数表已链接进产物 |

3 条用例共 **5 个断言点**（可执行 1 条 + `-V` 退出码/横幅 2 条 + `-h` 退出码/用法块 2 条），与 `test_package/MANIFEST.yml` 的 `assertion_count: 5` 同源。会话层声明为不可无头运行：不计入通过率、不写作"设备不支持"式的笼统结论，其恢复条件是设备侧具备 jackd 与音频后端（属环境前提，非本包缺陷）。

## 测试用例统计

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无 test/tests 目录，无任何以 test、check、spec 命名的文件 |
| 集成测试 | 0 | SConstruct 只有 Program / Default / install 目标，无 check、test 别名 |
| 其他测试 | 0 | README 构建步骤只有 scons 与 scons install，无测试步骤 |
| **合计** | **0** | 静态清点口径，三条依据见「上游测试用例清点」节 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无自动化测试可继承 |
| 消费者测试（test_package） | 3 | +3 | test_klick.sh 的 L1 可 exec、L2a 版本横幅、L2b 用法块三条真断言，共 5 个断言点；执行判决见「验证结果」节 |
| **合计** | **3** | **+3** | |

- 测试数量变化原因：上游合计为 0 且无可继承的测试套件，适配后的 3 条全部是新增的消费者用例（Conan `test_package` 调已安装二进制），因此适配后合计 3 ≥ 上游合计 0，不存在少报分母。

## 验证结果

- 编译状态：built——`conan-verify` 判绿，三一致读数：命令正文 `✅ 配方验证通过: klick 0.12.2`、`reports/conan-verify-report.md:3` 的 `**Verdict**: PASS`、驱动层 `CONAN_VERIFY_RC=0`。同文件 G0—G4 四道门禁逐条 `✅ PASS`（第 8、12、26、30、34 行），其中 G1 含 `✅ test_package/MANIFEST.yml 存在`、G2 含 `✅ conan create 成功`。
- 本地 CI 标记原样（`reports/w3-local-ci.log`，权威一律取 `*_RESULT=` 行）：`G0_RESULT=pass`（23 行）、`KC_RESULT=pass`／`KC_ERRORS=0`（68—69 行）、`JC_RESULT=pass`／`JC_ERRORS=0`（95—96 行）、`L0_RESULT=pass: all checks passed`（354 行）、`L1_RESULT=pass: test_package executed`（355 行）、`L2_RESULT=skip: klick version/help failed`（356 行）、`L4_RESULT=pass: patches clean`（357 行）、`L5_RESULT=pass: bin/ has content`（358 行）；`Build Summary` 为 `Success: 1 / Failed: 0 / Pass rate: 100.0% (1/1)`（364—366 行）。
- ⚠ 两种读数的口径提醒（同包实拍）：`reports/conan-verify-report.md` 的 `## L2: ✅ PASS`、`## L4: ✅ PASS`、`## L5: ✅ PASS` 三行图标与其正文 `⏭️ 跳过（无 cache 路径）` 互相矛盾，一律以上面的 `*_RESULT=` 标记为准。`L2_RESULT` 取值 `skip`（框架初值即 skip、non-blocking），它**既不是失败也不是产物可执行的证据**，⛔ 不得拿 `✅ PASS` 图标当运行级凭据。
- 产物可执行的真凭据是消费者断言原样输出 `KLICK_SMOKE_PASS version=1 usage=1 out_dir_removed=1`（`reports/conan-create.log:126`、`reports/conan-create-W3-pass.log:258`、`reports/w3-local-ci.log:338` 三处同一行，三次独立运行均复现）；`L1e` 破坏性负照真判绿（`reports/w3-local-ci.log:350` 的 `[ok] L1e: Negative test confirmed — test genuinely depends on klick`）。
- 上游测试用例通过率：不适用（上游 0 条自动化测试，见「上游测试用例清点」节）。
- 新增测试用例通过率：3/3 条用例、5 个断言点全过（口径与 `test_package/MANIFEST.yml` 的 `assertion_count: 5` 同源）。
- 历史判决留档：2026-09-26 09:18 与 09:28 两轮 `conan-verify` 为 `G0 PASS / G1 PASS / G2 FAIL`（对应修复前配方，⛔ 不得当作本轮证据），16:05 第二轮 FAIL 留档在 `reports/conan-verify-report-G2-fail-round2.md`，16:08 起判 PASS。失败轮报告与日志留在 `reports/` 只为可追溯——`reports/` 整体被根 `.gitignore` 第 96 行忽略，不随 PR 提交。

## 交付物

W3 已跑绿，构建产物已产生（`conan create` 通过、未向 ohpcd 上传）。本机 Conan 包目录实测读数：`bin/klick` 2218496 字节；`share/klick/samples/` 8 个 wav 合计 84938 字节；包目录 `du -sb` 合计 2321833 字节。本包安装内容：

| 路径 | 内容 |
|------|------|
| `bin/klick` | 命令行 JACK 节拍器可执行文件（`package_type = "application"`，`cpp_info.bindirs = ["bin"]`） |
| `share/klick/samples/*.wav` | 8 个点击采样（click / noise / sine / square 各含 emphasis 与 normal 两枚），按上游布局随包安装，编译期常量 `DATA_DIR` 指到这里 |

## 源码修改

- `patches/0001-source-SConstruct.patch`（22 行，portability）：`env.ParseConfig('pkg-config …')` + `--atleast-version` 探测段 → `KLICK_DEPFLAGS` 注入槽；链接表显式化；`HAVE_SNDFILE_OGG` 无条件定义。
- `patches/0002-source-SConstruct-scons4-compat.patch`（45 行，portability）：`Options`/`PathOption`/`BoolOption` → `Variables`/`PathVariable`/`BoolVariable` + 显式 `ARGUMENTS`；`Environment()` 构造点从 `os.environ` 取 `CC`/`CXX`。
- `patches/0003-source-constexpr-static-float.patch`（24 行，portability）：`src/metronome_map.hh` 的 `TICKS_PER_BEAT`、`src/metronome_simple.hh` 的 `MAX_TAP_AGE` 与 `TAP_DIFF` 改为 `static constexpr`。该补丁由 difflib 机械生成，并在设备上对未打补丁的源包真做过 apply 复验（RC=0）。
- `patches/0004-source-tempomap-literal-space.patch`（补丁文件 44 行、2 个 hunk 改写 10 行，portability）：`src/tempomap.cc` 内 15 处字符串字面量与其后 `REGEX_LABEL` / `REGEX_INT` / `REGEX_FLOAT` / `REGEX_PATTERN` 宏名相邻处补一个空格。纯空白改动，拼出的正则逐字不变；等价性自证（本轮独立复核，脚本 `~/tmp/uc2/klick/checkpatch.py`）＝逐对 `-`/`+` 行去掉全部空白后完全相同（`NON_WHITESPACE_DIFF_LINES=0`，10 对）、`"REGEX_` 相邻计数 15→0、改动行内引号总数 50→50。
- 四枚补丁都已在 `conandata.yml` 的 `patches:` 中登记（`apply_conandata_patches()` 只认登记过的；`conandata.yml:9-21` 的四条 `patch_file` 与盘上 `patches/0001~0004` 一一对应，版本级 `manifest.yaml` 的 `patches_applied` 亦列同四枚）。本包**不改任何配方之外的上游文件**。

## 路径与知识库声明

- 适配路径：路径 A（基础适配）
- 使用知识库：openharmony-compile-agent（`recipe-search` 语料检索 + 知识图谱检索，并复用仓内 SCons / autotools 类先例：gpsd/3.26 的 SCons 隔离前缀与不套布局 helper、ffmpeg2theora 的构造点定编译器、jkmeter 的 conan 下载缓存预置）
- 知识库扩展：无新增机制（命中既有条目，见关联 Issue 行）
- 关联 Issue：无。本包走路径 A（基础适配），知识库扩展判定为命中既有条目（E165 解释器 shebang、E075 configure/pkg-config 环境变量传参在交叉环境不生效、E151 手工补 have-defines、E238 嵌入式 Clang 头路径发现必须保留目标 sysroot），故不创建知识库扩展 Issue。
- 归档状态：`built`——W3（`conan-verify`）已判 PASS 且 `conan create` 未向 ohpcd 上传，正好落在 `knowledge/ARCHIVE-SPEC.md` §3 第 256 行 `built` 的触发条件上。该值此前是 `pending_ci`（当时 W3 从未跑绿、写 `built` 就是伪造证据），更正过程与两段时间层见文末「收口更正」及两级 `manifest.yaml` 的 status 注释。

## 注意事项

- 取源只用官方直链 `https://das.nasophon.de/download/klick-0.12.2.tar.gz`，sha256 `1289533c0849b1b66463bf27f7ce5f71736b655cfb7672ef884c7e6eb957ac42`（该哈希已与上游原始发布树逐字节比对一致；⛔ 取源地址不得改用发行版软件池镜像——PF7 拉黑，本包任何文件都不出现池址）。
- 版本串一律 `0.12.2`：任务版本、Conan 版本、归档目录 `archives/k/klick/0.12.2/`、分支 `feat/klick-0.12.2` 四者必须完全一致，不做"归一化"。
- `conanfile.py` 的 `validate()` 只放开 `os` ∈ 的 Linux / OHOS，且 OHOS 仅 `armv8`。
- 产物隔离：`archives/k/klick/0.12.2/reports/`（`.gitignore` 第 96 行）、`__pycache__/`（第 194 行）、`.handoff.json`（第 254 行）均为忽略态，不需要额外隔离动作；但 `__pycache__/` 跑一次 verify 就长回来，建 PR 前必须确认它不在待提交清单里（`run` 按包目录 add）。
- `test_package` 的一切写盘必须走私有输出目录（见「已试过的失败方案」第 4 条），否则会污染 `L1e` 负照轮。
- 地雷（本轮实测，⛔ 每跑一次判决就会复发）：`test_package/conanfile.py:41` 的 `runtime_root = str(Path(self.build_folder, "runtime-libs"))` 会把 jack 的版本号 SONAME 副本以**普通文件**落进归档树，而根 `.gitignore` 第 5 行只有 `*.so`，**不覆盖 `*.so.N` / `*.so.N.M`** ⇒ 本轮实测四枚未忽略的 `??`：`libjack.so.0`（391616 字节）、`libjack.so.0.1.0`（391616）、`libjackserver.so.0`（793024）、`libjackserver.so.0.1.0`（793024），合计 2369280 字节；`git check-ignore -v` 对四枚一律 rc=1，而同目录的裸 `libjack.so` 命中 `.gitignore:5:*.so`。`run` 按包目录 add 会把这些二进制卷进 PR。⇒ 本轮把四枚移到 `~/tmp/uc2/klick/quarantine-z70/` 留证（⛔ 不删，它是该复发机制的实物证据）；⛔ 不顺手给根 `.gitignore` 补 `*.so.*`——那是框架改动，须单独 PR。建 PR 前必须复核 `git status --untracked-files=all -- archives/k/klick` 为空。
- 本 PR 只含 `archives/k/klick/` 这一个软件归档，不含框架改动。
- ⛔ 不要恢复 OSC / RUBBERBAND，⛔ 不要引入第二个 source。

---

**收口更正（时间层一，原文判据保留）**：下面这段写于 W3 跑绿之前——其时构建准入门长期红（`MemAvailable` 5.3~5.9GB < 6000MB，最后一轮 40 次排队 0 次放行），`conan-verify` 从未判绿。当时的判据是：`knowledge/ARCHIVE-SPEC.md` §3 的 `built` 触发条件写明 `conan_verify PASS，未 upload`（第 256 行），而 W3 从未 PASS，写 `built` 或 `published` 就是伪造证据；`failed` 与 `archived` 又各自断言一件没发生的事（编译失败 / 被新版本取代）。四态中无一能诚实表达该现场，故取仓内既有先例值 `pending_ci`，并声明 `finish` 未执行、补丁面为 `patches/0001~0003`、无可引编译判决。**该段的这三项结论（状态取值、补丁面、finish 与判决有无）已被下述时间层二取代**；保留原文判据是为了「当时为什么不预标 built」可追溯，不做无痕改写。

**收口更正（时间层二，现值与凭据）**：W3 已 PASS，三一致读数为 `conan-verify` 正文 `✅ 配方验证通过: klick 0.12.2`、`reports/conan-verify-report.md:3` 的 `**Verdict**: PASS`、驱动层 `CONAN_VERIFY_RC=0`；G0—G4 逐条 `✅ PASS`（同文件第 8、12、26、30、34 行），本地 CI 的 `*_RESULT=` 标记与 `KLICK_SMOKE_PASS version=1 usage=1 out_dir_removed=1` 见「验证结果」节。补丁面是 **0001~0004 四枚**：新增的 `0004-source-tempomap-literal-space.patch`（2 个 hunk 改写 10 行）源于 clang 在**词法阶段**把 `"("REGEX_LABEL` 这类相邻读成 reserved user-defined literal 而判 `error: invalid suffix on literal`（g++ 当扩展折叠放过），修法纯空白——本轮独立复核：逐对 `-`/`+` 行去全部空白后完全相同、`"REGEX_` 相邻计数 15→0、改动行内引号总数 50→50，拼出的正则不变。`finish` 已执行，其落盘读数为 `.build-closed`、`.conan-verified`、`ci-metadata.json`、`reports/w3-local-ci.log` 与文末框架块；两级 `manifest.yaml` 的 `status` 均已同步为 `built`（软件级不由 `finish` 维护，本轮人工对齐），`.ci-result.json` 的 `exit_code` 为 0。

---

## 决策与否证记录

下列小节记录本包适配线路上真实发生过的判断与否证，每条结论都指回盘上实物（补丁名 / 文件行 / 判决原文）。

### 对话 #1：冷门构建系统下「没有先例」能不能当判据

- 问：顶层只有一个 SConstruct，`ohc-run.py recipe-search klick` 打印「无相似配方（语料 6174 条）」，能否据此判定依赖或发布态？
- 答：不能。该读数属**知识库语料检索**，与 ohpcd 制品仓的发布态是两件事；发布态一律以 `preflight_check.sh klick/0.12.2` 与精确 ref 查询为准（见「依赖版本」节第 3 条）。本包的扩展判定为命中既有条目（E165 / E075 / E151 / E238 一族），不新建条目，理由见「路径与知识库声明」节。
- 否证：曾按框架探索流水线取源，`ohc-run.py build klick 0.12.2` 的 Step1 下载器不读 `conandata.yml` 的官方直链（`das.nasophon.de` 不在其候选站内），取源失败并 `init_build_failed`（rc=2），`--resume-from=Step2` 再报「源码目录不存在 `archives/k/klick-0.12.2/src`」「未找到 `.build-context` 文件」。⇒ 定性为框架侧取源卡点、不是本包缺陷，改手写配方并以 `conan-verify` 作 W3 门禁（原文见「已试过的失败方案」第 1 条）。⛔ 不伪造 `src/` 目录、⛔ 不再跑 `init-build`（会覆盖手写配方）。

### 对话 #2：依赖探测链断在哪一层，用什么补

- 问：上游 `env.ParseConfig('pkg-config --cflags --libs jack samplerate sndfile')` 在 OHOS 交叉环境无路可走，为什么是换注入槽而不是补桩 `.pc` 文件？
- 答：两条独立否证。①E075（env-var-remove）根因是「设了 C_INCLUDE_PATH 后，pkg-config 把它当系统头文件路径，在返回 --cflags 时把匹配的 -I 全部过滤掉」，其推荐方案（移除 C_INCLUDE_PATH / LIBRARY_PATH，改用 PKG_CONFIG_PATH 让构建系统自己发现依赖）成立的前提是存在可信的系统 `.pc` 库可铺；本包走手写 SCons、不引任何生成器，交叉环境里没有任何系统 `.pc` 库可探，铺 `PKG_CONFIG_PATH` 也无从探起 ⇒ 只能把该条的结论往前推一层：彻底绕开探测链，由 Conan 逐条显式给 `-I` / `-L` / `-D`。②E151（manually-add-have-defines）的「手动添加缺失的 HAVE_* 定义」正是 `HAVE_SNDFILE_OGG` 的落点——它挂在 `pkg-config --atleast-version=1.0.18 sndfile` 上，而 Conan 的 libsndfile 必带 vorbis/ogg，故改为无条件定义。落点：补丁 `0001`（`conandata.yml:10-12`）与 `conanfile.py` 的 `_depflags()`。
- 追加真错（只补搜索路径不够）：`boost/1.84.0` 把 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 声明在自己组件的 `cpp_info.defines` 上，手写命令行不经过 CMakeDeps / AutotoolsToolchain 就拿不到 ⇒ `boost/core/detail/sp_thread_sleep.hpp:73:5` 报 `use of undeclared identifier 'pthread_setcancelstate'`。`18edb788f9` 起遍历 `self.dependencies` 的 `cpp_info` 与 `components` 把宏一并转发（去重保序）。E507 处理的是同一 OHOS libc 缺口在 CMake 侧的符号探测，本包**未复用其方法**，只同源根因。

### 对话 #3：clang 与 g++ 的两处分歧是警告还是必须改

- 问：`-Wstatic-float-init` 与 `invalid suffix on literal` 都是 g++ 放过的写法，能不能靠编译开关绕过而不打补丁？
- 答：不能，两处都是 clang 的 error 且分处不同阶段。constexpr 那处是**语义**判定（C++ 标准要求 non-integral 静态数据成员的类内初始化写成 `constexpr`），落点 `src/metronome_map.hh` 的 `TICKS_PER_BEAT`、`src/metronome_simple.hh` 的 `MAX_TAP_AGE` 与 `TAP_DIFF` ⇒ 补丁 `0003`，值 / 类型 / 使用点全不变。字面量那处发生在**词法阶段**：`src/tempomap.cc` 里 15 处字符串字面量紧挨 `REGEX_*` 宏名被读成 user-defined string literal，保留拼法在解析出任何类型信息之前就已判死，没有可压的 warning 开关 ⇒ 只能补空白，补丁 `0004`。
- 等价性如何自证（本轮独立复核，脚本 `~/tmp/uc2/klick/checkpatch.py` 直接解析补丁）：`0004` 是 2 个 hunk、10 对 `-`/`+` 行的改写，逐对去掉全部空白后完全相同（`NON_WHITESPACE_DIFF_LINES=0`），`"REGEX_` 相邻计数 15→0，改动行内引号总数 50→50 ⇒ 拼接出的正则表达式文本逐字不变 ⇒ 不改行为，因此不需要版本化开关，也不引入条件编译。

### 对话 #4：可选功能面按什么裁剪，运行级断言压在哪

- 问：OSC 与 Rubber Band 都编不进来，算「无法适配」还是算裁剪交付？
- 答：算按依赖发布态裁剪，且必须给控制组实证。同一 `CONAN_HOME`、同一 remote 下：`boost/1.84.0` 与 `jack/1.9.22` 正常返回 recipe revision，而 `liblo`、`rubberband` 与一个故意写出来的不存在 ref 返回**同一条** `system acceleration policy not enabled` ⇒ 报错形态属「未发布」同类，不是查询姿势错（原文见「功能裁剪（因依赖发布态而裁剪）」节）。据此用上游自带开关 `OSC=0 RUBBERBAND=0`（`RUBBERBAND` 上游默认即 False），不新建「无法适配」Issue；两依赖已入候选池由他窗适配，合入后本包只需翻开关。
- 运行级：沙箱无 jackd、无真实音频设备 ⇒ 会话层不可无头运行。消费者断言压在 server-free 路径（可 exec 证明动态依赖闭包、`-V` 与 `-h` 走 `Options::parse` 早期分支），判决原文 `KLICK_SMOKE_PASS version=1 usage=1 out_dir_removed=1`。`L1e` 会在正照之后对同一 `test_package` 起第二轮负照，一切写盘因此进带 shell-pid 后缀的绝对 `OUT` 目录并 `trap EXIT` 清理（`f99afa181d`），断言数不变。
- 副作用登记：`_prepare_ohos_runtime()` 往归档树写版本号 SONAME 副本，而根 `.gitignore` 的 `*.so` 不覆盖 `*.so.N` ⇒ 见「注意事项」的地雷条目。

### 对话 #5：两级 manifest 的 status 为什么要一起改

- 问：`finish` 已经回写过一次，为什么收口还要人工动 `manifest.yaml`？
- 答：`finish` 只回写版本级 `0.12.2/manifest.yaml`，软件级 `archives/k/klick/manifest.yaml` 不由它维护。W3 跑绿后版本级已是 `built` 而软件级仍是 `pending_ci` ⇒ 同一归档内两级互相打脸，且两级注释都还写着「W3 从未 PASS」这句已被取代的旧判据。收口按 `knowledge/ARCHIVE-SPEC.md` §3 第 256 行的触发条件把软件级同步为 `built`，并把 `versions:` 段的 `status` / `build_date` / `conan_ref` 与版本级逐字对齐（`built` / `2026-09-26` / `klick/0.12.2`）；两处都改成带时间层的写法而不是无痕改写，让「当时取 pending_ci 的判据」仍可回查。
- 边界：⛔ 不在跑绿之前写 `built`，⛔ 不改 §3 的四态定义，⛔ 不为此动根 `.gitignore` 或任何框架文件。
---

**编译结束**: 2026-09-26 16:52
**最终状态**: built
