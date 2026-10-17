## PR 信息
- **三方库名称**：libiconv
- **上游版本**：1.17（适配修订版本：1.17.1）
- **上游仓库地址**：https://www.gnu.org/software/libiconv/；源码：http://ftp.gnu.org/gnu/libiconv/libiconv-1.17.tar.gz
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent；E007（Autotools 平台识别）

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 201 | GNU libiconv 1.17 上游 `make -j1 check` 递归测试套件 |
| 集成测试 | 0 | 上游未单独提供消费者集成测试 |
| 其他测试 | 0 | 无 |
| **合计** | **201** | 上游完整测试，201/201 通过 |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 201 | 不变 | 上游完整测试，201/201 通过 |
| 集成测试 | 3 | +3 | 新增 Conan consumer test_package，验证三种字符集转换 |
| 鸿蒙特有测试 | 0 | 不变 | HarmonyOS 兼容性由 Conan W3 构建和消费者测试覆盖 |
| **合计** | **204** | **+3** | 适配后 204/204 通过 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

本次仅保留上游测试套件并在 Conan `build()` 中执行 `make -j1 check`；未修改 `tests/` 下任何上游测试文件。原有 HarmonyOS 补丁仅更新 `config.guess`/`config.sub` 的平台识别，不改变测试预期。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游没有针对 Conan 消费者运行时链接和 GMime 字符集转换场景的测试，适配后补全了测试
- [ ] **否**，上游已有测试用例覆盖全部本次回归边界

- **补全的测试范围**：新增 3 个消费者集成断言，覆盖 UTF-8→ASCII、EUC-KR→UTF-8、UTF-8→ISO-2022-JP。
- **补全原因**：上游测试验证 libiconv 自身编码表和转换实现，但未验证已发布 Conan 制品中的 libtool 元数据不会误导 Autotools 消费者；该问题在 GMime/test-iconv 和 test-filters 场景中暴露。
- **新增测试文件清单**：
  1. `archives/l/libiconv/1.17.1/test_package/test.c` — 调用 `iconv_open`、`iconv`、`iconv_close` 并逐字节校验三种转换结果。
  2. `archives/l/libiconv/1.17.1/test_package/conanfile.py` — 构建并执行消费者测试程序。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：201/201（100%）
- 新增测试用例通过率：3/3（100%）
- Conan create：通过，recipe `8545618022496ff2c0d87bbd8ac61f86`，package ID `4b977264131a1c74e82bd6bb51b63cc9aadc4cfa`，package revision `fcd1c297e8323d8ba957441b00499c71`

## 补充说明

- 本版本遵循版本策略：`1.17.1` 表示基于上游 `1.17` 的适配修复版本，不声称存在官方 `libiconv 1.17.1` 源码发布。
- 修复内容：打包阶段删除 `lib/*.la`，避免携带构建机绝对路径和 `libdir='//lib'` 的不可移植 libtool 元数据。
- 为兼容 HarmonyOS/HMDFS 的 `umask 077` 行为，配方使用安全的 `mktemp -d` 包装器：保留 `umask 077`，使用 `/dev/urandom` 随机后缀和非 `mkdir -p` 原子创建；未降低临时文件权限。
- 上游测试证据：`archives/l/libiconv/1.17.1/reports/test-report.md`，`make -j1 check` 返回码 0，日志 SHA-256：`559bf1bf2ded1eb47d70b14213a2cde3291fdb922a44befd9feb1ce0c392f18e`。
- Conan/消费者测试证据：同一报告及 Conan create 日志，日志 SHA-256：`31c928621852305a4a41b77a23c99dff0bc96536c7d64a06d57c70636c8e805c`。
- 最终包包含 `libiconv.a`、`libcharset.a`、头文件和 `iconv` 工具，不包含任何 `*.la` 文件。
- 无新增三方依赖。
