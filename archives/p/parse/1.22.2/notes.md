# parse 1.22.2 适配笔记

## 基本信息

- **名称**: parse
- **版本**: 1.22.2
- **许可证**: MIT
- **上游**: https://github.com/r1chardj0n3s/parse（官方 tag 1.22.2 实证存在；
  PyPI sdist 1.22.2 下载并核验 SHA-256 = 8ff0b98202798b8cefa4f8fac06b670d6d00e5ec6ecbbacaf97ac0d0e93a54e6）
- **类型**: 纯 Python 包（str.format() 的反向解析库——按格式模式解析字符串并做类型转换）

## 依赖关系

- **上游依赖**（PyPI requires_dist 实证）: 无。parse 1.22.2 仅使用 Python 标准库，
  无任何运行时依赖。
- **构建后端**: setuptools>=61.2（pyproject.toml [build-system]，环境已装 84.0.0）。
- **运行时外部程序**: 无（纯库，无子进程调用）。

## CLI 判定（R38/L0k）

parse 无可执行入口：pyproject.toml 无 console_scripts/entry_points/scripts 段，
源码无 shebang 脚本、无可执行位文件，构建产物仅 `parse/__init__.py` + `.pyi`。
判定为非 CLI 库，**不需要 commands.json**（库类型豁免）。

## 构建方式

纯 Python 包 conan 打包范式（gitpython/3.1.57 同款先例）：

```bash
# r02 起 build() 首步显式安装 setuptools（PEP 517 后端保障，terminator/2.1.5 同款）：
python3 -m pip install --break-system-packages --timeout 120 --retries 3 setuptools
# 再安装本包（--no-build-isolation 复用刚安装的后端）：
python3 -m pip install --no-deps --no-build-isolation --target="{install_target}" "{source_folder}"
```

- **首步 `pip install setuptools`（r02 新增）**: 远端 CI 设备 Python 缺
  `setuptools.build_meta`，`--no-build-isolation` 直接导入后端会触发
  PEP 517 `BackendUnavailable`（PR #11627 CI 首错）。显式安装保证后端
  在两环境均可用：本地已装 setuptools 84.0.0 幂等秒过，CI 先装再复用。
  `--break-system-packages` 绕过 PEP 668 externally-managed 守卫；
  `--timeout/--retries` 增强 PyPI 网络韧性；setuptools 以 wheel 安装、
  不创建 pip-build-env overlay（不触碰 inode 上限）。
- `--no-deps`: parse 无运行时依赖，不通过 pip 拉取
- `--no-build-isolation`: **worker 文件系统 inode 上限硬约束**——pip 构建隔离会
  在 `$TMPDIR/pip-build-env-*` 创建 overlay（setuptools+vendored 依赖），
  worker 上直接报 `No space left on device`（inode 耗尽）。环境已有
  setuptools 84.0.0 >= 61.2，复用即可，无需隔离构建环境。
- `--target`: 安装到构建目录 install 子目录，package() 整体拷贝

## 平台适配要点

1. **纯 Python 库无交叉编译**：无 C 扩展，OHOS aarch64 与 Linux 产物一致，
   conan create 走 python-require 打包路径。
2. **PYTHONPATH 运行环境**：package_info() 用 `runenv_info.prepend_path("PYTHONPATH", ...)`
   暴露包目录；test_package 经 VirtualRunEnv 的 conanrun 环境运行。
3. **parse 默认字段类型语义**：`{}` 默认是非贪婪 `.+?`（findall 场景只匹配 1 字符），
   需要词/日期等显式类型时用 `{:w}`（词）、`{:ti}`（ISO 日期转 datetime）、
   `{:d}`（int）等；`with_pattern` 是装饰器用法
   （`@parse.with_pattern(r"\d+")` 修饰函数后作为 extra_types 传入），
   转换器返回 None 时字段值为 None（不是匹配失败）。
4. **上游测试运行**：pytest 需 `-o addopts=""` 覆盖 pyproject 内的 `--cov` 参数
   （环境无 pytest-cov），并设 `-o cache_dir=<可写目录>`（/tmp 只读、worker
   inode 紧张）；TMPDIR/TMP/TEMP 指向可写目录。

## 上游测试

- **总数**（pytest --collect-only 实证）: 98 个独立用例，来自 7 个 test_*.py：
  test_parse.py(51) / test_bugs.py(12) / test_parsetype.py(13) /
  test_pattern.py(11) / test_result.py(4) / test_search.py(4) / test_findall.py(3)。
  check_typing.py 是 mypy 类型检查脚本（文件头声明不跑 pytest），不计入。
- **全量运行**: 97 passed / 1 skipped（99.0%）。唯一 skip 为版本条件
  （`test_parse.py:775` "Python 3.5 removed the limit of 100 named groups"，
  python3.12 下限制已不存在，无需恢复）。无失败、无未实例化。
- 详见 test-report.md 双口径台账。

## 鸿蒙专项测试

新增 `tests/ohos_test_parse.py`（8 项业务断言）：配置行/日志行解析、ISO 日期转换、
多行日志流 findall、with_pattern 自定义类型（semver）、无匹配容错、format 反向对齐。
实际运行全部 PASS。与上游 pytest、test_package 消费者用例分别计数。

## 消费者验证（test_package）

`test_package/test_parse.py`（15 项断言）：import、版本一致、公开 API 表面
（parse/search/findall/compile/with_pattern）、位置/命名解析、int/float 类型转换、
search/findall、compile+with_pattern 自定义类型。conan create 实测全部 PASS。

## 环境/基础设施备注

- **worker inode 上限**（`.staging-verified`/`.build-closed` 基线噪声）:
  W3 junk_check 命中 origin/main 上其他库（cloog/0.21.1、kics/2.1.20）错误提交的
  空运行时状态文件（blob e69de29b…，提交前已存在、非当前库文件）。已按基线隔离
  复验规程处理：记录路径+隔离前 SHA-256 → index 临时隔离 → 复跑 JC（PASS）→
  原样恢复并核对 SHA-256（见最终回报 baseline_isolation_audit）。当前库
  diff/staged/PR 不含这些路径。
- **磁盘/inode 资源**：/tmp 为只读 erofs；`/storage/Users/currentUser` 为 HMDFS，
  inode 全局 100% 水位，任何大目录创建/完整 checkout 都可能 No space。worktree
  采用稀疏 checkout（cone 模式）规避。
---

**编译结束**: 2026-09-21 20:00
**最终状态**: built
