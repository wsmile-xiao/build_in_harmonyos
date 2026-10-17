# pdd 1.7 — OHOS/HarmonyOS PC 适配笔记

## 目标库

- **pdd**（jarun/pdd）："Tiny date, time diff calculator with timers"，纯 Python CLI（GPLv3）。
- 上游：https://github.com/jarun/pdd（v1.7，2022-12-03）
- 源：PyPI sdist `pdd-1.7.tar.gz`（files.pythonhosted.org 官方 CDN，同 python-dateutil 先例）
  - HTTP 200 / 22158 B / 真 gzip
  - sha256 `c532faf070fc98c5d1e81df953450f54dc8d96b243fbe06a29c5c979182113a5`（与 PyPI 记录逐字一致）
- 版本自证：`pdd.py:42 _VERSION_ = '1.7'`；配方 build() 内再校验一次，不一致即 ConanException。

## 依赖

| 依赖 | 版本 | 类型 | ohpcd 可消费性 |
|---|---|---|---|
| python-dateutil | 2.9.0.post0 | 运行时强制（install_requires，裸名无下限） | ✅ download EXIT=0 |
| six | 1.17.0 | 传递（python-dateutil 配方 requires） | ✅ download EXIT=0 |
| pytest / twine / setuptools | — | tests extra / packaging extra / 构建期 | Found 0，不进运行图 |

依赖分析报告：仓根 `pdd_1.7_deps.md`（含交错正对照 `dep-probe17.log`）。

## 打包形态

- `package_type = "application"`（照 `archives/c/cookiecutter/2.7.1`、`archives/a/autotiling/1.9.3`）
- 上游 setup.py `entry_points={'console_scripts': ['pdd=pdd:main']}`、`py_modules=['pdd']`：
  - `lib/python3.12/site-packages/pdd.py` ← 复制源码模块
  - `bin/pdd` ← 手写 launcher（自定位 site-packages，`exec "${PYTHON:-python3}" -c ...`），
    复刻 console_scripts 语义；sdist 内没有 `pdd` 可执行文件，必须自生成。
- 依赖传播：python-dateutil 配方（`package_type="python-require"`）未导出 runenv，
  其 site-packages 不会自动进 PYTHONPATH。本配方 `package_info()` 遍历依赖包目录，
  把依赖 site-packages **prepend** 进 runenv/buildenv 的 PYTHONPATH——不复制依赖源码进本包，
  与「禁止混入依赖库源码」一致。test_package 侧另有独立收集（catkin-pkg/1.1.0 先例），
  双保险。

## OHOS 适配要点

- 纯 Python、无 C 扩展（wheel `py3-none-any`）：不触及 musl/libc、编译器、交叉工具链差异。
- `ctypes` 仅在 `if os.name == 'nt':` 分支（Windows 光标隐藏），OHOS 不触发。
- 输出期望与 TZ/locale 无关（月名硬编码、纯日历算术）。
- 无 `--version` 参数（上游 usage 证实 `unrecognized arguments: --version`）⇒
  legacy driver 的 `.staging-verified`（对 staging prefix 逐 exe 跑 `--version`）本就不适用
  （v3.0 conan 流程也不产出该标记，非阻塞）。

## 上游测试（真实执行）

- 入口：`python3 -m pytest test.py -v`（上游 test.py 自述的测试入口）
- 环境：OHOS aarch64（HarmonyOS，HongMeng Kernel 1.12.0）、Python 3.12.9、pytest 9.1.1
  （pytest 非 conan 依赖，为跑测试临时 pip 装入 `.workbuddy/tmp/pdd-1.7/pylibs`，不入库、不进包）
- 结果：**15 passed / 0 failed / 0 skipped / 0 xfailed**（`platform ohos`），EXIT=0
- 日志：`.workbuddy/tmp/pdd-1.7/upstream-tests.log`
- 说明：sdist 只有 `pdd.py`，测试以 `./pdd` 调用 → 执行前 `cp pdd.py pdd && chmod 755 pdd`
  （等价 `make install` 后的可执行形态，不修改上游代码）。

## test_package（含新增鸿蒙用例）

- `test_pdd.py`（纯 stdlib，不依赖 pytest——ohpcd Found 0）：
  - 上游等价 6 用例（期望值逐字取自上游 res 表）
  - **鸿蒙可行性 3 用例（本仓库要求的新增消费者用例）**：
    1. `test_ohos_platform`——断言运行平台为 OHOS/HarmonyOS
    2. `test_ohos_consumer_entrypoint`——PYTHONPATH 仅含依赖 site，直调打包出的
       `bin/pdd` launcher，验证自定位逻辑在 OHOS musl python 下可用
    3. `test_ohos_dateutil_from_conan`——dateutil 必须从 conan 交付的 site-packages
       import 成功（OHOS 无系统 pip，证明依赖链真实可达）

## 环境坑位记录（本包相关）

- 无编译步骤 → 无 SELinux 域/cmake symlink 类问题。
- 共享 worktree：提交须显式白名单 add（见提交记录），禁 `git add -A/.`。
- `/tmp` 只读；临时产物一律落 `.workbuddy/tmp/pdd-1.7/`。
---

**编译结束**: 2026-09-18 14:28
**最终状态**: built
