# smemstat 0.02.13 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4（OHOS aarch64，profile `tools.build:compiler_executables`）
- 状态: built
- worktree: `~/qzy/GLM-53-smemstat-0.02.13`（分支 `feat/smemstat-0.02.13`，基线 e321afdc8c）
- CONAN_HOME: `~/tmp/ch/home-glm53-smemstat`

## W0 / W0b 记录
- W0 preflight：初跑无依赖声明；读 Makefile 发现硬链接 `-lm -lncursesw` → 依赖 **ncurses**。
  制品仓实查 `ncurses/6.4|6.5|6.6`（`conan list ncurses/* -r=ohpcd`），配方级验证
  `conan download ncurses/6.6 -r=ohpcd --only-recipe` 通过，conan create 实际解析安装二进制通过（R35 口径）。
- W0b：归档树无 smemstat 历史归档/notes（全新适配）；`lang-preflight` 通过（C，milestone=lang_checked）。
- 上游 URL：https://github.com/ColinIanKing/smemstat（tag V0.02.13）
  sha256=0c0caf1ee9a0c0c4a840c0d01836bc4ea59d715e4df03cc3f24960c8e4009044（本地实算，conandata.yml/manifest/正文同源）。

## 编译步骤
1. `make -C <src> -j2 CC=<profile clang> CFLAGS='-O2 -fPIC -DVERSION='"'"'"0.02.13"'"'"' -I<ncurses include>' LDFLAGS='-L<ncurses lib>' smemstat`
   （命令行 CFLAGS 完整重供：make 命令行变量会令 Makefile 的 `CFLAGS +=` 追加失效，
   其中含上游的 `-DVERSION='"$(VERSION)"'` 版本宏，引号形态必须保留到编译器）
2. ncurses/6.6（ohpcd 制品仓静态宽字符构建，libs=formw/menuw/panelw/ncursesw）提供 libncursesw。
3. 不做 `make install`（HMDFS install-sh/chmod 类问题，dhcpoptinj/0.5.3 先例），
   package() 纯 Python 拷贝：bin/smemstat、share/man/man8/smemstat.8、
   share/bash-completion/completions/smemstat、licenses/COPYING。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G2 首跑 `AttributeError: '_Component' object has no attribute 'package_folder'` | Conan2 依赖 cpp_info 聚合对象无 package_folder 属性 | 改用依赖 conanfile 的 `package_folder` 属性拼接 includedirs/libdirs（含绝对路径回退） |
| 2 | Makefile `CFLAGS +=` 携带 `-DVERSION`，命令行传 CFLAGS 会静默关闭追加 | GNU make 命令行变量优先级高于 Makefile 内赋值（含 +=） | 命令行完整重供 CFLAGS，版本宏按上游引号形态 `-DVERSION='"0.02.13"'` 传入 |
| 3 | 依赖 ncurses 登记表备注误标"无外部依赖" | 备注由 SCT 按 README 粗判 | 以 Makefile 链接行为为准，ncurses/6.6 已在制品仓，直接 requires |

## 源码修改

无补丁（patches: {}）。`apply_conandata_patches(self)` 显式调用保留。

## 依赖版本

- ncurses/6.6（ohpcd 制品仓，静态 wide 构建）
- 系统 libm（OHOS sysroot）

## 测试账本（五维，R51）

| 维度 | 数值 | 依据 |
|---|---|---|
| N_static 上游静态用例 | 0 | 无 tests/ 目录；Makefile 无 check/test 目标；tarball 无 CI 测试配置；smemstat.c 无测试框架字符串（详见 test_package/MANIFEST.yml 审计） |
| N_registered | 0 | 同上 |
| N_executed | 0 | 上游无测试可执行 |
| 未执行分类 | 0 | 不存在上游用例 |
| N_consumer 消费者测试 | 1 程序（3 用例） | test_smemstat：`-h` 用法+版本断言、`-k 1 1` 单次快照真实采集 /proc、`-Z` 非法选项失败路径；实测 3/3 PASS（conan-create.log HMBS 标记） |

## 路径 B 判断

- 结论：**走路径 B**（知识库扩展）。
- 主题：纯 Makefile 项目在 conan 配方 build() 中的命令行变量覆盖陷阱——
  `CFLAGS +=` 被 CLI 变量静默关闭导致上游 `-DVERSION` 宏丢失。
- 查重：`knowledge/graph/index.tsv` 无同主题条目（E063 仅 -Werror 场景）。
- 真实触发证据（本任务复现）：
  - 缺 -DVERSION：`smemstat.c:1511:13: error: use of undeclared identifier 'VERSION'`
  - 裸值无引号：`smemstat.c:1511:13: error: invalid suffix '.13' on floating constant`
- 已验证方案：命令行完整重供 CFLAGS + 上游引号形态（本配方 conan-verify G1-G4/L2/L4/L5 全绿，消费者 3/3）。
- 跨仓库复用价值：make 型构建占归档语料 ~21%，凡 Makefile 用 `+=` 注入版本宏/标志的包均适用。
- 草稿：knowledge/drafts/ 下同 stem .kv/.md（见本 PR），经真实解析器与 draft-review。

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify smemstat 0.02.13
# G1 PASS / G0 PASS / G2 conan create PASS / G3 PASS / G4 产物完整 / L2 smoke 可执行 / L4 / L5 全绿
# 消费者测试 test_smemstat 3/3 PASS（HMBS_TEST_PACKAGE_RESULT passed=true passedCount=3）
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/smemstat | 主程序（静态链接 libncursesw） |
| share/man/man8/smemstat.8 | 手册页 |
| share/bash-completion/completions/smemstat | 补全 |
| licenses/COPYING | GPL-2.0 |

## 注意事项

- OHOS 真机上未签名 ELF 不可直接执行；conan-verify L2 smoke 已按设备签名流程执行通过。
- 平台写操作与 CI/AI 闭环记录见 PR 正文与 result.json（OHC_RESULT_OUT 任务私有路径）。
---

**编译结束**: 2026-09-18 02:54
**最终状态**: built
