# 三方库测试质量规范

## 1. 目标

作为新平台（HarmonyOS），每个三方库必须通过**上游官方完整测试套件**才能发布。
本文档定义 CI 强制执行的质量门禁标准，适配组必须遵守。

## 2. 三层测试体系

```
┌─────────────────────────────────────────────────────────────┐
│  层 1: 上游官方测试 (upstream make check)                    │
│  位置: conanfile.py → build() 方法末尾                       │
│  执行者: conan create (自动)                                 │
│  作用: 在源码编译目录中运行上游完整测试套件                   │
│  结果: 失败则 conan create 失败 → 构建失败                   │
├─────────────────────────────────────────────────────────────┤
│  层 2: test_package (消费者视角验证)                         │
│  位置: test_package/conanfile.py → test() 方法               │
│  执行者: conan create (自动, 在层 1 之后)                    │
│  作用: 验证产出的库/二进制可以被正确链接和使用                │
│  结果: 失败则 conan create 失败 → 构建失败                   │
├─────────────────────────────────────────────────────────────┤
│  层 3: CI 门禁 (build_and_test.sh)                           │
│  位置: CI pipeline                                           │
│  作用: 5 层防御, 防止偷懒绕过测试                            │
│  结果: 任一门禁失败 → CI 构建失败, PR 无法合入               │
└─────────────────────────────────────────────────────────────┘
```

## 3. 层 1：上游官方测试 (必做)

### 3.1 在 conanfile.py 的 build() 中集成 make check

构建完成后，**立即**在同一个编译目录中运行上游测试。

**Autotools 项目** (bash, coreutils, sed 等):
```python
def build(self):
    autotools = Autotools(self)
    autotools.configure()
    autotools.make()
    # ── 上游官方测试 ──
    autotools.make(target="check")
```

**Makefile 项目** (zlib 等):
```python
def build(self):
    self.run("./configure --static --prefix=/")
    self.run("make -j1")
    # ── 上游官方测试 ──
    self.run("make check")
```

**CMake 项目**:
```python
def build(self):
    cmake = CMake(self)
    cmake.configure()
    cmake.build()
    # ── 上游官方测试 ──
    cmake.test()  # 内部调用 ctest
```

### 3.2 如何确认 make check 跑了什么

```bash
# 解压上游源码包
tar xf zlib-1.3.1.tar.gz && cd zlib-1.3.1

# 先 configure + make 构建一次
./configure && make

# dry run: 只打印命令不执行
make -n check

# 辅助工具: 自动分析
bash ci/tools/extract_upstream_tests.sh zlib-1.3.1.tar.gz
```

### 3.3 如果 make check 有个别用例在 OHOS 上失败

1. **不要删除 make check 调用**
2. 在 conandata.yml 的 patches 中添加补丁修复测试
3. 如果确实无法修复（如平台限制），在 MANIFEST.yml 中声明豁免并说明原因

## 4. 层 2：test_package (必做)

### 4.1 目录结构

```
archives/z/zlib/1.3.1/
├── conanfile.py              # 主配方 (含 build 方法中的 make check)
├── conandata.yml             # 源码 URL + patches
└── test_package/
    ├── conanfile.py          # 测试入口 (test 方法)
    ├── test.c                # 测试源码
    └── MANIFEST.yml          # 上游测试声明 (CI 强制要求)
```

### 4.2 test_package/conanfile.py 要求

- 必须有 `def test(self)` 方法
- `test()` 中必须有 `self.run()` 调用
- `self.run()` 不能只是 `echo`/`print`/`true`（CI 会检测假测试）
- 测试程序必须真正链接并调用库的功能

### 4.3 test_package/MANIFEST.yml 要求

每个包的 test_package/ 下**必须**有 MANIFEST.yml，声明上游测试来源。

模板见 `ci/tools/extract_upstream_tests.sh` 的输出，或参考已有示范：
- `archives/z/zlib/1.3.1/test_package/MANIFEST.yml`
- `archives/b/bash/5.3/test_package/MANIFEST.yml`

## 5. CI 门禁详情 (build_and_test.sh)

### 5.1 L0 门禁 (conan create 之前)

