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

L0 任一检查失败 → **构建直接终止**，不进入编译阶段。

### 5.2 L1 验证 (conan create 之后)

| 检查项 | 说明 |
|--------|------|
| L1a | conan create 日志中有 "Testing package" 痕迹 |
| L1b | 日志中有编译/运行测试程序的证据 |
| L1c | 如果 MANIFEST 声明了 make check，检查日志中有执行痕迹 |
| L1d | test() 不是假运行 (echo/print/true only) |

### 5.3 测试结果说明

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
