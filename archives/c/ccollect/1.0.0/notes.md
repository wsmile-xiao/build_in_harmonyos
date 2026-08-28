# ccollect 1.0.0 适配笔记

## 编译环境
- 构建系统: makefile（纯 sh 脚本，无 C/C++ 编译）
- 编译日期: 2026-08-26
- 编译器: N/A（纯 sh 脚本，无需编译）
- 状态: built

## 三身份说明

| 维度 | 值 | 说明 |
|------|------|------|
| 平台身份 | ccollect 1.0.0, Issue #2398, feat/ccollect-1.0.0 | 任务平台登记 |
| 上游身份 | ccollect 1.0 (tag `1.0`), ungleich/ccollect, GPL-3.0-or-later | 上游 git tag 为 `1.0`，脚本内 VERSION="1.0" |
| 归档身份 | ccollect/1.0.0, archives/c/ccollect/1.0.0/ | Conan name/version 1.0.0 匹配平台 |

## 编译步骤

ccollect 是纯 sh 脚本备份工具，无需 configure/make 编译：
1. 从官方 Git 仓库下载源码（code.ungleich.ch/ungleich-public/ccollect tag 1.0）
2. 应用 TMPDIR 补丁（OHOS /tmp 只读，mktemp 需使用 TMPDIR 环境变量，回退到 /data/local/tmp）
3. 创建 Conan 配方（conanfile.py + conandata.yml + test_package/）
4. 通过 conan create 验证配方可用性

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | mktemp 失败: /tmp 只读 | OHOS 上 /tmp 挂载为只读文件系统 | 补丁 0001-ccollect-ccollect.patch: 将 `mktemp "/tmp/..."` 改为 `mktemp "${TMPDIR:-/data/local/tmp}/..."`，使 TMPDIR 环境变量生效，回退路径为 /data/local/tmp |
| 2 | rsync 不可用 | 编译环境未安装 rsync；ccollect 是 rsync 包装器，rsync 是运行时外部依赖 | 记录为外部运行时依赖（类似 pidcat 的 adb），不作为 Conan 管理依赖 |
| 3 | 版本差异: 上游 1.0 vs 平台 1.0.0 | 上游 git tag 为 `1.0`（脚本内 VERSION="1.0"），平台登记为 1.0.0 | 三身份在 manifest/notes/PR 正文中分别说明，上游版本映射为规范 semver |

## 源码修改

- 补丁: `patches/0001-ccollect-ccollect.patch`
  - 修改 `ccollect` 第 43 行: `export TMP="$(mktemp "/tmp/${__myname}.XXXXXX")"` → `__tmpdir="${TMPDIR:-/data/local/tmp}"` + `export TMP="$(mktemp "${__tmpdir}/${__myname}.XXXXXX")"`
  - 原因: OHOS 平台 /tmp 为只读文件系统，需使用 TMPDIR 环境变量指向可写临时目录；回退到 /data/local/tmp（OHOS 标准可写临时目录）
  - 语义不变: 当 TMPDIR 已设置时使用 TMPDIR，否则使用 /data/local/tmp

## 运行时依赖

| 依赖 | 类型 | 说明 |
|------|------|------|
| rsync | 系统命令 | 核心备份机制，ccollect 是 rsync 包装器 |
| ssh | 系统命令 | 远程备份支持 |
| hostname | 系统命令 | 用于确定备份源名称 |
| posix sh | 解释器 | ccollect 为 /bin/sh 脚本 |

## 上游测试

| 测试脚本 | 说明 | 可运行性 |
|----------|------|----------|
| test/test-ccollect1.sh | 完整备份测试流（需 rsync + 可写 /tmp） | 需 rsync 环境 |
| test/test-ccollect-tools.sh | 工具脚本语法检查 | 纯 sh 语法检查 |
| test/exec.sh | 执行检查 | 基础 |
| test/local.sh | 本地测试 | 基础 |
| test/remote.sh | 远程测试 | 需网络 |
| test/return-value.sh | 返回值检查 | 基础 |
| Makefile `test` 目标 | 整合测试（需 rsync + conf/sources 配置） | 需 rsync 环境 |

## 交付物

| 文件 | 说明 |
|------|------|
| archives/c/ccollect/1.0.0/conanfile.py | Conan 配方 |
| archives/c/ccollect/1.0.0/conandata.yml | 源码声明（官方 code.ungleich.ch 源，SHA256 已核验） |
| archives/c/ccollect/1.0.0/test_package/ | 消费者测试 |
| archives/c/ccollect/1.0.0/patches/0001-ccollect-ccollect.patch | OHOS TMPDIR 兼容补丁 |
| archives/c/ccollect/commands.json | 命令行工具声明(R38) |

## 注意事项

- ccollect 是纯 sh 脚本工具，运行时依赖 rsync/ssh 等系统命令，不在 Conan 管理范围内
- 本包为 application 类型，无库文件产出
- 平台版本 1.0.0 对应上游 tag `1.0`（VERSION="1.0"），三身份在 manifest/notes/PR 正文中分别说明

---

**编译结束**: 2026-08-26
**最终状态**: built