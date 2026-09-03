# PR 描述草稿（按 pr_template.txt 生成，待粘贴至 atomgit PR #7031）

> 说明：本文件为本地交接草稿。最终"上游测试用例通过率"需待 CI（ohpcd-robot `## CI 校验通过`）
> 跑通后回填。CI 在本机无法触发（atomgit 无可用 API），需人工在 PR #7031 评论区回复 `/rebuild`。

## PR 信息
- **三方库名称**：util-linux-login
- **上游版本**：v2.42.2
- **上游仓库地址**：https://github.com/util-linux/util-linux
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无（通用 Autotools + PAM 适配经验）

---

## 测试用例对比
### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | util-linux 上游未为 login/nologin 提供独立单元测试框架 |
| 集成测试 | 0 | 上游 test_shell 套件覆盖整体命令，但不针对 login/nologin 单程序 |
| 其他测试 | N/A | 上游以 `tests/` 命令级回归为主，非按程序拆分 |
| **合计** | **0** | 上游无 login/nologin 专属测试用例 |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无，未新增 |
| 集成测试 | 0 | 不变 | 上游无，未新增 |
| 鸿蒙特有测试 | 2 | 新增 | test_package 编译 login + nologin 并校验 `--help` 输出语义 |
| **合计** | **2** | **+2** | 以 test_package 功能验证替代上游缺失的单程序测试 |

---

## 上游测试用例修改说
### 是否存在对上游测试用例的修改？
- [x] **否**，未修改上游任何测试用例（本适配仅构建 login/nologin，未触达上游测试代码）

---

## 补全测试用例说明
### 上游是否存在无测试用例，适配后补全的情况？
- [x] **是**，上游无 login/nologin 单程序测试用例，适配后补全了测试
> - **补全的测试范围**：为 login、nologin 两个程序新增编译 + 功能验证（共 2 项）
> - **补全原因**：上游 test_shell 套件不覆盖 login/nologin 单程序，且本适配通过 `--disable-all-programs` 仅构建二者，需独立验证其可被正常编译并输出预期 help
> - **新增测试文件清单**：
>   1. `archives/u/util-linux-login/2.42.2/test_package/conanfile.py` — 编译 test.c（引用 PAM/login 符号）并运行 `login --help` / `nologin` 校验语义
>   2. `archives/u/util-linux-login/2.42.2/test_package/test.c` — 最小编译验证源

---

## 验证结果
- 编译状态：待 CI 端到端确认（本机无 ohos-aarch64 profile / OHOS SDK，已做静态校验：conanfile 语法通过、源码 SHA256 与官方 kernel.org 一致）
- 上游测试用例通过率：0/0（上游无 login/nologin 单程序测试）
- 新增测试用例通过率：待 CI 回填（test_package 2 项，目标 2/2 通过）

---

## 补充说明
- **依赖**：硬依赖 `linux-pam/1.7.2`（提供 PAM 头与库）。该依赖需发布至 ohpcd remote（其 issue #1765 未合并）后 CI 方可解析；未发布时 CI 将报"依赖缺失"，届时不混入本 PR，先拆 linux-pam 单独适配。
- **构建范围**：通过 `--disable-all-programs --enable-login --enable-nologin` 仅构建 login 与 nologin，不打包任何库。
- **OHOS 适配**：config.sub 已原生含 `ohos*`；config.guess 需补丁检测 HarmonyOS；PAM 头/库路径注入；utmpx GNU 检查在 OHOS 下跳过。
- **运行时**：login 需 `/etc/pam.d/login` 配置与真实终端，可能需 SUID（真机首次启动避坑见共性问题指南）。
- **issue 编号**：本库 issue 待补（会话/项目中无明确编号），依赖库 linux-pam 的 issue 为 #1765。
- **CI 闭环**：本机无法访问 atomgit API，CI 修复循环需人工在 PR #7031 评论区 `/rebuild` 触发并读数。

---

## 上游通过率（最终，CI 跑通后由人工回填）
- 待 CI（ohpcd-robot `## CI 校验通过`）运行后填写：例 `Pass rate: 100% (1/1)` 或具体数值。
- 本机静态前置验证结论：conanfile 语法 ✅、源码 SHA256 ✅、目录原子性 ✅；真实交叉编译与 L0/L1 门禁待 CI。
