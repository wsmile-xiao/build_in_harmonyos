# pyelftools 0.33 适配笔记

## 编译环境
- 构建系统: none（纯 Python noarch，setuptools 打包 manifest，无 C 扩展，无需交叉编译）
- 编译日期: 2026-10-04
- 编译器: N/A（纯 Python）；本机工具链 clang 15.0.4 / make 4.4.1 就绪
- 解释器: Python 3.12.9（PATH python3；`/data/service/hnp/bin/python3` 本机不可访问，配方内以 PATH 为准并留 isfile 探测兜底）
- 状态: built

## 源码与版本核验
- 源码地址（官方源，R39）: https://files.pythonhosted.org/packages/a3/11/767522582afab1b884d277de0e6e011640cb9d7292a38694b4b1a1df1ae8/pyelftools-0.33.tar.gz
- SHA256: 660d82dcbeb8e83d1702bd97f223f761625da06111c0cc988eac6b8ab0c1b61f（实测一致）
- 版本核验: `elftools/__init__.py` → `__version__ = '0.33'` ✓
- 上游仓库 tag: `v0.33`（GitHub tag 名带 v 前缀；GitHub codeload tarball SHA256=5507d69b…6869d 仅交叉参考，配方以 PyPI sdist 为准，同 packaging/aiohttp/six/certifi 先例）

## W0 依赖核验（适配前）
- `pyproject.toml` `[project]` 无 `dependencies` 声明（PyPI JSON `requires_dist: null`）→ **运行时零第三方依赖**
- build-system `setuptools>=46.4.0` 为构建后端（本机已具备，非 conan requires）
- `typing` 依赖组（mypy/pyright/typeguard/typing_extensions）为开发可选组（PEP 735 dependency-groups），非运行时依赖
- 源码内 `typing_extensions` 9 处 import 全部位于 `if TYPE_CHECKING:` 块（配合 `from __future__ import annotations`），运行时永不执行
- **结论: 无未核验/未发布第三方依赖，继续适配**（conan requires 为空）

## 编译步骤
1. `ohc-run.py init-build pyelftools 0.33 --url=<PyPI sdist>` → 下载/解压/骨架/环境（见"首个真实错误"）
2. `ohc-run.py lang-preflight pyelftools 0.33 --src ... --lang python` → detected=python，exit 0（R47 通过）
3. 无编译步骤：纯 Python 包，`conan create` 内 `package()` 直接拷贝 `elftools/` 到 site-packages
4. 上游测试（unittest）见"上游测试"节

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 后 `.work` 源码树被销毁：仅剩 `Makefile/elf_creator.c/llvm-dwarfdump/readelf`（test/external_tools 内容），`elftools/` 包消失 | 框架 init_build.py F068 嵌套源码启发式 `_BUILD_MARKERS=(configure,CMakeLists.txt,Makefile,meson.build)` 不含 Python 打包 manifest（pyproject.toml/setup.py/setup.cfg）；PyPI sdist 顶层无 Makefile（dev-only 未入 sdist），启发式递归 3 层锁到 `test/external_tools/Makefile`，将其中内容提升为"源码根"并删除其余全部目录 | 最小修改（不改框架，协作者 scripts/ 只读）: 手动从 PyPI sdist 重新解压重建 `.orig`/`.work`（`tar -xzf --strip-components=1` + `cp -a`），并核验 `elftools/__init__.py` 版本与 test/ 完整性。已复验通过。SKILL 缺陷反馈见 feedback/（F068 对纯 Python sdist 误判） |

## 首个真实错误（Step 4 记录）

