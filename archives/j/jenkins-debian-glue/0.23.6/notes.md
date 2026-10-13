# jenkins-debian-glue 0.23.6 — OHOS 适配笔记

## 软件概况

- 上游: https://github.com/mika/jenkins-debian-glue（tag v0.23.6）
- 构成: scripts/（10 个 jdg-* bash/sh/ruby 脚本）+ tap/（8 个 ruby TAP
  辅助脚本）+ examples/ + pbuilder-hookdir/，顶层 Makefile 仅做 install
- 构建系统: none（纯脚本安装，package_type=application，package_id 清空）
- 无 conan 依赖（R36 检查：requires 为空；运行时依赖系统
  bash/grep/file/ruby，OHOS PC 全部内置）

## 适配路径判定

路径 A（认领库）。理由：零编译脚本工具，适配面仅为 shebang 与 file(1)
选项移植，无强绑定 Debian 私有接口的不可绕过障碍（完整 deb 构建功能
依赖 dpkg 工具链，但脚本可正常安装、通用功能可运行可测试），不构成
路径 B/C 条件。

## 语言预检说明（R47）

`lang-preflight` 判 detected=mixed → env_unsupported，经分析为**误报**：

1. 源码主体是 bash 脚本，lang_detect 按 D.4 规则将 bash 排除出主体统计；
2. 剩余唯一非 bash 文件为 fabfile.py（Fabric 部署辅助脚本），被判
   "python 主体 100%"（total=1）；
3. "冲突"来自顶层 Makefile（工具自注"无更强 manifest"——它是打包
   Makefile，不是语言 manifest）。

本包实际主体为 bash 脚本工具，走 SKILL v12.21 脚本工具配方路径
（先例：archives/r/roffit/0.17，单脚本工具，published），零编译，
无 C/C++ 工具链需求，R47 防浪费编译的目的实质不适用。任务明确指定
适配本库，故继续。已将本说明同步写入 manifest.yaml。

## 上游测试三步法（R51）

清点：tests/ 共 3 个测试文件（shunit2 框架，共 18 项断言）：
tests/increase-version-number（13）、tests/merge-conflict（3）、
tests/file-detection（2）；`make check` 注册 3 项。

运行：shunit2 在 OHOS 不可用（/usr/share/shunit2 不存在，制品仓无此
包），无法按上游框架逐字运行。处理：test_package 以纯 bash 逐项 1:1
重放全部 18 项断言 + 1 项后缀断言 + 2 项 pep8 tap 门控补充断言
（上游无 pep8 专项测试，仿上游 tests/file-detection 的 fake 工具
shim 惯例补充，防 mimetype 门控回归）= 21 项，实测 21/21 通过。

差异说明：
- increase-version-number：13 项断言逐字重放，无差异
- merge-conflict：KO 文件 TAP 输出与上游期望**字节级一致**；
  目录输入用例上游硬编码 /tmp（OHOS /tmp 只读），改传 fixtures 目录
- file-detection：上游断言完整文案含 Debian file(1) 的 mimetype
  输出 "[POSIX shell script, ASCII text executable]"；OHOS file(1)
  输出 "[/bin/sh script]"（平台 file 实现差异），断言放宽为
  "doesn't look like perl" + "Ignoring." 前后缀匹配，检测行为等价

## 补丁说明

patches/0001-ohos-portability.patch（portability 类，无平台宏，PF5 通过）：
1. scripts/*（9 个 /bin/bash）与 pbuilder-hookdir/B90lintian：
   shebang → `#!/usr/bin/env bash`（OHOS 无 /bin/bash）
2. tap/jdg-tap-shellcheck、jdg-tap-checkbashism、jdg-tap-pep8、
   jdg-tap-perlcritic：`file -Pbytes=32 -b -i`/`file -Pbytes=32 -b`
   → `file -b`（OHOS file 不支持 -Pbytes/-i）；
   mimetype 匹配正则与命令成对修改（命令与正则必须同步，否则
   可读输出不含 mimetype 子串导致静默漏检）：
   - shellcheck/checkbashism：`/.*x-shellscript/i` → `/script/i`
   - pep8：`/.*x-python/i ... /.*x-script\.python/i` → `/python/i`
   （file -b 输出人类可读类型如 "/bin/sh script"/"python3 script"，
   在 Debian 上同样匹配，行为等价）

补丁后实测：jdg-tap-shellcheck 输出 "1..0"（与上游 testOK 一致）、
jdg-tap-perlcritic 优雅忽略、jdg-tap-merge-conflict 输出与上游期望
字节级一致。

## 验证结论

- conan create 全流程通过（见 .ci-result.json）
- test_package: 21/21 通过（100%）
- R38: 产物为可执行脚本集，软件级 commands.json 已声明
---

**编译结束**: 2026-10-11 10:32
**最终状态**: published