| 检查项 | 说明 | 失败码 |
|--------|------|--------|
| L0a | test_package/ 目录存在 | `no_test_package_dir` |
| L0b | test_package/conanfile.py 存在 | `no_test_conanfile` |
| L0c | test_package/ 下有 .c/.cpp/.sh/.py 源文件 | `no_test_sources` |
| L0d | test() 方法存在且有 self.run() | `no_test_method` / `stub_test_method` |
| L0e | test_package/MANIFEST.yml 存在 | `no_manifest` |
| L0f | conanfile.py 中检测 Go/Rust 源文件，阻止非 C/C++ 项目 | `non_cpp_project` |
| L0g | conanfile.py 语法检查 + conandata.yml sha256 校验 | `invalid_conanfile` / `missing_sha256` |
| L0h | 扫描 self.run() 中的 ${CC}/${CFLAGS}/${CXX}/${LDFLAGS}，命中拦截 (R33) | `env_var_dependency` |
| L0i | patch 格式检查（命名规范 `{seq}-{desc}.patch`、patch_file 路径有效） | `invalid_patch_format` |
| L0j | conan download 检查制品仓是否已存在同版本，已存在且配方有修改则拦截 (R37) | `version_conflict` |
| L0k | 工具类型包（产物含 bin/）必须有 commands.json，库类型不应有 (R38) | `missing_commands_json` |

L0 任一检查失败 → **构建直接终止**，不进入编译阶段。

### 5.2 L1 验证 (conan create 之后)

| 检查项 | 说明 |
|--------|------|
| L1a | conan create 日志中有 "Testing package" 痕迹 |
| L1b | 日志中有编译/运行测试程序的证据 |
| L1c | 如果 MANIFEST 声明了 make check，检查日志中有执行痕迹 |
| L1d | test() 不是假运行 (echo/print/true only) |
| L1e | 破坏性反向验证：mv 产物目录重新 conan test，验证 test 真实依赖被测包 (R34) |

### 5.3 L2/L4/L5 门禁 (conan-verify 阶段)

| 检查项 | 说明 | 失败码 |
|--------|------|--------|
| L2 | smoke test：构建产物中有可执行文件时，执行 `--version` 验证可运行 | `smoke_test_fail` |
| L4 | 安全扫描：readelf 检查 NX / PIE / RELRO 安全属性 | `security_scan_fail` |
| L5 | 产物基线：SHA256 产物基线对比，确保产物一致性 | `baseline_mismatch` |

L2/L4/L5 在 conan-verify 阶段执行，与 G0-G4 门禁配合。L2/L4/L5 失败 → conan-verify 失败 → 不可标记 published。

### 5.4 测试结果说明

| 结果 | 含义 |
|------|------|
| L0_RESULT=pass | 门禁通过 |
| L0_RESULT=fail | 门禁失败，构建被拦截 |
| L1_RESULT=pass | 测试已执行 |
| L1_RESULT=fail | 测试未执行或假测试 |

## 6. 偷懒检测清单

| 偷懒方式 | 被哪层捕获 |
|---------|-----------|
| 不写 test_package | L0a |
| 写空壳 test() | L0d |
| test() 假运行 (echo ok) | L0d + L1d |
| 假测试源码 (int main) | 代码审查 + L1b |
| 不写 MANIFEST.yml | L0e |
| 不跑 make check | L1c (日志无痕迹) |
| 提交 Go/Rust 项目（非 C/C++） | L0f |
| conanfile.py 语法错误/缺 sha256 | L0g |
| self.run() 中裸用 ${CC}/${CFLAGS} | L0h (R33) |
| patch 命名不规范/路径无效 | L0i |
| 同版本号重复上传不同配方 | L0j (R37) |
| 工具包缺少 commands.json | L0k (R38) |
| test 不调用被测包 API（假测试） | L1e (破坏性反向验证) |

## 7. 新增库的标准流程

```
1. 下载上游源码包，放到 archives/对应字母/包名/版本号/
2. 写 conanfile.py (含 build 方法中的 make check)
3. 运行 extract_upstream_tests.sh 分析上游测试
4. 写 test_package/conanfile.py (消费者视角测试)
5. 写 test_package/MANIFEST.yml (上游测试声明)
6. 本地验证: conan create . --profile=ohos
7. 提交 PR → CI 自动检查 L0-L5
```

## 8. 参考示范

| 库 | 构建系统 | make check 方式 | 参考 |
|----|---------|----------------|------|
| zlib | Makefile | `self.run("make check")` | archives/z/zlib/1.3.1/ |
| bash | Autotools | `autotools.make(target="check")` | archives/b/bash/5.3/ |
