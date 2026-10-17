# DRAFT — 本机 conan 验证残留生成物污染 test_package/，打包传设备前必须清理

> Status: **Draft**（待审核 promote）｜ severity: `2` | category: `conan|packaging|workflow|device-transfer` | Updated: 2026-10-01
> 对应: `knowledge/drafts/DRAFT-tayga-0.9.2-generators-pollute-test-package.kv`

## 错误签名

```text
archives/t/tayga/0.9.2/test_package/conanbuild.sh
archives/t/tayga/0.9.2/test_package/conanrunenv-release-x86_64.sh
archives/t/tayga/0.9.2/test_package/deactivate_conanrun.sh
archives/t/tayga/0.9.2/test_package/metadata/
```

传输后设备端 `find archives/t/tayga -type f` 列出上述文件——本机验证残留跟着 tar 上了真机。

## 根因

in-source 配方（kelbt/tayga 式）设置 `self.folders.generators = "."`。conan create 的 test 阶段把 VirtualRunEnv/VirtualBuildEnv 产物（`conanrun.sh`、`conanrunenv-release-x86_64.sh`、`deactivate_*.sh`、`conanbuild.sh`、`metadata/`）直接写进 `test_package/`。这些文件：
- 不在 git 索引里，`git status` 有时看不到（被全局 ignore 吞掉）→ "worktree 干净"是错觉；
- `tar -czf archives/<l>/<lib>` 打包时全部带上 → 设备端包目录混入 **x86_64 命名空间**的生成物；
- 每次"本机验证 → 打包"循环都会**重新生成**，清一次不够。

## 推荐方案（两道防线 + 可选根治）

**① 打包前清**（tar 命令前执行）：

```powershell
Get-ChildItem <pkg>/test_package -File | Where-Object Name -match '^(conanbuild|conanrun|conanbuildenv|conanrunenv|deactivate_)' | Remove-Item -Force
Remove-Item <pkg>/test_package/metadata, <pkg>/test_package/__pycache__ -Recurse -Force -ErrorAction SilentlyContinue
```

**② 验证后清**：Docker 回归命令末尾挂同款清理，保证 worktree 无残留。

**根治（可选）**：本机验证不挂载 worktree 本体——把包目录 copy 到临时目录再 `conan create`，生成物落在副本里随容器销毁。

**设备端复查**：解压后 `find archives/<l>/<lib>/<ver>/test_package -type f` 应只剩 `conanfile.py / MANIFEST.yml / 测试源文件`；发现生成物就地删除再开跑（缺文件或垃圾文件都不要启动测试）。

## 来源

tayga/0.9.2 适配 r3 轮（2026-10-01）：Docker 回归后打 tar 传设备，find 验完整性时发现 7 个生成物混入；两端清理后 r3 才正常进 L0。

---
*本文由 `knowledge/drafts/DRAFT-tayga-0.9.2-generators-pollute-test-package.kv` 字段衍生（补齐 kv→md 配套）。*
