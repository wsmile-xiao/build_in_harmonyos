# xmlformat 1.04 适配笔记

## 编译环境
- 构建系统: custom（纯 Perl/Ruby 脚本工具，无需编译）
- 编译日期: 2026-08-04
- 编译器: N/A（脚本工具）
- 状态: built

## 软件概述

xmlformat 是一个 XML 文档格式化工具，用 Perl 和 Ruby 各写了一份同名实现
（xmlformat.pl / xmlformat.rb），输出应一致。上游 tarball 内：

- xmlformat.pl — Perl 实现（shebang `#!/usr/bin/perl -w`）
- xmlformat.rb — Ruby 实现（shebang `#!/usr/bin/ruby -w`）
- runtest     — 测试驱动脚本，按 `tests/*.xml` 命名跑用例，diff 对比 .res
- tests/      — 27 个正常用例（每个含 .xml 输入 + .res 预期输出 + 可选 .conf）
- bad1~5.xml/res — 5 个反面用例（畸形 XML，xmlformat 应报错并退出）
- Makefile 的 `test` 目标依次跑 Ruby 版（`runtest all`）和 Perl 版（`runtest -p all`）

## 编译步骤

纯脚本工具，无编译。conan recipe 直接下载源码包：
- 把 xmlformat.pl 安装为 bin/xmlformat（按 INSTALL 建议去掉 .pl 扩展名）
- 同时附带 xmlformat.rb（有 ruby 的环境可用，无 ruby 不影响）
- 安装 man 手册（docs/xmlformat.1 若存在）与示例配置（docs/xmlformat.conf）

## 上游测试套件执行

上游"测试套件" = 27 个 tests/*.xml 正面用例 + 5 个 bad*.xml 反面用例 = 32 个用例。
驱动方式：`./runtest -p all`（Perl 版）+ 逐个 `./xmlformat.pl badN.xml` 对照 badN.res。

**已踩的坑（重要）**：runtest 用 `diff -u $BASE.res $BASE.out` 比对输出，但**不检查
diff 的退出码**——即使输出不一致也整体返回 0。已验证：把 xmlformat.pl 换成只打印
"broken output" 的桩后，runtest 会打印 diff（用例确实失败）但进程退出码仍是 0。
所以不能信 runtest 的退出码，必须检查 diff 输出是否为空。

conanfile.py build() 里用一段 shell 把每个用例的 runtest 输出收集起来：
- runtest 对单个用例的输出 = diff 正文；输出非空 → 失败
- bad*.xml 直接跑 xmlformat.pl 并 diff bad*.res

本地用 perl 5.38 实跑：27 个正面用例全过（diff 输出为空），5 个反面用例全过
（xmlformat 输出与 bad*.res 一致）。即 32/32。

HarmonyOS PC 自带 perl（/usr/bin/perl），但**无 ruby**，所以本次只接了 Perl 版；
上游 `make test` 同时跑 Ruby 版的那部分在鸿蒙真机上无法执行，PR 正文已如实说明。

## 遇到的问题与解决方案

1. **上游官网 kitebird.com 下线**：原始 http://www.kitebird.com/software/xmlformat/
   已不可达。改用 MacPorts distfiles 镜像（distfiles.macports.org），其 tarball 字节
   数 156498 与 Debian 官方记录一致，sha256
   `71a70397e44760d67645007ad85fea99736f4b6f8679067a3b5f010589fd8fef`
   与 Debian sources 记录完全相同 → 同一份官方源码包，可信。

2. **runtest 不报失败**：如上"已踩的坑"，用 diff 输出非空判定失败，不信退出码。

3. **Ruby 不可用**：鸿蒙真机无 ruby，只适配 Perl 版；Ruby 脚本仍随包附带。

## 源码修改

无（未修改上游任何源码或测试）。

## 依赖版本

- 运行时：perl（鸿蒙自带，版本 >= 5 即可，xmlformat.pl 无外部模块依赖）
- 构建时：无（脚本工具）

## 验证结果

```bash
# 上游测试套件（Perl 版，32 个用例）
cd <src>
./runtest -p all          # 27 个 tests/*.xml，全 diff 通过（输出为空）
for i in 1 2 3 4 5; do    # 5 个反面用例
  ./xmlformat.pl bad$i.xml > bad$i.out
  diff -u bad$i.res bad$i.out   # 全一致
done

# test_package（消费者侧 smoke）
xmlformat --version       # 或运行 xmlformat 对一个样例 XML 产格式化输出
```

## 注意事项

- 纯脚本，无交叉编译；配方不读 compiler settings，仅声明 os/arch
- 上游 Ruby 版测试（`make test` 的前半 `runtest all`）在鸿蒙真机无法跑（无 ruby），
  已在 PR 正文「补充说明」如实写明
- runtest 的退出码不可信，配方中以 diff 输出是否为空判定通过

---

**编译结束**: 2026-08-04
**最终状态**: built
