#include <stdio.h>
#include <string.h>
#include <crack.h>

/* 消费者侧冒烟测试（R34 反空壳）。
 *
 * 本包只交付 cracklib 的库（上游同样把字典 pw_dict* 作为独立安装项），
 * 因此本包里没有可用的默认字典。能确定的消费者契约只有一条：FascistCheck
 * 确实走到了「打开字典」这条路径并把结果报出来，而不是静默放过或直接崩溃。
 *
 * 判定方式（R03 按审查意见强化）：用足长密码（通过 FascistCheck 内部长度/
 * 规则预检查，确保任何返回都必须来自字典装载路径本身）+ 不存在的字典路径，
 * 断言确定性错误消息 "error loading dictionary"（字典打开失败时的固定返回）。
 * 与 GetDefaultCracklibDict() 对比：若默认字典路径某天真的可用（或错误契约
 * 变化），两者不再相等，本测试立刻失败——而不是像旧版那样恒为 PASS。
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

    /* 足长密码：长度/规则预检查均通过，任何非 NULL 返回必来自字典装载路径 */
    const char *pw = "CorrectHorseBatteryStaple!2026";
    const char *r = FascistCheck(pw, dict);
    if (!r) {
        /* 只有「字典可用且该口令合格」才会走到这里，本包不可能出现。 */
        printf("FAIL FascistCheck('%s', %s) returned NULL\n", pw, dict);
        return 1;
    }

    const char *missing = FascistCheck(pw, "/nonexistent/cracklib/pw_dict");
    if (!missing) {
        printf("FAIL FascistCheck('%s', <nonexistent>) returned NULL\n", pw);
        return 1;
    }
    if (strcmp(missing, "error loading dictionary") != 0) {
        printf("FAIL nonexistent dict did not yield the deterministic "
               "'error loading dictionary' message: got '%s'\n", missing);
        return 1;
    }
    if (strcmp(r, missing) != 0) {
        printf("FAIL default dict path behaved differently from a missing one:\n"
               "  default  (%s): %s\n  missing: %s\n", dict, r, missing);
        return 1;
    }

    printf("PASS test_cracklib: FascistCheck reached the dictionary-loading "
           "path ('%s') -> '%s'\n", dict, r);
    return 0;
}
