## PR 信息

- **三方库名称**：Gauche
- **上游版本**：0.9.15（OpenHarmony Conan 发布版本：0.9.15.1）
- **上游仓库地址**：https://github.com/shirok/Gauche
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 39,319 | 上游 `make -j1 check` 实际汇总的断言数量 |
| 集成测试 | 0 | 上游未单独标识可独立统计的集成测试类别 |
| 其他测试 | 0 | 未将示例程序计入测试用例 |
| **合计** | **39,319** | 通过上游统一入口 `make -j1 check` 实际执行 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|-------------|------|
| 单元测试 | 39,319 | 不变 | 上游 `make check` 记录为 39,309 通过、10 失败、2 中止 |
| 集成测试 | 0 | 不变 | 无独立集成测试分类 |
| 鸿蒙特有测试 | 1 | 新增 | Conan `test_package` 的 `test_gauche` consumer test |
| **合计** | **39,320** | **+1** | consumer test 不计入上游通过率 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

适配修改仅涉及 OHOS 构建输入、Boehm GC 兼容性和核心子目录构建；未修改上游测试脚本或生成构建文件。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，补充了 1 个 Conan consumer test

- **补全的测试范围**：验证 `gosh` 可执行文件、Gauche 头文件和 `libgauche` 链接/运行。
- **补全原因**：作为包级 smoke test，覆盖已安装 Conan 包的核心解释器和 C API 消费场景。
- **新增测试文件清单**：
  1. `archives/g/gauche/0.9.15.1/test_package/test.c` — consumer test。
  2. `archives/g/gauche/0.9.15.1/test_package/conanfile.py` — Conan 测试入口。

## 验证结果

- 编译状态：通过。`finish` 于 2026-08-13 11:31 自动完成 W3 本地 CI 验证，生成 `.ci-result.json`，退出码为 0。
- 上游测试用例通过率：39,309/39,319（99.9746%）；10 失败，2 中止。
- 新增测试用例通过率：1/1（100%）。该 Conan consumer test 断言 C API 求值结果为 `6`，并运行包内 `gosh`。

已执行的完整上游验证命令：

```text
make -j1 check
```

完整套件实际执行后未全量通过。剩余 10 个失败和 2 个中止来自当前 HMDFS 测试环境的系统能力边界，未修改上游测试或 Gauche 运行时逻辑来掩盖它们：

- Unix-domain socket：`bind` 返回 `Operation not permitted`，后续 client `connect` 失败，影响 `net.scm` 的本地 socket 测试。
- 文件权限语义：HMDFS 对复制文件的 mode 处理与 POSIX 断言不同，影响 `ext/file` 的 `copy-file` 权限测试。
- 终端控制：PTY 上 `tcdrain` 与 `tcflow` 返回 `Permission denied`，影响 `ext/termios` 测试。
- 脚本执行语义：上游 `scripts.scm` 的解释器名称、file-to-file、files-to-directory 和 `-T` 场景依赖 HMDFS 不提供的可执行文件与权限行为。

## 补充说明

- CI 源码使用官方 Gauche 归档 `https://practical-scheme.net/vault/Gauche-0.9.15.tgz`，并校验 SHA-256 `3643e27bc7c8822cfd6fb2892db185f658e8e364938bc2ccfcedb239e35af783`。
- 最终配方跳过未在 OHOS 完成动态加载适配的 `ext/` 目录；因此不声称完整上游测试在当前发布包中可用。
- 未发现需要先发布的 Conan 依赖。
