# keyrings.alt 5.0.2 适配笔记

## 基本信息

- **名称**: keyrings.alt（Alternate keyring implementations，Python `keyring`
  包的备用后端集）
- **版本**: 5.0.2
- **许可证**: MIT
- **上游**: https://github.com/jaraco/keyrings.alt（tag `v5.0.2` 实证存在：
  `git ls-remote --tags` 返回 `c94ca9da1e4f30d90a1cdce8ac5dfc6c97f9cd37 refs/tags/v5.0.2`）
- **类型**: 纯 Python 包（无 C 扩展，无需编译）
- **平台任务**: #12819（taskBranch=`feat/keyrings.alt-5.0.2` 原值核对一致）

## 依赖关系（供给核清后再动手——W0）

- **上游运行时依赖**（pyproject.toml dependencies 实证）:
  - `jaraco.classes` → 制品仓无配方（`conan list jaraco.classes/* -r=ohpcd`
    空结果）→ **不声明**（R36/L0i：声明未发布依赖硬失败）
  - `jaraco.context` → 同上，不声明
- **keyring 本体**：上游 pyproject 中 keyring 属 **test extras**
  （`[project.optional-dependencies].test: "keyring >= 20"`），但后端模块
  源码运行时 import keyring（`from keyring.backend import KeyringBackend`
  等）。仓内 `archives/k/keyring/25.6.0` 仅有手工 wheel 解压记录
  （manifest.yaml + notes.md，`status: published` 但 **无 conanfile.py/
  conandata.yml/test_package**），制品仓 `conan list keyring/*` 为空 →
  **无法声明为 Conan 依赖**
- **jaraco.classes/context/keyring 不声明的影响**：`keyrings/alt/__init__.py`
  为空（`import keyrings.alt` 零依赖）；keyring/jaraco 仅在后端模块体
  加载时 import（非包导入时）。消费者实际使用后端时需自行供给 keyring
  （宿主环境 pip 供给或后续任务适配 keyring conan 配方后补依赖声明）。
  aetos/2.0.0 先例：依赖链缺口如实记录在 README/notes/MANIFEST，消费者
  测试诚实降级而不是伪造 import
- **pycryptodome/pycryptodomex**（Encrypted 后端的加密实现，test extras
  声明）：仓内无适配（非 conan 依赖）；PyPI wheel 的 native .so 在本机
  用户目录可正常 dlopen（2026-09-24 实测修正：第一轮记录的"未签名
  ELF Permission denied（E212）"系当时安装位置所致，非平台硬限制，
  详见"上游测试"节实测环境要点）——测试侧 pip 供给后 Encrypted 后端
  67 用例全过
- **上游测试框架依赖**（test extras：pytest/keyring>=20/
  pycryptodome/pycryptodomex 等）：本地实跑时已用 pip 供给
  （keyring 25.7.0 + jaraco.classes 3.4.0 + jaraco.context 6.1.2 +
  pycryptodome 3.23.0 + pycryptodomex 3.23.0）

## 构建方式

纯 Python 包 conan 打包范式（gitpython/3.1.57 #11142 先例，gitdb/4.0.12
与 smmap/5.0.3 同款）：

```bash
python3 -m pip install --no-deps --target="{install_target}" "{source_folder}"
```

- `--no-deps`: jaraco.* / keyring 均未在制品仓发布（见上），不由 pip
  拉取（sdist 构建走 PEP 517 setuptools 后端，仅打包无依赖解析）
- `--target`: 安装到构建目录 install 子目录
- 使用 `sys.executable` 确保调用正确的 Python 解释器

sdist 构建注意：keyrings.alt 用 setuptools_scm 动态版本，sdist 的
PKG-INFO 已固化 `Version: 5.0.2`，`pip install` 离线可用（无需访问
git 元数据）。

## 包信息暴露

通过 `runenv_info.prepend_path("PYTHONPATH", package_folder)` 将包路径
注入运行时环境。下游消费者经 conanrun 环境自动获得 keyrings.alt 的
PYTHONPATH。

## 本地验证（local_verify）

