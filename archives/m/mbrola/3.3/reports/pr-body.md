- **三方库名称**：mbrola
- **上游版本**：3.3
- **上游仓库地址**：https://github.com/numediart/MBROLA
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（仓库适配流程与门禁）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游发布包无 tests/ 目录，无 ctest/pytest 注册 |
| 集成测试 | 0 | 同上 |
| 其他测试 | 0 | Makefile `check/checkold` 依赖私有 `UTILITY_TCTS` 语料，发布包中不存在（`find . -name 'UTILITY_TCTS*'` 为空） |
| **合计** | **0** | 详见 `test_package/MANIFEST.yml` 与 `notes.md` |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 未修改上游 |
| 集成测试 | 0 | 不变 | 上游无集成测试 |
| 鸿蒙特有测试 | 8 | 新增 | `test_package/test_mbrola_consumer.py`：8 组消费者场景、66 条断言，以已发布 `mbrola-gr2` 语音库真实驱动被测二进制 |
| **合计** | **8** | **+8** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无测试用例，适配后补全了测试

> - **补全的测试范围**：CLI 契约与错误退出、`-i` 数据库信息、上游 211 条音素示例的真实合成（WAV/AU/RAW、时长对齐 17264ms、幅度与确定性）、`-t/-v/-f/-l` 运行选项、`-W/-w` ROM 往返与直渲染字节一致、`-e` 错误恢复；共 8 组场景 66 条断言。
> - **补全原因**：上游发布包不含自动化测试；`check/checkold` 依赖的 `UTILITY_TCTS` 语料未随发布包分发，无法运行。
> - **新增测试文件清单**：
>   1. `archives/m/mbrola/3.3/test_package/test_mbrola_consumer.py` — 语义消费者测试驱动
>   2. `archives/m/mbrola/3.3/test_package/test_mbrola_consumer.sh` — bash 包装（CI 运行器以 bash 执行 ELF）
>   3. `archives/m/mbrola/3.3/test_package/conanfile.py` — 测试入口（声明 `mbrola-gr2/0.0.20010521` 为测试数据依赖）

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（上游无自动化测试，原因与证据见上）
- 新增测试用例通过率：66/66（100%）

## 补充说明

- mbrola 3.3 为便携 C89 命令行合成器，无源码补丁；配方仅以 Conan profile 的
  clang 覆盖上游 Makefile 默认的 `gcc -ansi -pedantic`（R33/R9）。
- 源码 URL 使用 GitHub 官方 codeload 下载端点（与 `archive/refs/tags/3.3.tar.gz`
  同一实体，SHA256 一致），`get()` 显式指定 `filename=mbrola-3.3.tar.gz`。
- 消费者测试对运行时数据使用已发布的 `mbrola-gr2`（测试依赖，不计入 PR 变更）。
- L2 冒烟检查（`--version`/`--help`）对上游 CLI 仅提供 `-h` 的情况为非阻塞告警，
  功能验证由 66 条消费者断言覆盖。
