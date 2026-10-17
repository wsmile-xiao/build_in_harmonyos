# dh-linktree 0.9 适配笔记

## 适配环境
- **构建系统**: none（纯 Perl 脚本打包，零编译）
- **适配日期**: 2026-09-10
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）
- **运行时依赖**: debhelper/13.3.4（Debian::Debhelper::Dh_Lib）、dpkg/1.23.7（Dpkg::IPC 模块 + dpkg/dpkg-query 命令）

## 适配步骤（conan create 全流程）

```bash
conan create archives/d/dh-linktree/0.9 -pr:h ci/conan/profiles/ohos-aarch64 --build=missing
```

### 1. 源码获取（source()）
沙箱 `get()` 有 PermissionError 风险——`download()` + 手动解压：
```bash
tar -xJf dh-linktree_0.9.tar.xz --no-same-owner || true
cp -a dh-linktree/. . && rm -rf dh-linktree
```
tarball 内容（8.5 KiB，sha256=ea968315…f0253bfd 与 Launchpad 公开值双源核对一致）：
- `dh_linktree`（327 行 Perl，debhelper 的 dh_* 插件）
- `linktree.pm`（8 行 dh sequence 插件）
- `dh_linktree.1`（man 页）
- `debian/`（打包元数据：rules 仅 dh + pod2man，无测试套件）

### 2. 构建（build()）
纯 Perl 无编译步骤——`build()` 直接 `pass`。

### 3. 打包（package()）
挑文件安装（禁止整目录拷贝）：
- `dh_linktree` → `<pkg>/bin/dh_linktree`（chmod 0o755）
- `linktree.pm` → `<pkg>/lib/perl5/Debian/Debhelper/Sequence/linktree.pm`
- `dh_linktree.1` → `<pkg>/share/man/man1/dh_linktree.1`
- `package_info()`：`cpp_info.libs=[]`、`bindirs=["bin"]`

### 4. 消费者验证（test_package，test_type="explicit"）
- **R1 文件存在断言**：bin/dh_linktree + Sequence/linktree.pm（2 断言）
- **R2 perl -c 语法检查**：PERL5LIB 加入本包与依赖包（debhelper/dpkg）的 perl 库根，dh_linktree 与 linktree.pm 均 `perl -c` 退出码 0（2 断言）。注意：不能把整个依赖树含 .pm 的目录都加入 PERL5LIB——实测 dpkg 包的 Dselect/Method/Config.pm 会遮蔽 perl 核心 Config 模块导致 Errno.pm 编译失败
- **R3 功能冒烟（尽力）**：最小 debian 骨架（debian/control）+ 可写绝对路径源目录，真实运行 `dh_linktree embed <src> usr/share/smoke/lib`——符号链接树创建成功（1 断言）；脚本尾部 `dpkg --search` 因沙箱无 dpkg 数据库受阻，如实记录为"受限通过"（不伪造通过率）

## 验证结果
- **构建**: `dh-linktree/0.9: Package created`
- **R34 消费者验证**: test_package/test_dh_linktree.py — 5 断言全过（文件存在 2 + 语法检查 2 + 符号链接树创建 1）；dpkg --search 阶段受限（无 dpkg 数据库，如实记录）
- **上游测试**: 无（上游无测试套件——debian/rules 仅 dh + pod2man，tar tJf 核验，rule 4 如实记录）

## 已知限制
- `dh_linktree` 完整运行（生成 ${misc:Depends} 依赖）需 Debian dpkg 数据库，OHOS 沙箱无此环境——冒烟只验证到符号链接树创建
- 上游 man 页由 pod2man 生成，直接安装上游自带 dh_linktree.1