```bash
conan create archives/k/keyrings.alt/5.0.2 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

test_package 冒烟内容（import 冒烟 + 后端类可寻址断言 + 真实功能往返）：

1. 包结构：keyrings/ + keyrings/alt/ + dist-info 在 conan 包目录内
2. `import keyrings.alt` 成功（零依赖入口）
3. 版本核对（importlib.metadata 口径，包无 `__version__` 属性）
4. 八个后端模块（file/file_base/escape/multi/Gnome/Google/Windows/keyczar）
   经 `importlib.util.find_spec` 可寻址（寻址≠加载——后端模块体 import
   未发布的 keyring/jaraco，不触发执行）
5. escape/unescape 纯 stdlib 真实往返（中文/空格/特殊字符样本）
6. 桩替 keyring/jaraco 最小面后：PlaintextKeyring 真实落盘读写删往返 +
   configparser 格式校验 + MultipartKeyringWrapper 分片写入往返 +
   keyczar Crypter 桩替冒烟（上游 tests/mocks.py 同款手法）
7. `keyring.backends` entry-points 元数据（file/Gnome/Google/keyczar/
   multi/Windows (alt) 六项）可发现

## 上游测试（rule 4，本地联网实跑）

### 依赖供给（Septest #11524 意见"缺依赖补依赖"修复，2026-09-24 补跑）

R36 决策树走查（keyring 本体供给）：
- 平台任务池 `GET /api/contrib/tasks?q=keyring` 翻页全量查——无 keyring
  本体任务（仅 keyrings.alt 自身/7811 keyringer/debian-*-keyring 不同物）
- main 归档 `archives/k/keyring/25.6.0` 仅历史手工 wheel 记录（无
  conanfile.py/conandata.yml/test_package），`conan list keyring/* -r=ohpcd`
  0 配方——**无制品可声明**（gitpython→gitdb 的 conan requires 建模前提
  是依赖已发布，keyring 不满足）
- → **测试侧 pip 供给**（R36 决策树 b 分支）：测试环境从 PyPI 镜像拉
  keyring + jaraco + pycryptodome/pycryptodomex wheel 真跑上游测试
  （keyring 25.7.0 / jaraco.classes 3.4.0 / jaraco.context 6.1.2 /
  jaraco.functools 4.6.0 / pycryptodome 3.23.0 / pycryptodomex 3.23.0）

### 实测结果（2026-09-24 二轮，keyring + crypto 供给补齐后）

- **上游 tag**: https://github.com/jaraco/keyrings.alt tag `v5.0.2`
- **测试规模**: `pytest --collect-only` 实测 **183 个用例**
  （tests/ 目录 8 个文件 × 类参数化展开：
  test_file 68（TestEncryptedFileKeyring 46 + TestUncryptedFileKeyring 22）+
  test_crypto 21 + test_Windows 36（TestWin32CryptoKeyring 21 +
  TestRegistryKeyring 15）+ test_Google 32（Interaction 17 + TestCase 15）+
  test_Gnome 17 + test_keyczar 5 + test_multi 4）
- **实跑环境**: 本机 OpenHarmony PC（arm64-ohos, Python 3.12.9,
  pytest 9.1.1；测试依赖 pip 供给 keyring 25.7.0 / jaraco.classes 3.4.0 /
  jaraco.context 6.1.2 / pycryptodome 3.23.0 / pycryptodomex 3.23.0）
- **实跑结果**: **98 passed + 85 skipped + 0 failed**（1.8s 跑完）
  - 98 passed = test_file 68 全过（TestUncryptedFileKeyring 22 +
    TestEncryptedFileKeyring 46——Crypto/Cryptodome 双参数化在
    pycryptodome+pycryptodomex 供给后全过）+ test_crypto 21 全过 +
    test_keyczar 5 + test_multi 4
  - 85 skipped 全部为上游环境条件跳过（skipif/requires 环境探测，
    非 OHOS 平台缺陷，上游在无桌面 Linux CI 同样跳过）：
    - `Need Google Docs (gdata)` × 32（上游 pyproject 注释明确
      "gdata doesn't currently install on Python 3"——Python 2.7 专属）
    - `Need Windows` × 21（TestWin32CryptoKeyring 需 win32 平台）
    - `Need GnomeKeyring` × 17（Linux 桌面 gnome-keyring 守护进程）
    - `RegistryKeyring not viable` × 15（Windows 注册表）
- **通过率**: 98/183（53.6%，超 50% 红线；此前未供给 crypto 依赖时为
  31/183=16.9%）

### 实测环境要点（复现命令）

```bash
# 测试依赖供给（隔离目录，不污染系统 site-packages）
python3 -m pip install --target=$HOME/tmp/kalt-verify/pylibs \
    pycryptodome pycryptodomex
# keyring/jaraco 系已在解释器 pip-global（/data/storage/el2/base/files/
# interpreters/pip-global）
cd <keyrings_alt-5.0.2 sdist 解压目录>
PYTHONPATH=/data/storage/el2/base/files/interpreters/pip-global:$HOME/tmp/kalt-verify/pylibs \
TMPDIR=/data/storage/el2/base/cache \
python3 -m pytest -p no:cacheprovider -o addopts=''
# → 98 passed, 85 skipped, 8 warnings in 1.79s
```

两个环境要点（第一轮 31 passed → 本轮 98 passed 的差异根因）：
1. **pycryptodome/pycryptodomex native .so 实际可加载**——此前 notes
   记录"未 OHOS 签名 ELF dlopen Permission denied（E212）"经本轮实证
   **修正**：pip 安装到用户目录（HMDFS）后 `Cryptodome.Util._cpuid_c.abi3.so`
   dlopen 正常（ctypes.CDLL 实测 OK），Encrypted 后端 67 用例全过。
   第一轮失败系当时安装位置（受限路径）+ 收集期 error 误判，非平台
   硬限制
2. **TMPDIR 必须指到 tmpfs**（/data/storage/el2/base/cache）——HMDFS
   用户路径 chmod 不生效（E046 类：os.chmod 0o600 后 stat 仍 0o660，
   group_other=0o060 恒非零），上游
   `test_keyring_not_created_world_writable` 断言 `st_mode & 0o077 == 0`
   在 HMDFS 恒失败；tmpfs 上 chmod 语义正常，用例通过

### 上游测试不修改说明

上游套件零修改实跑（无补丁、无测试文件改动）——85 个 skipped 均为
上游自身 skipif 环境探测（Windows/GnomeKeyring/gdata），不构成"减少
测试"，如实按原样申报。

## 已知限制

- keyring 本体与 jaraco.classes/jaraco.context 未在制品仓发布，本配方
  无法声明这些依赖（R36）。消费者使用后端时需宿主环境供给（或等
  keyring conan 配方适配发布后补 `requires`）；上游测试已通过测试侧
  pip 供给真跑（见"上游测试"节，98/183 通过）
- pycryptodome/pycryptodomex native .so 在本机用户目录可正常加载
  （2026-09-24 实测修正，见"实测环境要点"）；Encrypted 后端在依赖
  供给后 67 用例全过。测试期 crypto 依赖由测试环境 pip 供给，非制品
  仓 conan 依赖（pycryptodome/pycryptodomex 仓内亦无配方）
- Gnome/Google/Windows 后端分别为 Linux 桌面/已停更 gdata（Python 3
  不可装）/Windows 专属，OHOS 环境天然不适用（上游 skipif 同样跳过，
  共 85 用例）
