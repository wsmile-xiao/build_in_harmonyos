# probcons 1.12 适配笔记 (主理-30, 2026-09-25)

## 路径 B 声明（3+2）

- 适配路径：路径 A（直接适配）+ 路径 B 判定 = create（新增机制见下）
- 使用知识库：复用 E526（conan apply_conandata_patches 经 patch_ng 应用 conandata.yml 补丁声明，draft-review 最高相似 0.19）；K0（2026-09-25）合规走最小补丁路径（主命令名与包名一致，无需包装入口）
- 知识库扩展：DRAFT-probcons-1.12-toybox-patch-cannot-apply-unified-diff-use-conan-patchng——鸿蒙 PC /usr/bin/patch 为 toybox 实现，对字节正确的标准 unified diff 报 Hunk FAILED、自产 diff 回环应用也漂移 ⇒ 补丁一律走 conan 内置 patch-ng；与 E254（dry-run 污染变体）区分且 fallback 方向相反；kv/md 成对随本 PR，draft-review 预审 create
- 关联 Issue：#3354（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3354）

## 适配点

### 1. 编译器：上游 Makefile 烧死 CXX=g++，设备无 g++
- 症状: 设备上 g++ 不存在（clang 15.0.4 位于 /data/service/hnp/bin）。
- 根因: 上游 Makefile 第 11 行 `CXX = g++`（2004 年裸 Makefile，无 PREFIX/无 install 目标）。
- 方案: conanfile build() 传 `make CXX=<profile clang++>`；编译器路径取
  `tools.build:compiler_executables` conf（R33 合规：不依赖 shell 环境变量，含 clang++ 字面回退）。

### 2. 无 install 目标
- 症状: 上游无 install/PREFIX，无法 autotools.install()。
- 方案: package() 将 4 个默认目标（probcons/compare/project/makegnuplot）拷入 `<pkg>/bin`；
  package_type=application，cpp_info.bindirs=["bin"]，随包提供 commands.json（R38）。

### 3. K0：主命令不认 --help/--version
- 症状: 上游 `probcons --help`/`--version` 均 `ERROR: Unrecognized option` + exit 1（无参 usage 也 exit 1）。
- 根因: ParseParams() 无 help/version 分支（2004 年 CLI 风格）。
- 方案: patches/0001-Main.cc.patch (由 finish refresh-patch --auto 从 0001-add-help-version-flag.patch 轮换生成，git 风格 a/ b/ 头需 patch_strip=1) 在 ParseParams 参数循环前加
  -h/--help/--version 分支（exit 0，--version 打印 VERSION 宏）。
  主命令名 probcons == 包名，按 K0 无需同名包装入口。
- 补丁应用: 经 conan 内置 patch-ng（apply_conandata_patches, patch_strip=1）。

### 4. 设备 patch 工具缺陷（平台知识候选）
- 症状: 设备 /usr/bin/patch 为 toybox 实现：对标准 unified diff 报
  `Hunk 1 FAILED`（字节级正确的补丁），对其自身 `diff -u` 产物做回环应用也
  得到内容漂移（ROUNDTRIP_FAIL）。
- 根因: toybox patch 的上下文匹配缺陷（HarmonyOS 设备无 GNU patch）。
- 方案: 补丁一律走 conan 内置 patch-ng（纯 Python），不依赖系统 patch。

### 5. 上游测试三步法（R51）
- 清点: tarball 16 个文件全为源码/头文件，无 tests/ 目录；Makefile 无 check 目标
  （`make -n check` -> No rule to make target 'check'）。无上游自动化测试。
- 实测: test_package 消费者测试执行真实二进制：--version/--help 冒烟（K0）+
  3 条蛋白质序列真实比对（表头数/序列行数/残基字符合法性/行等长 4 项断言），
  共 9 断言，9/9 通过（见 reports/）。

## 环境坑位记录
- /tmp 只读（E002）：探索期测试文件一律放 $TMPDIR($HOME/tmp)。
- clang++ 直编仅产出 -Wdeprecated-copy 警告（SafeVector 用户 provided 拷贝构造），
  无错误，未改上游警告面。

## 五维测试账本
- 静态测试总数（上游声明）: 0（无上游测试面，证据见上）
- 可执行测试数: 9（test_probcons.py 断言：--version 2 + --help 2 + 真实比对 5）
- 实测通过: 9
- 跳过: 0
- 失败: 0
---

**编译结束**: 2026-09-25 02:34
**最终状态**: built
