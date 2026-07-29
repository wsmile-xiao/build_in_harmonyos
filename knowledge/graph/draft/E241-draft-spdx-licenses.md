# E241 - 数据/规则清单型库在 OHOS 上的固定版本、hash 完整性、规则查询和精确输出比对方法

## 使用说明

当适配 OpenHarmony PC 平台的数据/规则清单型上游库（无 C/C++ 编译、无 autotools/cmake/meson、无传统测试套件）时使用本条目。本条目以 spdx-licenses 3.28.0（SPDX License List Data）为例，说明完整的数据包适配模式。

## 适用范围

- SPDX License List 数据包（licenses.json + exceptions.json）
- IANA 协议/服务名数据
- Unicode 字符数据库
- 时区数据（tzdata）
- CA 证书列表
- 任何以 JSON/数据文件为主要产出的上游项目

## 输入定义

- 上游 tarball 下载 URL
- 官方发布页的 SHA256 校验和
- 核心数据 JSON 文件
- 数据版本号、条目总数、已弃用条目数等统计信息
- 预期查询成功/失败的规则 ID

## 输出定义

- `conandata.yml`：固定源码 URL + SHA256
- `conanfile.py`：数据包配方（无 settings、无 package_type）
- `test_package/conanfile.py`：通过 `self.run()` 调用独立测试脚本
- `test_package/test_<name>.py`：独立测试脚本（含 hash 校验、版本校验、计数校验、正例/负例查询）
- 固定 JSON 摘要（`<name>-<version>-summary.json`），用于 CI 精确比对

## 错误特征

```text
# CI L0c: No test source files in test_package/
# CI L0d: test() method has no self.run() call — likely a stub
# CI L0k: CLI tool detected but commands.json missing (R38)
```

## 根因

OpenHarmony PC 适配中遇到一类没有 C/C++ 源码、不需要编译的纯数据/规则清单型上游库。传统 CMake/Autotools Conan 模板不适用于此类库。CI 默认检查（test_package 需有非 conanfile.py 的源文件、test() 需含 self.run() 调用）需要针对数据包特点做调整。

## 解决步骤

### 1. 源码包完整性

```bash
curl -fSL -o v3.28.0.tar.gz https://github.com/spdx/license-list-data/archive/v3.28.0.tar.gz
sha256sum v3.28.0.tar.gz
# 结果: 52375a91b28b5f6f3142c4b3a555086482f1e09be68c4fa7fdbf377d37afa340
```

### 2. conanfile.py 核心配置

- `settings = None`（不依赖编译器/架构）
- 不设置 `package_type`（避免 CI 误判为 CLI 工具）
- `export_sources()` 调用 `export_conandata_patches(self)`（G1 门禁要求）
- `build()` 以 `apply_conandata_patches(self)` 开头（G1 门禁要求），然后执行数据完整性校验
- `package()` 将 JSON 数据复制到 `res/` 目录

### 3. 核心数据校验（build() 中执行）

```python
# 校验 licenseListVersion
assert data["licenseListVersion"] == "3.28.0"
# 校验总数
assert len(licenses) == 727
# 校验已弃用数
assert len(deprecated) == 32
# 校验已知 ID 存在
assert "MIT" in license_ids
# 校验非法 ID 不存在
assert "NOT-A-REAL-SPDX-ID" not in license_ids
```

### 4. test_package 结构

test_package/ 必须包含非 conanfile.py 的源文件（py/sh），且 test() 方法使用 self.run()：

```
test_package/
├── conanfile.py       # 通过 self.run() 调用测试脚本
├── test_spdx.py       # 独立测试脚本（L0c 门禁要求）
└── MANIFEST.yml       # 测试声明文件
```

### 5. 固定 JSON 摘要输出

test_package 在验证完成后输出固定结构的 JSON 摘要文件，包含：
- 版本号、总数、已弃用数等统计值
- 全部已知 ID 的查询结果
- 全部核心数据的 SHA256 校验和
- 最终状态（ALL_PASSED/FAILED）

示例：`spdx-licenses-3.28.0-summary.json`

## 验证证据

| 检查项 | 期望值 | verify |
|--------|--------|--------|
| v3.28.0.tar.gz SHA256 | 52375a91b28b5f6f3142c4b3a555086482f1e09be68c4fa7fdbf377d37afa340 | sha256sum |
| json/licenses.json SHA256 | f728c534d8bd1044fc515a2ddb2292be99559021d830bfa3281be0bcd36302ee | sha256sum |
| json/exceptions.json SHA256 | bd145bb558f44432fcd6f0d7e956ed0124dff72af7641a7cfcb1b557dc390a5b | sha256sum |
| licenseListVersion | 3.28.0 | JSON 解析 |
| 许可证总数 | 727 | JSON 解析 |
| 已弃用许可证 | 32 | JSON 解析 |
| 异常总数 | 84 | JSON 解析 |
| 已弃用异常 | 1 | JSON 解析 |
| MIT 查询 | FOUND | JSON 查询 |
| Apache-2.0 查询 | FOUND | JSON 查询 |
| BSD-3-Clause 查询 | FOUND | JSON 查询 |
| GPL-2.0-only 查询 | FOUND | JSON 查询 |
| NOT-A-REAL-SPDX-ID 查询 | NOT FOUND | JSON 查询 |
| conan create | PASS | exit code 0 |
| conan-verify (G1/G2/G3/G4) | PASS | verify report |
| W3 本地 CI | PASS | setup.sh + build_and_test.sh |

## 禁止做法

- 为数据包设置 `package_type = "application"`（CI 会误判为 CLI 工具并要求 commands.json）
- 设置 `settings` 为 os/compiler/arch 等（数据包不依赖架构）
- test_package 中只有 conanfile.py 没有独立测试脚本（L0c 不通过）
- test() 方法中没有 `self.run()` 调用（L0d 不通过）
- test() 中只做 assert/print 不调用 self.run()（CI 视为 stub）

## 关联条目

- E221：Conan test_package 的显式运行与环境
- R38：CLI 工具命令声明
- R26：系统同名库静态链接
- CI L0c：test_package 中必须有非 conanfile.py 的源文件
- CI L0d：test() 方法必须有 self.run() 调用
