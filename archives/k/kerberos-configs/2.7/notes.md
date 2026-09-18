# kerberos-configs 2.7 适配笔记

## 上游真源码包

- 上游仓库: https://github.com/deepin-community/kerberos-configs（deepin 移植的 Debian kerberos-configs）
- tag 2.7 归档: https://codeload.github.com/deepin-community/kerberos-configs/tar.gz/refs/tags/2.7
- sha256: b77e8802b4c0907309a3afa238d6d3c5ecb6a5bb30a4c3c5d7ad8ed9142cae33（31572 字节）
- 三维核验: 制品仓无 / main 无归档 / 上游 tag 2.7 实存（HTTP 200）

## 构建系统

**纯配置包（build_system: none）**。上游为 Debian 源码包结构：
- `debian/krb5-config.install`：`krb5.conf.template usr/share/kerberos-configs`——deb 包载荷就这一个配置文件
- `debian/rules`：`genblob`（perl）把 krb5.conf.template 解析成 realm_map/domain_map 数据块，
  与 `krb5-config.in`（debconf 交互脚本）拼接出 `debian/krb5-config.config`——这是
  **Debian debconf 安装器机制专属产物**（依赖 Debconf::Client::ConfModule），对 conan/OHOS 交付无意义
- `krb5confparse.pl`：krb5.conf 解析模块（genblob 引用）
- 无 configure/无 Makefile 编译目标/无 C 代码

**适配策略（packaging-only 模式）**：跳过 debconf 拼接，直接安装配置载荷到
`share/kerberos-configs/`（对齐 deb install 路径）：krb5.conf.template（主载荷）+
krb5confparse.pl（realm 解析模块，供消费方复用）+ README/packaging-guidelines（docs）。

本机实测上游 genblob 可运行（perl），输出 32 行 realm_map/domain_map 数据块——
上游逻辑健康，仅在 OHOS 无 Debconf 模块环境不适用。

## 上游测试案例（N=0 如实申报）

- 上游仓库**无自动化测试套件**：无 tests/ 目录、无 CI 测试目标
  （.github/workflows 仅 call-auto-tag/call-chatOps 打标签工作流）
- 根目录 `test-cases` 文件是**人工测试清单**（首行 "When testing major changes to
  krb5-config, the following are currently covered"，内容为"confirm we walk up the
  realm tree / set hostname to a.b.domain..."等人工操作步骤——需人工配置 DNS TXT
  记录、修改 hostname、降低 debconf 优先度），**非可执行自动化测试**，不构成测试用例数
- debian/rules 无 make check/test 目标
- N=0 声明依据：`find . -name "*test*"` 仅命中人工清单文件；grep 无 add_test/ctest 注册

## 适配后新增测试案例（M=6，全通过）

test_package/test_kerberos_configs.sh（POSIX sh + grep/wc）：
1. 载荷落位：krb5.conf.template/krb5confparse.pl/README/packaging-guidelines 四文件存在
2. krb5.conf 语法健全：[libdefaults]/[realms]/[domain_realm] 三段必备段存在
3. realm 块花括号配平（10/10）
4. [libdefaults] 段 default_realm 赋值存在
5. 内容完整性标记：ATHENA.MIT.EDU/stanford.edu/kerberos.mit.edu
6. 模板规模健全（84 行 ≥ 80）

通过率 6/6 = 100%。

不引入 perl/python3 解释器调用（OHOS CI worker 上 python3/perl 不可用/卡死——
adduser #17506 教训）；shell 内建+grep/wc 是最稳路径。

## 依赖

零依赖：纯配置数据，无 requires/tool_requires（PF4 依赖闸直接过）。
运行时与 krb5 主件（archives/k/krb5 1.22.x 已在库）天然配合——krb5 库读
/etc/krb5.conf，本包提供模板源。deb 侧 Depends bind9-host 仅用于安装时
DNS 探测，非配置文件本身的依赖。

## license 核对

GPL-2.0-only（debian/copyright 明示 "only version 2 of the License is permitted"）。

## 鸿蒙特有适配

- validate 段 settings.os in (Linux, OHOS)（R32）
- 无补丁：配置文件内容平台无关（INI 文本），原样安装
- 纯配置包无 ELF 产物：R38 commands.json 不适用（adduser/acf-unbound 同款先例）
- package_type="library" + cpp_info 清空 libs/bindirs + resdirs 声明资源目录

## 源码 URL 直链策略

codeload.github.com 直链（200 无跳转）替代 github.com archive 形态（302 重定向
依赖 curl -L，worker 缺 curl 时整链死——mmkv #9693 教训）。两种形态 sha256 实测
一致（b77e8802...）。

## CI 轮次记录（#50186 → 修复）

- 轮 1（#50186，CI-007）：L0p 门禁挂——settings 只声明 os/arch 两项，L0p 要求四项全
  （os/compiler/build_type/arch）。8 月合入的 adduser/acf-unbound（os/arch 两项）是
  L0p 上线前的先例，不可照抄。
- 修复：settings 四项 + package_id() 里 self.info.clear() 做 noarch 归一
  （adamstark-audiofile 1.1.4 先例）——纯配置数据与 os/compiler/build_type/arch
  组合无关，info.clear 后 package id 归一为空设置哈希 da39a3ee...
