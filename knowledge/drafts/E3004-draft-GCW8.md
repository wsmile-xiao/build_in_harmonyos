# DRAFT-E3004：PIDL + Parse::Yapp 生成器依赖降级（vendored + 预生成）

- **触发实例**：samba 4.21.0 适配（2026-09-21，分支 feat/samba-4.21.0，PIDL 生成 NDR/RPC 代码）
- **错误签名**：`Can't locate Yapp` / `Parse::Yapp` / `pidl: ... failed`
- **类别**：build-system（生成器依赖）/ perl / IDL
- **严重度**：2（早期硬失败，但 release 产物自带补丁可降级）

## 症状（可复现）

PIDL（IDL → NDR/RPC 代码生成器）依赖 Perl 模块 Parse::Yapp（yapp 命令）对 IDL 文法做 LR 解析。OHOS 无 yapp/Parse::Yapp，且 perl tool_requires 也不含：

```text
Can't locate Yapp/Parse/Yapp/Driver.pm in @INC ...
pidl: configure: couldn't find perl module Parse::Yapp (yapp)
```

## 根因

Samba 的 PIDL 生成器对 IDL 文件生成时调用 yapp 做解析。但 **release tarball 自带预生成的解析器**（IDL.pm/Expr.pm 等），因此"yapp 缺失"不必然致命——上游把缺失当硬失败是过度防御。若本地构建时 yapp 缺失即中断，则无法利用预生成产物。

## 方案

1. **配方 `tool_requires` 声明 perl**；
2. **vendored `Parse::Yapp::Driver.pm`**（来源 CPAN Parse-Yapp 1.21），经 conan `export_sources` 注入，并设 `PERL5LIB` 使其可加载；
3. **PIDL wscript 把"yapp 缺失"由硬失败改为 `Logs.warn` 降级**——release tarball 带预生成解析器，生成阶段用预生成产物即可。

对应 patch：`0004-pidl-wscript.patch` + `export_sources(parse-yapp/Parse/Yapp/Driver.pm)`。

## 验证

```sh
# PERL5LIB 指向 vendored 解析器；缺 yapp 时走 warning 而非失败，PIDL 正常生成
export PERL5LIB=<vendored-parse-yapp>; python3 buildtools/bin/waf pidl
```

samba 4.21.0 全量生成 NDR/RPC 代码（2,000+ 文件）成功。

## 边界 / 禁止

- 不伪造生成器产物；不硬编码设备路径到 pm 加载路径；
- 若 release 无预生成产物，须真正安装 Parse::Yapp（如 cpanm）而非降级静默；
- 降级 target 生代码要能被真实校验（编译+运行通过）。

## 关联

- 触发 PR：!11515。
