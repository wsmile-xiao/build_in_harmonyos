# abc 0.0.0.20260511 适配笔记

## 编译环境
- 构建系统: makefile（Berkeley ABC，纯 Makefile 项目，无 configure/install 目标）
- 编译日期: 2026-08-07
- 编译器: clang/clang++ (15.0.4)
- 状态: published

## 编译步骤

```bash
# 1. init-build（源码为 GitHub c61f1a04 快照，上游无 release tag）
python3 scripts/ohc-run.py init-build abc 0.0.0.20260511 \
  --url=https://codeload.github.com/berkeley-abc/abc/tar.gz/c61f1a04e9db42db9cea876c1127bfd8f3eab040

# 2. 手动编译（探索阶段）
cd $BUILD_SRC_DIR
make -j2 ABC_USE_NO_READLINE=1
# 功能验证（上游 demo，Arch Linux 同款 check）
./abc -c "r i10.aig; b; ps; b; rw -l; rw -lz; b; rw -lz; b; ps; cec"
#   → Networks are equivalent.  Time = 0.17 sec

# 3. 配方生成与验证
python3 scripts/ohc-run.py conan-init abc 0.0.0.20260511
python3 scripts/ohc-run.py conan-verify abc 0.0.0.20260511
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make: No rule to make target 'readline/readline.h' | readline 为可选依赖，制品仓/预编译包均无 readline | 用 `ABC_USE_NO_READLINE=1` 禁用（Makefile 官方开关） |
| 2 | conan get: BadZipFile: File is not a zip file | codeload URL 末尾是 commit hash 无 `.tar.gz` 后缀，conan 无法推断格式 | 改用 `https://github.com/berkeley-abc/abc/archive/<commit>.tar.gz`（带后缀，sha256 一致） |
| 3 | ConanException: 'tools.build:compiler_executables:c' does not exist | conan 2.29.1 的 conf 是 dict 形式（`tools.build:compiler_executables`），非标量 | 按 bzip2 先例改 `self.conf.get(..., default={}, check_type=dict)` |
| 4 | make: No targets specified and no makefile found | abc 是 in-source 构建，Makefile 在源码根目录 | conanfile.py `self.folders.build = "."` |

## 源码修改

无补丁。探索阶段未修改任何源码文件（readline 通过 Makefile 官方开关禁用，非源码改动）。

## 依赖版本

无第三方库依赖（readline 可选，已禁用）。

## 验证结果

```bash
# 上游 demo 等价性验证：PASS
./abc -c "r i10.aig; b; ps; b; rw -l; rw -lz; b; rw -lz; b; ps; cec"
#   Networks are equivalent.  Time = 0.17 sec

# test_package（conan create L1 测试）
./test_abc  # → PASS: abc ran version command, output: UC Berkeley, ABC 1.01

# conan-verify 门禁
G1-G4 全部 PASS，配方验证通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py + conandata.yml | Conan 配方（Makefile in-source 构建） |
| test_package/ | L1 实质测试（popen 执行 abc -c 'version' 验证） |
| packaging/abc-0.0.0.20260511-ohos-aarch64.tar.gz | release 打包产物 |
| commands.json | 命令行工具声明 (R38) |

## 注意事项

- abc 为命令行工具（逻辑综合），`package_type=application`，`cpp_info.bindirs=["bin"]`，无库文件
- 二进制约 97MB（含 CUDD 决策图支持），全量编译 -j1 约 40 分钟，W3 本地 CI 模拟超时已从 600s 放宽至 3600s（与 i686-elf-binutils 先例一致）
- 版本号 0.0.0.20260511 为 Arch Linux 日期版本，对应 GitHub commit c61f1a04

---

**编译结束**: 2026-08-07 00:02
**最终状态**: published
