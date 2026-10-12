# DRAFT-E-musl-regfree-double-free: musl regcomp 后端双重 regfree 段错误

## 现象

libgit2 1.9.6（libgit2-tools）在 OHOS（musl libc）上以
`REGEX_BACKEND=regcomp` 构建时，上游测试
`test_diff_userdiff__compile_userdiff_regexps` 100% 段错误，且与前置
suite 状态无关（任意组合都崩）。崩溃点输出停在 "Loaded 387 suites:"
之后、任何测试结果之前，易误判为环境/沙箱问题。

## 根因

- 上游测试模式（tests/libgit2/diff/userdiff.c）：

```c
static git_regexp regex;              /* 全局静态 */

void test_diff_userdiff__cleanup(void)
{
    git_regexp_dispose(&regex);       /* 测试后无条件 dispose */
}

void test_diff_userdiff__compile_userdiff_regexps(void)
{
    for (idx = 0; idx < ARRAY_SIZE(builtin_defs); ++idx) {
        cl_git_pass(git_regexp_compile(&regex, ddef.fns, ddef.flags));
        git_regexp_dispose(&regex);   /* 循环内已 dispose */
        ...
    }
}
```

- libgit2 REGCOMP 后端的 dispose（src/util/regexp.c）：

```c
void git_regexp_dispose(git_regexp *r)
{
    regfree(r);                       /* 裸 regfree，无防护 */
}
```

对照 pcre2/builtin 后端：`pcre2_code_free(*r); *r = NULL;`——带
置空防护，同一测试模式安全。

- musl regfree 对已释放的 regex_t 二次调用直接崩溃（无 glibc 的
  `re_magic` 静默返回路径）。

## 定性方法（5 秒最小复现）

```c
#include <regex.h>
int main(void){
    regex_t r;
    regcomp(&r, "abc", REG_EXTENDED);
    regfree(&r);
    regfree(&r);   /* Segmentation fault on musl/OHOS */
    return 0;
}
```

LD_PRELOAD 拦截法（区分"正则内容问题"与"释放问题"）：预加载一个
hook regcomp/regfree 并打印的 .so，观察崩溃前最后一个调用是否为
多余的 regfree。

## 修复

不指定 `REGEX_BACKEND`，走上游 SelectRegex.cmake 自动检测：
OHOS 上（无 `regcomp_l`、无系统 PCRE）→ bundled PCRE2（"builtin"
后端），dispose 安全。特性输出确认：`regex, using bundled PCRE`。

## 通用性

去掉 libgit2 这个名字，本坑对任何满足以下条件的 C 库都成立：
1. 目标平台 musl libc（OHOS/Alpine）；
2. 提供 regex 后端抽象，REGCOMP 后端的 dispose 是裸 regfree；
3. 存在"循环内 compile→dispose + cleanup 再 dispose"或任何双重
   dispose 的调用路径。

## 验证

- libgit2-tools/1.9.6 conan create（OHOS aarch64，clang 15，
  bundled PCRE2）通过；
- libgit2_tests offline 入口 3010 用例（2931 pass + 79 SKIP）0 失败；
  invasive 入口 41 用例（39 pass + 2 SKIP）0 失败；
- 修复前同构建 regcomp 后端在 userdiff 套件 100% 段错误。

## 记录

- first_seen: 2026-09-18，libgit2-tools 1.9.6 适配（任务 #13202）
- author: j669539
