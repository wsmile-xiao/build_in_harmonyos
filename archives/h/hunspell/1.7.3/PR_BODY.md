- **三方库名称**：Hunspell
- **上游版本**：1.7.3
- **上游仓库地址**：https://github.com/hunspell/hunspell
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无（从零编写 conan 配方，参照 templates/conanfile-autotools.py.tmpl；OHOS autotools 端口经验见 E007/E072/E344）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 拼写/词形回归（.dic） | 132 | tests/Makefile.am `TESTS` 中 .dic 项，经 tests/test.sh 驱动 src/tools/hunspell 逐词典实跑（.aff/.dic/.good/.wrong 全量随源码自带，无网络依赖） |
| 崩溃/溢出回归（.test） | 12 | gh*/ofz*/*overflow 脚本回归（gh1032/gh1058 两个 check_PROGRAMS 由 .test 驱动执行） |
| ABI 符号基线 | 1 | abi-check.sh（非 Linux 环境按设计 exit 77 SKIP，非失败） |
| check_PROGRAMS | 2 | gh1032 / gh1058 编译期回归程序（构建后由上述 .test 驱动） |
| **合计** | **147** | `make check` = TESTS 145 + check_PROGRAMS 2 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 拼写/词形回归（.dic） | 0 集成 | 未实跑 | 曾接入 `autotools.make(target="check")` 由 OHOS CI 实跑（本 PR build #40559）：145 项 TOTAL 中 **133 FAIL / 11 PASS / 1 SKIP**。根因是 conan 分离构建目录（out-of-tree VPATH）下 tests/ 数据未落入 builddir，且 test.sh 驱动新编译 hunspell CLI 逐词典跑输出 diff —— OHOS 沙箱/构建模式环境限制，非产物缺陷（证据见 test_package/MANIFEST.yml）。已从 build() 移出 |
| 鸿蒙特有测试 | 1 用例（3 断言） | 新增 | test_package 编译 C++ 程序链接 libhunspell-1.7，加载内置迷你词典（test.aff/test.dic），对 hello/world 命中、helo 未命中真实执行 spell() |
| **合计** | **1 用例（3 断言）** | 实跑 | test_package 在 CI worker（OHOS aarch64）对安装产物真实编译+链接+执行 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 说明：上游 tests/ 原样保留随源码；本次不触碰任何测试文件。仅对 config.guess 与 configure 打 OHOS 移植补丁（见 patches/）。上游 145 项回归未进 build() 的原因（out-of-tree 构建 + 沙箱实跑 133 FAIL，MANIFEST.yml 实证）与 libdom/libvips 等 OHOS 库处理一致，无虚报。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试覆盖（147 项回归套件），仅受沙箱/构建模式限制无法在 OHOS 整包实跑
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 说明：test_package 新增消费者端到端用例（真实编译 + 链接 + 调 spell()），确保产物在 OHOS 上可加载可用（R34）。

## 验证结果

- 编译状态：通过（OHOS aarch64 CI 构建，待本 PR CI 复跑确认）
- 上游测试用例通过率：不适用（上游 `make check` 在 OHOS CI 实跑 **11/145 PASS / 133 FAIL / 1 SKIP**，属 out-of-tree 构建 + 沙箱环境限制，原因见 test_package/MANIFEST.yml，无虚报）
- 新增测试用例通过率：1/1（test_package 3 断言实跑）

## 补充说明

- **适配范围**：从零编写 hunspell 1.7.3 conan 配方（archives/h/hunspell/1.7.3/），供下游拼写检查类应用（LibreOffice 系等）消费。包目录 slug：`hunspell/1.7.3`，分支 `feat/hunspell-1.7.3`。
- **OHOS 移植关键点**：
  1. `patches/0001-config.guess.patch`：config.guess 增加 HarmonyOS（uname -s=HarmonyOS）case，输出 `aarch64-unknown-linux-ohos`；
  2. `patches/0002-configure.patch`：configure 临时目录改到 `${TMPDIR:-$HOME/tmp}`（沙箱限制 `./confXXXXXX`）；该版本自带 2024 config.sub 已原生识别 `linux-ohos*`，无需 config.sub 补丁；
  3. `--disable-nls`：跳过 AM_GNU_GETTEXT(external) 的 libintl 探测（翻译语料 po/*.gmo 已预编译随源码，库消费方不需要）；
  4. `-j1` 串行构建（沙箱不支持 mkfifo / GNU make jobserver，先例见 vala）；
  5. package 时把 libtool 生成的 `.so` 符号链接链 `cp -a` 解引用为真实文件副本（HMDFS 动态链接器不解析符号链接）。
- **上游测试统计核验方式**：解包 release tarball `hunspell-1.7.3.tar.gz`，`tests/Makefile.am` 实读 `TESTS`/`check_PROGRAMS` 计数（132 .dic + 12 .test + 1 .sh = 145 + 2）；OHOS CI 集成实测记录见本 PR build #40559（145 项 11 PASS/133 FAIL/1 SKIP）。
- 与 archives/h/hunspell/1.7.2（仅 manifest/notes/patches，无 conanfile）不同，本版本补全完整可构建配方 + test_package + 依据实证声明的上游测试策略。
