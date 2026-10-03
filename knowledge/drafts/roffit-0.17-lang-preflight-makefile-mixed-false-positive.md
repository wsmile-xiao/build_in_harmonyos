# E-draft: lang-preflight 对纯脚本工具 + 顶层 Makefile 包误报 mixed

## 现象

`ohc-run.py lang-preflight roffit 0.17 --src <src> --lang perl` 判定：

```
❌ 语言不匹配: task=perl, detected=mixed → env_unsupported
language_evidence:
  build_system: make
  manifest: 顶层 Makefile（无更强 manifest）
  source_stats: 源文件 1 个（perl:1），主体占比 100%
notes: 冲突: manifest=c 但统计 perl 占 100% → mixed
```

## 根因

lang_detect 的 manifest 级判定把"顶层 Makefile"当作 c 语言 manifest。纯脚本
CLI 工具（roffit = 单文件 Perl 脚本，Makefile 仅有 install/test 目标）源码统计
为 perl 100%，两者矛盾 → mixed 误报 → env_unsupported 终止。

## 复核与处置

1. 读 `language_evidence.source_stats`：单一脚本语言 100% + 构建系统仅 Makefile
   → 脚本工具，不是 mixed。人工复核后继续适配（仓库先例：abcselect 1.5 纯 Perl）。
2. 配方模式：settings 四项齐全（L0p）、requires perl/5.42.2.3、build() 仅打补丁、
   package() 拷脚本 + man 页 + LICENSE（licenses/ 目录记得 makedirs）。
3. 附带坑：HTML::Entities 属 CPAN HTML-Parser 模块（非 perl 核心），ohpcd perl 包
   不含 → 用纯 Perl 正则等价实现 `encode_entities($s, q{<>&"'#})`（& < > " ' #
   七字符，`&#39;`/`&#35;` 数字实体），上游黄金文件 testpage.output 逐字节比对
   验证一致后再打 patch（patches/0001-roffit.patch）。

## 验证

roffit/0.17：conan-verify G0-G4 + L2/L4/L5 全 PASS；W3 本地 CI L0-L5 全 pass；
上游 make test 1/1（100%）；test_package 3/3（2026-10-02，真机 aarch64）。
