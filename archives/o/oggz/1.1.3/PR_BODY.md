- **三方库名称**：oggz
- **上游版本**：1.1.3
- **上游仓库地址**：https://www.xiph.org/oggz/ （源码 https://downloads.xiph.org/releases/liboggz/liboggz-1.1.3.tar.gz）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（SKILL.md v11.6）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 24 | 来源：`src/tests/` 目录（CUnit/手写 main 各系列：comment/io-count/write-read/seek-stress 等） |
| 集成测试 | 0 | 无 |
| 其他测试 | 0 | — |
| **合计** | **24** | 上游通过 `make check` 调用 libtool wrapper 执行 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 24 | 不变 | 上游 `src/tests/` 24 个测试二进制经 conan create 阶段直接运行全部通过（comment/io-count/write-*/read-*/seek-stress 等） |
| 集成测试 | 0 | 不变 | — |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/test.c` 真实调用 liboggz 写读 API 验证 OHOS 平台产物可加载运行 |
| **合计** | **25** | **+1** | 新增鸿蒙平台写读往返 smoke test |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例（仅在 conanfile.py 的 `package()` 中新增 OHOS ELF 签名步骤与 `rm *.la` 清理）

> 适配采用「平台仅影响构建层」策略：3 个 patch 全部作用于 `config.guess` / `config.sub` / `configure`（临时目录），不触动 `src/tests/` 内任何代码。上游 24 个测试在 conan create 阶段以可执行二进制形态直接运行（绕开 libtool wrapper 沙箱限制）全部 PASS。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖

> 上游提供 24 个测试程序（src/tests/）。补全的 1 个 test_package 用例属于**消费方集成测试**（Conan L1），非上游缺失补充。

## 验证结果

- **编译状态**：通过
- **上游测试用例通过率**：24/24（100%，conan create 阶段直接运行所有测试二进制）
- **新增测试用例通过率**：1/1（100%，ctest 1/1 Passed in 0.03s）
- **conan-verify 8 道门禁**：G0 / G1 / G2 / G3 / G4 / L2 / L4 / L5 全部 PASS
- **CI 集成验证**：`finish` step [5/9] 通过，写入 `.ci-result.json`（exit_code 0, integrity_hash=eedb7891d119c2a7）

## 补充说明

### 平台适配要点（路径 A 基础适配）

1. **config.guess / config.sub** 增加 HarmonyOS 三元组支持（补丁 0001 / 0002）
   - `uname -s = HarmonyOS` → `aarch64-unknown-linux-ohos`
   - 复用 `patch-autotools-ohos.pl` + `linux-ohos*` kernel/OS 白名单
2. **configure 临时目录** 修复（补丁 0003）
   - `mktemp -d ./confXXXXXX` 在 OHOS HMDFS 不可写（E002）→ 改为 `mkdir -p`（与 flac 同款修复）
3. **依赖**：`libogg/1.3.6.1`（系统同名库，强制静态消费，R26 / R36 已发布）
4. **源码解压**：`conan get(strip_root)` 遇 tarball 顶层 `PATCHES` 文件与导出 `patches/` 目录在大小写不敏感沙箱 FS 冲突（IsADirectoryError），改为手动 `tarfile` 解压并跳过 `PATCHES`
5. **运行时签名**：所有 `bin/` ELF 经 `binary-sign-tool` 注入 `.codesign` 段（OHOS XPM 加载器要求）
6. **路径污染防护**：coreutils shim 在 `$DEFAULT_PREFIX/bin` 抢占 PATH 破坏 conan 内 configure heredoc/管道（E540），`build()` 用 python subprocess + 固定 PATH 驱动

### 交付物

- `archives/o/oggz/1.1.3/conanfile.py`（236 行, R1/R26/R32/R33/R34 全部到位）
- `archives/o/oggz/1.1.3/conandata.yml`（官方源 URL + sha256 + 3 补丁）
- `archives/o/oggz/1.1.3/patches/0001-config.guess.patch`（OHOS 三元组识别）
- `archives/o/oggz/1.1.3/patches/0002-config.sub.patch`（OHOS kernel/OS 白名单）
- `archives/o/oggz/1.1.3/patches/0003-configure.patch`（临时目录 mkdir 化）
- `archives/o/oggz/1.1.3/test_package/{conanfile.py, CMakeLists.txt, test.c, MANIFEST.yml}`
- `archives/o/oggz/commands.json`（13 个 CLI 工具声明，R38 hicmd 格式）
- `archives/o/oggz/1.1.3/{manifest.yaml, notes.md, reports/conan-verify-report.md, .ci-result.json}`

### 已知限制

- 状态为 `built`：conan-verify 通过，但本子任务（compile-collaborator）不做 `conan upload` / push；制品位于本地 conan 缓存
- 上游 `make check` 中的 `httpdate_test` 因 libtool wrapper + HMDFS getcwd 环境无法经封装执行（环境限制，非代码缺陷），但 24 个测试以**直接调用可执行文件**方式均已通过

### 相关铁律 / 知识条目

- **遵循** R1 / R4 / R5 / R6 / R18 / R26 / R32 / R33 / R34 / R35 / R36 / R37 / R38 / R39 / R40
- **遵循规程** W0（依赖检查）/ W1（同步 main）/ W2（结构完整性）/ W3（finish 阻塞验证）/ W5（graph validate 通过）
- **命中知识** E002（mktemp/HMDFS）、E007（config.guess）、E072（config.sub）、E490（autotools 权限，未触发）、E540（PATH shim）
