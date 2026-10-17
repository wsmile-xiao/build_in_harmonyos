- **三方库名称**：libspectre
- **上游版本**：0.2.12
- **上游仓库地址**：https://gitlab.freedesktop.org/libspectre/libspectre/tree/0.2.12
- **适配路径**：路径 B（贡献创新）
- **使用知识库**：新增 `DRAFT-LIBSPECTRE-0.2.12-HARMONYOS-CONFIG-GUESS`，沉淀旧版 Autotools 构建三元组显式指定与 HarmonyOS 消费者渲染验证方法；知识库议题：[Issue #3570](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3570)

关联任务：OHPCD DEP #13639（libspectre 0.2.12）。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游发行源码无 `TESTS`/单元测试注册；`test/Makefile.am` 仅声明 3 个独立程序。取数：`grep -cE '^[[:space:]]*TESTS[[:space:]]*=' Makefile.am test/Makefile.am`，结果 0。 |
| 集成测试 | 0 | 上游未注册集成测试。 |
| 其他测试 | 0 | `make check` 无登记用例；3 个 `noinst_PROGRAMS` 是独立工具，不作为自动化用例计数。 |
| **合计** | **0** | 按实际可执行断言用例计数。 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 未修改上游测试。 |
| 集成测试 | 0 | 不变 | 上游没有自动登记的集成用例。 |
| 鸿蒙特有测试 | 4 | 新增 | HarmonyOS PC 安装消费者检查文档载入、页数、页面尺寸及 Ghostscript 渲染像素缓冲；见 `archives/l/libspectre/0.2.12/test_package/test_package.c`。 |
| **合计** | **4** | **+4** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无自动登记测试用例，适配后补全了消费者测试

- **补全的测试范围**：HarmonyOS PC 上安装链接与 PostScript 文档渲染，共 4 项断言。
- **补全原因**：上游三个测试程序未登记到 `make check`，且渲染示例依赖 Cairo；需补充消费者视角验证 libgs 的目标机运行链路。
- **新增测试文件清单**：`archives/l/libspectre/0.2.12/test_package/test_package.c` — 生成最小单页 PostScript，校验载入状态、页数、页面尺寸和实际渲染输出。

## 验证结果

- 编译状态：通过（HarmonyOS 设备隔离 `CONAN_HOME=$HOME/work/psj/ch-gs14845` 的 `conan create` 退出码 0。configure 输出 `checking for gsapi_new_instance in -lgs... yes` 与 `checking for libgs >= 9.53.0... yes`。日志 `$HOME/work/psj/ls13639/create.log`。）
- 上游测试用例通过率：0/0（100%；发行包没有把 `test/` 登记为 `make check` 的 `TESTS`。设备实际执行 `make check -j1`，输出 `Nothing to be done for 'check'`。3 个 `noinst_PROGRAMS` 不计入。）
- 新增测试用例通过率：4/4（100%；`PASS 1/4` 文档载入，`PASS 2/4` 一页，`PASS 3/4` 页面尺寸为正，`PASS 4/4` Ghostscript 渲染像素缓冲，最终 `HARMONYOS_TESTS=4/4`。）

## 补充说明

- Conan 依赖改为 `ghostscript/10.07.1.1`（依赖 PR #14671，任务 #14845）。该包用官方 10.07.1 源码额外执行 `make so` / `make soinstall`，提供 `libgs.so` 与 `include/ghostscript/iapi.h`。制品仓里的 `ghostscript/10.07.1` 只有 `gs` 命令，没有 libgs，所以旧配方在 configure 报 `You need libgs`。
- 10.07.1.1 尚未进入制品仓。合入顺序必须是先合入并发布 ghostscript #14671，再合入本 PR。在此之前 CI 的依赖可用性门禁失败是预期结果。上面的通过率是设备实跑，不表示 CI 已通过。
- 配方传入 `--build=aarch64-unknown-linux-musl`。构建期把 ghostscript 库目录加入 `LD_LIBRARY_PATH`。补丁把 configure 临时目录 `umask 077` 改为 `022`，并为离树编译增加 `-I$(top_srcdir)`。
- 上游标签 `0.2.12` 对应提交 `44ba3f8291e5640045d501f130f8a4521fc407b3`；发行归档 SHA-256 为 `55a7517cd3572bd2565df0cf450944a04d5273b279ebb369a895391957f0f960`。
- 配方含 `compiler` 与 `build_type` 设置；`archives/l/libspectre/commands.json` 已提供软件索引；本 PR 只包含 libspectre 包和配对知识草稿。
