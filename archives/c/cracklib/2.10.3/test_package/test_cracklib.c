#include <stdio.h>
#include <string.h>
#include <crack.h>

/* 消费者侧冒烟测试（R34 反空壳）。
 *
 * 本包只交付 cracklib 的库（上游同样把字典 pw_dict* 作为独立安装项），
 * 因此本包里没有可用的默认字典。能确定的消费者契约只有一条：FascistCheck
 * 确实走到了「打开字典」这条路径并把结果报出来，而不是静默放过或直接崩溃。
 *
 * 判定方式：拿一个保证不存在的字典路径与 GetDefaultCracklibDict() 对比，
 * 两者必须给出同一条消息。若默认字典路径某天真的可用（或错误契约变化），
 * 两者不再相等，本测试立刻失败——而不是像旧版那样恒为 PASS。
 *
 * 依赖字典的语义（典内词拒绝 / 强密码通过）在配方 build() 的 L1 里验证：
 * 用上游 cracklib-packer 把随包分发的 dicts/cracklib-small 打成 testdict 后
 * 由公开 API 做 4 条断言。
 */
int main(void) {
    const char *dict = GetDefaultCracklibDict();
    if (!dict || !*dict) {
        printf("FAIL GetDefaultCracklibDict() returned no path\n");
        return 1;
    }

    const char *r = FascistCheck("abc", dict);
    if (!r) {
        /* 只有「字典可用且该口令合格」才会走到这里，本包不可能出现。 */
        printf("FAIL FascistCheck('abc', %s) returned NULL\n", dict);
        return 1;
    }

    const char *missing = FascistCheck("abc", "/nonexistent/cracklib/pw_dict");
    if (!missing) {
        printf("FAIL FascistCheck('abc', <nonexistent>) returned NULL\n");
        return 1;
    }
    if (strcmp(r, missing) != 0) {
        printf("FAIL default dict path behaved differently from a missing one:\n"
               "  default  (%s): %s\n  missing: %s\n", dict, r, missing);
        return 1;
    }

    printf("PASS test_cracklib: FascistCheck reached the dictionary path "
           "('%s') -> '%s'\n", dict, r);
    return 0;
}