**命令**: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build pyelftools 0.33 --url=...`（exit 0，但产物被污染）
**原始输出**（日志: $HOME/tmp/pyelf/01-init-build.log）:
```
ℹ️   下载: https://files.pythonhosted.org/packages/a3/11/.../pyelftools-0.33.tar.gz
ℹ️   嵌套源码检测: 找到源码在 test/external_tools，正在提升到 pyelftools-0.33.orig ...
✅   嵌套源码提升完成: test/external_tools → pyelftools-0.33.orig
✅   .orig 已解压: /storage/Users/currentUser/tmp/builds/pyelftools-0.33.orig
✅   .work 已创建 (复制): /storage/Users/currentUser/tmp/builds/pyelftools-0.33.work
```
**复现核验**: 提升后 `pyelftools-0.33.work/` 顶层 = `Makefile README.txt elf_creator.c llvm-dwarfdump readelf`（5 项，均为 test/external_tools 内容）；`elftools/` 不存在，`grep __version__` 失败（exit 2）。
**根因**: 见问题表 #1（F068 启发式对无顶层构建标记的纯 Python sdist 递归误锁子目录 Makefile）。
**最小修改**: 手动重建 .orig/.work（不改源码、不打补丁、不改框架脚本）；后续 conan 配方 `source()` 自行下载解压（conan create 内不经过 F068），不受此问题影响。

## 上游测试（R51 三步法）

### 第一步：清点（上游 test/ 目录）
| 测试族 | 入口 | 规模 |
|---|---|---|
| 单元测试 | `test/run_all_unittests.py`（unittest discover `test/test*.py`） | 54 个 test_*.py 文件 |
| 示例测试 | `test/run_examples_test.py`（跑 examples/*.py） | 12 个示例 |
| readelf 对比 | `test/run_readelf_tests.py --parallel` | 对比捆绑 `test/external_tools/readelf`（x86-64 ELF） |
| dwarfdump 对比 | `test/run_dwarfdump_tests.py --parallel` | 对比捆绑 `test/external_tools/llvm-dwarfdump`（x86-64 ELF） |
| 夹具 | `test/testfiles_*/` | 99 个 .elf 文件 |
- 上游官方入口: `python test/all_tests.py`（依次跑以上四族；上游 CI 用 `.github/workflows/ci.yml`）

### 第二步：运行（本机 aarch64 OHOS, Python 3.12.9）

| 测试族 | 命令 | 总数 | 通过 | 失败 | 跳过 | 日志 |
|---|---|---|---|---|---|---|
| 单元测试 | `python3 test/run_all_unittests.py`（官方入口；另用 TextTestResult 钩子逐项枚举复核） | 118 | 118 | 0 | 0 | 07-unit-test-ids-final.txt / 03-upstream-unittests(-verbose).log |
| 示例测试 | `python3 test/run_examples_test.py` | 12 | 12 | 0 | 0 | 04-upstream-examples.log（Conclusion: SUCCESS） |
| readelf 对比 | `python3 test/run_readelf_tests.py` | 49（.elf 夹具） | 0 | 阻断 | 0 | 05-upstream-readelf.log |
| dwarfdump 对比 | `python3 test/run_dwarfdump_tests.py` | 9（.elf 夹具） | 0 | 阻断 | 0 | 06-upstream-dwarfdump.log |

**可执行合计: 130 项, 130 通过, 0 失败, 0 跳过, 通过率 100%**（unittest 118 + examples 12）
**平台阻断: 58 项**（readelf 49 + dwarfdump 9）——具体技术原因: 上游捆绑的对比工具 `test/external_tools/{readelf,llvm-dwarfdump}` 为 **x86-64 预构建 ELF 二进制**（`file` 核验: ELF shared object 64-bit LSB x86-64, dynamic /lib64/ld-linux-x86-64.so.2），aarch64 OHOS 无法执行（`OSError: [Errno 8] Exec format error`）。这是上游测试设计对 CPU 架构的硬依赖，非本包代码缺陷；本机 binutils readelf 2.45 / llvm-dwarfdump 存在，但与上游捆绑版本输出格式不一致，替换对比基线超出"不改上游测试"口径，故如实记录为平台阻断。

单元测试 118 项逐项名称清单: `$HOME/tmp/pyelf/07-unit-test-ids-final.txt`（全部 `ok`，格式 `<status>\t<module.Class.test_method>`，如 `ok\ttest_arm_call_reloc.TestARMRElocation.test_reloc`、`ok\ttest_hash.TestGNUHash.test_gnu_hash` 等，完整 118 行）。

> 注: 曾以"逐 test 对象单独 run()"方式枚举出现 5 项 `test_core_notes*` ERROR——系隔离执行未触发 `setUpClass`（`_core_file` 类属性未建立）的**测量假阳性**；官方入口与官方 runner（discover+TextTestRunner）均为 118/118 OK，以官方 runner 为准。

### 第三步：PR 回填
- 上游测试: 130/130 通过（100%，unittest 118 + examples 12）
- 平台阻断: 58 项对比测试（捆绑 x86-64 工具无法在 aarch64 OHOS 执行，Exec format error，非代码缺陷）
- 上游测试用例零修改、零排除、零占位符

## 依赖版本
- 无运行时第三方依赖（见 W0 核验）
- 测试运行器: unittest（标准库）；pytest 未用（上游用 unittest discover）

## 验证结果

```bash
# conan create (真实, 同 CI 命令: ci/conan/build_and_test.sh L1354)
conan create archives/p/pyelftools/0.33 \
  -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="pyelftools/*"
# → EXIT=0; 源码下载✓ 上游 unittest 118/118 OK✓ 包创建✓ test_package 冒烟✓
#   pyelftools/0.33: Package 'da39a3ee5e6b4b0d3255bfef95601890afd80709' created
#   (sha256 660d82dc…61f 校验通过; L1 OK: pyelftools ELFFile parses minimal ELF64 aarch64 header)

# conan-verify (8 门禁)
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify pyelftools 0.33
# → G1/G2/G3/G4 PASS, L2 PASS, L4 PASS, L5 PASS, exit=0
```

| 门禁 | 结果 | 说明 |
|------|------|------|
| G1 配方完整性 | ✅ | conanfile+conandata+test_package+MANIFEST 齐备 |
| G2 conan create | ✅ | 干净源码构建 exit=0，上游 118/118，冒烟真实 ELF 解析通过 |
| G3 系统同名库隔离 | ✅ | 纯 Python 无 .so/.a |
| G4 产物完整性 | ✅ | elftools/ 包 17 子模块 |
| L2 smoke test | ✅ | 冒烟 exit=0，真实 API 输出 |
| L4 安全扫描 | ✅ | 纯 Python 无 ELF |
| L5 产物基线 | ✅ | 无存量基线（首版） |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conanfile.py | - | Conan 配方（纯 Python noarch，同 packaging 先例） |
| conandata.yml | - | PyPI sdist URL + SHA256 |
| test_package/ | - | conan L1 测试 |
| elftools/（包内） | 69M 源码→~4M 包 | site-packages 拷贝 |

## 注意事项
- 纯 Python 库：不产 commands.json（R38 仅 tool 类型；本包产物为库，`scripts/readelf.py` 属包内脚本不单独安装为系统 CLI——与 packaging 先例口径一致，包内 import 可用）
- readelf/dwarfdump 对比测试依赖捆绑 x86-64 二进制，aarch64 OHOS 不可执行（平台限制，如实记录跳过原因）
- conan 配方 `package()` 拷贝 `elftools/`（含 py.typed）到 `lib/pythonX.Y/site-packages/`（随构建机 Python 版本），`runenv_info.PYTHONPATH` 注入（Conan 2 API；同 packaging/26.3 先例的语义，`env_info` 为 1.x 兼容 shim）
---

**编译结束**: 2026-10-04 11:02
**最终状态**: built
