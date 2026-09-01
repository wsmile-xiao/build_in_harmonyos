# xxhash 0.8.2 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure 步骤）
- 编译日期: 2026-08-31
- 编译器: clang 15.0.4（aarch64 + NEON，HarmonyOS）
- 状态: built（本地验证全通过，待 CI/release）

## 编译步骤

1. `init-build` 获取上游 v0.8.2 tarball（sha256 `baee0c6a…79c4`）
2. `lang-preflight`：检测为 cpp（C 主体 91%），通过
3. 探索编译（源码目录直接 make）：
   ```bash
   make -j2                       # 生成 libxxhash.a / libxxhash.so.0.8.2 / xxhsum
   make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX
   ```
4. 上游测试全量执行：
   ```bash
   make check            # sanity_test 49948 断言 + xxhsum CLI 10 组
   make test-xxhsum-c    # 65 组命令行校验/校验和/错误路径
   make test-unicode     # Unicode 文件名 2 项
   ```
5. 固化配方：`conan-init` → 修正 conandata.yml/conanfile.py → `conan-verify`
   （conan create + test_package 消费者测试 1/1 通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make install` 报 `No rule to make target 'install'` | Makefile:498 `ifneq(filter Linux Darwin …, $(UNAME))` 白名单不含 HarmonyOS，整个安装规则段未定义 | 补丁①：UNAME filter 追加 `HarmonyOS`（知识草稿 E257） |
| 2 | `make: install: No such file or directory` (Error 127) | 系统无 GNU install 命令（E108 已知模式） | 补丁②：HarmonyOS 分支 `INSTALL=cp -p`、`INSTALL_DATA=cp -p`、`INSTALL_DIR=mkdir -p` |
| 3 | conan create 首跑 `KeyError: '0.8.2'` | conan-init 生成的 conandata.yml sources 为平铺结构，recipe 用 `conan_data["sources"][self.version]` 索引 | conandata.yml 改为 `sources: {"0.8.2": {url, sha256}}` 版本键结构 |
| 4 | conan make 报 `No targets specified and no makefile found` | Conan basic_layout 下 build folder 与 source folder 分离，Makefile 在 source folder | make/install 均追加 `-C $(self.source_folder)` |
| 5 | test_package 运行时 `Error loading shared library libxxhash.so.0` | shared=False 语义下 recipe 需只产静态库，但 make install 仍装了 .so，消费者链接到动态库 | build/package 按 `self.options.shared` 分支：静态时仅构建/安装 `libxxhash.a` + headers + pc |
| 6 | conan-verify 结束后 conandata.yml 被还原成损坏结构 | verify 的镜像注入回滚逻辑把「崩溃残留快照」当原始内容恢复 | 验证后手动重写正确内容；.ghfast-bak/.orig 残留删除（勿入 PR，JC1 会拦） |

## 源码修改

- `patches/0001-Makefile.patch`（+14/-1，platform_only）：
  1. UNAME filter 白名单追加 `HarmonyOS`（install 段生效）
  2. HarmonyOS 分支 INSTALL/INSTALL_DATA/INSTALL_DIR 用 cp/mkdir 替代 GNU install
  3. `install_libxxhash.includes` 目标内 HarmonyOS 分支用 `mkdir -p`

## 依赖版本

无（零依赖库，仅 libc）

## 验证结果

```bash
# 上游测试（全部通过，无跳过）
make check          → OK. (passes 49948 tests) + 10 组 CLI 检查 "checks completed successfully"
make test-xxhsum-c  → 65 组命令全部通过（含 FAILED/错误路径退出码断言）
make test-unicode   → 2 项通过

# Conan 验证
conan create … --build=missing   → Package created（b7707b67…/1382ffc6…）
test_package (test.c: XXH32/XXH64/XXH3_64bits 实际计算) → 1/1 Passed

# 产物冒烟
$TEST_PREFIX/usr/local/bin/xxhsum --version
→ xxhsum 0.8.2 by Yann Collet, compiled as 64-bit aarch64 + NEON little endian
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libxxhash.a | 42576 B | 静态库（shared=False 默认产物） |
| libxxhash.so.0.8.2 | 51520 B | 共享库（shared=True 时安装） |
| xxhsum (+xxh32/64/128sum) | 84416 B | CLI 工具（含 3 个符号链接） |
| xxhash.h / xxh3.h | — | 头文件 |

## 注意事项

- 上游 `make test-mem` 依赖 valgrind，设备无此工具；它不属于上游 `make check` 默认路径，未纳入统计。
- xxhash 属系统同名库风险场景外的普通库，无需 R26 强制静态；但配方默认 shared=False，test_package 必须静态链接才能运行。
- conandata.yml 必须保持「版本键 + patches 版本键」双层结构；任何工具改写后提交前需人工复核（本次 conan-verify 回滚机制两次破坏过该文件）。
- 制品仓已有 `xxhash/0.8.3`（另一上游版本，非本配方冲突）；本配方为 0.8.2 首次适配，无同版本 revision 冲突，按 R37 用上游版本号 0.8.2。
- 本包为命令行工具（xxhsum）+ 库混合产物；R38 commands.json 由 CI L0k 门禁校验，见软件级目录声明。
---

**编译结束**: 2026-08-31 14:38
**最终状态**: published
