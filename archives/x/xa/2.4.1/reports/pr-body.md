- **三方库名称**：xa（上游项目 xa65，6502/R65C02/65816 交叉汇编器）
- **上游版本**：2.4.1
- **上游仓库地址**：https://github.com/fachat/xa65
- **适配路径**：路径 A（基础适配）
- **使用知识库**：ohc 适配流程；参考知识条目 E037/E049（Perl shebang 可移植性）、E017（GitHub 镜像下载）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 35 | 来源：`tests/*/Makefile`（汇编产物/工具输出的逐字节 hex 比对，`tests/hextool`） |
| 集成测试 | 9 | 来源：`tests/*/test.s` + 预期 `ok` o65 二进制比对（`xa` 汇编 + `hextool -cmp`） |
| 其他测试 | 0 | 上游统一由 `tests/harness`（Perl）驱动，`make test` 即同一入口 |
| **合计** | **44** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 35 | 不变 | 上游用例全数保留运行 |
| 集成测试 | 9 | 不变 | 上游用例全数保留运行 |
| 鸿蒙特有测试 | 12 | 新增 | `test_package/test_xa.sh`：六个二进制功能断言（汇编字节比对/o65 生成/链接/重定位/归档往返/BASIC 反汇编） |
| **合计** | **56** | **+12** | 上游 44/44 + 消费者功能 12/12 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 1. **修改的测试文件**：`tests/harness`
>    - **修改原因**：上游 shebang `#!/usr/bin/perl -s` 在 OHOS 上不可执行——系统无 `/usr/bin/perl`（perl 在 PATH 上，如 Harmonybrew userland）；且 Linux 内核对 `#!/usr/bin/env perl -s` 只能把 `perl -s` 作为**单个**参数传给 `env(1)`，toybox `env` 无法拆分。
>    - **修改内容**：shebang 改为 `#!/usr/bin/env perl`，并在脚本开头加入与 Perl `-s` 等价的开关解析（`-tests=/-cc=/-cflags=/-make=/-makeflags=`，解析后从 `@ARGV` 移除）。**测试逻辑、断言、期望产物零改动**；以 `perl -s` 方式调用亦兼容。
> 2. **修改的测试文件**：`tests/hextool`
>    - **修改原因**：同 1（各 `test Makefile` 以 `../hextool -cmp=...` 直接调用该脚本，shebang 失效导致全部二进制比对用例无法执行）。
>    - **修改内容**：同上（`-cmp=` / `-output` / `-noutput` 解析），比较语义仍为逐字节 hex 比对。

> 补丁文件：`patches/0001-tests-harness.patch`、`patches/0002-tests-hextool.patch`（均标注 `patch_type: portability`；无平台宏、无系统前缀注入）。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 上游自带 44 例回归并已全数运行（44/44）。`test_package/test_xa.sh` 的 12 条消费者断言是归档规范要求的安装后功能验证（不属于补全上游空缺），已在测试用例对比表中单列为"鸿蒙特有测试"。

## 验证结果

- 编译状态：通过（`conan create` 干净复现，G0–G4/L2/L4/L5 PASS）
- 上游测试用例通过率：44/44（100%）
- 新增测试用例通过率：12/12（100%）

## 补充说明

- **源码与校验**：`sources.url` 为官方 GitHub tag 归档；sha256 `8fecdb9e64da84eb77d3572e73033bf3d1ca533c7291fb5d0d9735c5440eb67e` 已与 canonical `codeload.github.com` 归档（`github.com/.../archive` 302 的实际目标）逐字节二次核验一致。
- **两级目录布局**：该 tag 归档为 `README + xa/` 结构（项目在 `xa/` 子目录），配方 `source()` 将子目录提升为工程根；此适配点已写入 notes/manifest。
- **安装方式**：上游 `make install` 依赖 `install(1)`（OHOS/toybox 无），`package()` 直接 copy 六个二进制到 `bin/`、六份 man 到 `share/man/man1`，与上游安装内容对齐。
- **产物**：`bin/{xa,file65,ldo65,reloc65,uncpk,printcbm}`（CLI，软件级 `commands.json` 已声明，R38）+ 6 份 man 手册。
- **限制**：上游测试驱动需要 `perl` 在 PATH（设备与 CI 的 GNU userland 均具备）；配方在缺失 perl 时硬失败，不静默跳过上游测试。`printcbm` 自上游 2.4 起标记弃用（功能完整）。
- **许可**：GPL-2.0-or-later（上游 COPYING 原文保留）。
