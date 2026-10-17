#include <gtkspell/gtkspell.h>
#include <stdio.h>
#include <stdlib.h>

/* gtkspell3 真实 API 冒烟测试（无显示环境可运行）：
 * 1. gtk_spell_error_quark() 返回有效 error domain
 * 2. gtk_spell_checker_get_type() 注册的 GObject 类型有效
 * 3. gtk_spell_checker_new() 可创建对象（GObject 构造）
 * 4. gtk_spell_checker_get_language_list() 可查询 enchant 语言列表
 */
int main(void) {
    GQuark q = gtk_spell_error_quark();
    if (q == 0) {
        fprintf(stderr, "FAIL: gtk_spell_error_quark() == 0\n");
        return 1;
    }

    GType t = gtk_spell_checker_get_type();
    if (t == 0) {
        fprintf(stderr, "FAIL: gtk_spell_checker_get_type() == 0\n");
        return 1;
    }

    GtkSpellChecker *checker = gtk_spell_checker_new();
    if (checker == NULL) {
        fprintf(stderr, "FAIL: gtk_spell_checker_new() returned NULL\n");
        return 1;
    }
    if (!GTK_SPELL_IS_CHECKER(checker)) {
        fprintf(stderr, "FAIL: created object is not GtkSpellChecker\n");
        g_object_unref(checker);
        return 1;
    }
    g_object_unref(checker);

    /* 查询 enchant 可用语言列表（无词典环境允许返回空列表） */
    GList *langs = gtk_spell_checker_get_language_list();
    g_list_free_full(langs, g_free);

    printf("gtkspell3 3.0.10-r3 smoke test OK (quark=%u, type=%lu)\n",
           (unsigned)q, (unsigned long)t);
    return 0;
}
