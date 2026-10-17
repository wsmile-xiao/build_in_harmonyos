# abuild-rootbld 3.17.0 适配笔记

## 编译环境
- 构建系统: custom（noarch 元包，无 C/C++ 编译）
- 编译日期: 2026-08-10
- 编译器: N/A
- 状态: built

## 软件形态与适配思路

abuild-rootbld 是 Alpine abuild 的 **noarch 元包子包**（`_rootbld()` split 函数，APKBUILD 中仅声明依赖）：
- 运行时依赖：`abuild`（主包，提供 `abuild rootbld` 命令）+ `bubblewrap`（bwrap，chroot 沙箱）+ `cmd:envsubst`（gettext 提供，模板变量替换）
- `rootbld` 命令本体是 `abuild.in` 内的 shell 函数（`rootbld()` / `rootbld_actions()`，约 2482-2687 行），由 abuild 主包安装

因此本配方：
1. `requirements()` 声明 abuild/3.17.0 + bubblewrap/0.11.0 + gettext/0.22.5.1（依赖契约）
2. `package()` 安装 `bin/rootbld` 薄包装脚本（`exec abuild rootbld "$@"`），使入口在 PATH 可用；附带打包 abuild.in 源码摘录（share/abuild-rootbld/abuild.in）供参考
3. 无编译（build_system: custom）

## 依赖就绪情况（W0）

| 依赖 | 版本 | 状态 |
|------|------|------|
| abuild | 3.17.0 | ✅ 已发布 ohpcd 制品仓 |
| bubblewrap | 0.11.0 | ✅ 本地 conan 缓存验证通过（conan create + test_package 全过），尚未发布 ohpcd |
| gettext | 0.22.5.1 | ✅ 本地 conan 缓存验证通过（conan create + test_package 全过），尚未发布 ohpcd |

bubblewrap/gettext 未发布 ohpcd 属预期：本地工作流先完成全部适配，PR 合并后由 CI 统一发布。

## 上游测试情况（如实记录）

- `abuild-rootbld` 无独立上游测试套件：rootbld 是 abuild.in 内的 shell 函数，abuild 自身的 ATF/Kyua 测试（tests/*_test）不涉及 rootbld
- 本配方 test_package 验证依赖契约：rootbld wrapper --version、bwrap --version、envsubst --version、abuild 存在性（5 项断言）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ohc-run.py find_project_dir 解析到 SKILL 目录 | 脚本从 SKILL_ROOT 位置向上找项目根 | 所有命令加 `--project-dir /storage/Users/currentUser/runner/build_in_harmonyos` |
| 2 | conan 下载源慢 | 制品仓/源站网络 | 复用本地 tarball + conan-src-cache 预置（sha256 命名 + .json） |
| 3 | noarch 元包 G4 产物检查 | G4 要求 bin/ 产物 | package() 安装 bin/rootbld 委托包装脚本（非空产物） |

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | noarch 元包配方（requirements 三依赖 + rootbld wrapper） |
| conandata.yml | abuild 3.17.0 tarball 源（sha256 校验） |
| test_package/ | 依赖契约冒烟测试（conanfile.py + test.sh + MANIFEST.yml） |
| manifest.yaml | 版本级（status=built） |
| commands.json | 软件级 tool 声明（commands: rootbld） |

## 注意事项

- rootbld 实际沙箱构建需要 bwrap user namespaces / setuid，OHOS 上受限（与 bubblewrap 相同），不影响本元包编译与依赖契约验证
- 本任务未执行 finish/submit/commit/upload（主编统一处理归档收尾与提交）
