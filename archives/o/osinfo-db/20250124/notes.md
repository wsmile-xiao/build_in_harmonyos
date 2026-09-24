# osinfo-db 20250124 适配笔记

## 编译环境
- 构建系统: script（纯数据包，无编译）
- 编译日期: 2026-06-08
- 编译器: 无需编译器（数据包）
- 状态: built

## 编译步骤

osinfo-db 是纯数据包（XML/JSON格式的OS信息数据库），不需要编译。安装步骤：

1. init-build 下载源码并解压
2. 将数据文件直接复制到 DESTDIR 的 `$DEFAULT_PREFIX/share/osinfo/` 目录
3. 安装的文件包括: VERSION, LICENSE, datamap/, device/, os/, platform/, install-script/, schema/
4. 总共 1070 个数据文件

```bash
source .build-context-osinfo-db-20250124
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/share/osinfo
cd $BUILD_SRC_DIR
cp -r VERSION LICENSE datamap device os platform install-script schema $TEST_PREFIX/$DEFAULT_PREFIX/share/osinfo/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub/GitLab无法直接下载 | 网络限制+Anubis反爬保护 | 从Fedora镜像下载SRPM并提取原始tarball |
| 2 | 版本查找困难 | osinfo-db使用日期版本号 | 从Fedora镜像找到20250124版本 |

## 源码修改

无源码修改，纯数据包不修改源文件。

## 依赖版本

无编译依赖，纯数据包。

## 验证结果

```bash
# 检查安装文件数量
find $TEST_PREFIX/$DEFAULT_PREFIX/share/osinfo/ -type f | wc -l
# 结果: 1070

# 检查安装结构
ls $TEST_PREFIX/$DEFAULT_PREFIX/share/osinfo/
# VERSION LICENSE datamap device os platform install-script schema
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| osinfo-db-20250124-ohos-aarch64.tar.gz | ~159KB | 预编译数据包（aarch64） |
| osinfo-db-20250124-ohos-aarch64-debug.tar.gz | ~159KB | 预编译数据包（debug） |

## 注意事项

- osinfo-db是纯数据包，不需要编译，只需将数据文件安装到正确路径
- 数据安装路径: `$PREFIX/share/osinfo/`
- 通常通过osinfo-db-import工具安装，但本平台没有此工具，手动复制数据文件即可
---

**编译结束**: 2026-08-26 00:34
**最终状态**: built

## 重试会话复验记录（2026-09-20）

第 2 次尝试接续修复：服务端校验 PR #6637 时报 `sha mismatch`（前序会话
result.json 的 commit_hash 取自错误仓库状态，与 PR 分支头不一致），本包
配方本身 CI/AI 检视均已通过，无需改动 conanfile.py/conandata.yml/test_package。

本次动作：

1. 检出 `feat/osinfo-db-20250124`，本地复验 `conan create`（ohos-aarch64
   profile）——test_package 通过：`version=20250124, os_xml=930, total_files=1077`
2. 手工下载源码核验 sha256：`7ca717f0...7250` 与 conandata.yml 一致，
   并将 manifest.yaml 中空缺的 `source.sha256` 字段补齐
3. 推送本提交更新 PR 头部 SHA，重新触发 CI 并确认通过后，以正确的
   pr_url/pr_number/commit_hash/branch 重写 result.json

**复验结论**: 配方自包含可复现，数据包安装结构与版本校验均正常。
