【依赖项】feat(zxcc): 适配 zxcc 0.5.7 到鸿蒙PC aarch64-linux-ohos

- **三方库名称**：zxcc（CP/M 2/3 模拟器与交叉开发工具链包装器）
- **上游版本**：0.5.7
- **上游仓库地址**：https://github.com/agn453/ZXCC（tag 0.5.7；官网 https://www.seasip.info/Unix/Zxcc/）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：build_in_harmonyos SKILL（E007 autotools 平台识别、E490 autotools 脚本执行位、E540 构建环境知识，conan-verify 知识图谱 G0/G2 预检）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 源码树无 tests/ 目录，顶层/cpmio/cpmredir/Z80/bin 五个 Makefile 均未定义 TESTS |
| 集成测试 | 0 | 无 |
| 其他测试 | 0 | `make check` 真机实测：五个子目录全部 "Nothing to be done for 'check'" |
| **合计** | **0** | R51 三步法（清点→运行→回填）实测确认 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | |
| 集成测试 | 0 | 不变 | |
| 鸿蒙特有测试 | 3 | 新增 | test_package/test_zxcc.py 真实执行型冒烟测试：① `zxcc` 无参运行（校验 "No CP/M program name provided." 用法提示，覆盖 BIOS 数据加载与参数解析启动路径）；② `zxas` 无参运行（经 PATH 解析 zxcc 包装器，校验 bindirs 与工具间互调装配）；③ 五个打包工具（zxcc/zxc/zxas/zxlink/zxlibr）存在且可执行检查 |
| **合计** | **3** | **+3** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例（上游本无测试用例）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无测试用例，适配后补全了测试

> - **补全的测试范围**：test_package/test_zxcc.py 真实执行型冒烟测试 3 项（R34：实际执行打包产物；L1e 破坏性反向验证确认测试真实依赖被测包；R38/PF8：命令行工具软件级 commands.json 已声明）
> - **补全原因**：上游为 2001 年代的 CP/M 模拟器项目，仅交付可执行工具与数据文件，无任何测试框架/测试目标（R51：上游 0 用例必须自行补齐）；CI 首轮 L0c 门禁检出 test_package 缺测试源文件，已补独立测试脚本 test_zxcc.py
> - **新增测试文件清单**：
>   1. `archives/z/zxcc/0.5.7/test_package/test_zxcc.py` — 独立测试脚本：真实执行打包产物 zxcc/zxas + 五工具存在性/可执行性检查
>   2. `archives/z/zxcc/0.5.7/test_package/conanfile.py` — test() 以 conanrun 环境调度 test_zxcc.py（注入 ZXCC_TEST_BINDIR）
>   3. `archives/z/zxcc/0.5.7/test_package/MANIFEST.yml` — R51 上游测试三步法申报（0 用例证据 + 补全说明）

## 验证结果

- 编译状态：通过（ohc-run.py conan-verify：G0/G1/G2 + L2 平台 smoke + L4 checksec + L5 产物基线 全部 PASS）
- 上游测试用例通过率：0/0（上游无测试用例，N/A）
- 新增测试用例通过率：3/3（100%，本机完整 CI 实测：L0 全过 / L1 pass / L2 pass / L5 pass，L1e 反向验证确认）
- 二进制产物：bin/{zxcc,zxc,zxas,zxlink,zxlibr} + lib/{libcpmio.a,libcpmredir.a} + lib/cpm/bin80/bios.bin

## 补充说明

- **补丁内容**（`patches/0001-autotools-ohos-support.patch`，9 文件，无 `__OHOS__` 宏注入，满足 PF5）：
  1. config.guess×3（整文件升级至现代版 + HarmonyOS `*:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos` 分支）；config.sub×3（aarch64 + `-linux-ohos*` 识别）
  2. configure×3：`umask 077 && mktemp -d` → `mktemp -d`（HMDFS 上私有 umask 目录属主权限位丢失导致 config.status 写入失败）
- **配方级平台处理**（不改上游源码，见 conanfile.py build()/generate()）：
  - cpmio configure 硬编码探测 `-lncurses`，而 ncurses/6.5 包仅提供 libncursesw.a → conanfile 建立 compat-lib 符号链接目录并手动注入 -I/-L
  - OHOS /bin/sh 为 mksh：configure 在 mksh 下探测出 korn-shell 能力，生成的 libtool 含 mksh 专有语法 → configure/make 全程以 bash 运行，并对生成的 libtool 做后处理（shebang、archive_expsym_cmds 引号重建、`print -r --` → `printf %s\n`）
- **源码包说明**：conandata.yml 使用 GitHub 官方仓库 tag 源码包（seasip.info 对 gzip 响应带 Content-Encoding，conan requests 客户端自动解压导致 sha256 校验不稳定）
- **运行依赖**：ncurses/6.5（制品仓已发布）；运行真正的 CP/M 编译需用户自行安装 CP/M 侧 Hi-Tech C 编译器文件至 `<prefix>/lib/cpm/{bin80,lib80,include80}/`
- **分支**：`feat/zxcc-0.5.7`（已推送 fork，提交 af019999f / cb6516fe1），归档目录 `archives/z/zxcc/`
- **CI 首轮失败修复**：PR #11635 首轮 CI 于 L0c 门禁失败（test_package 缺测试源文件）→ 补独立测试脚本 test_zxcc.py 并经本机完整 CI（setup.sh + build_and_test.sh）验证全绿后推送
