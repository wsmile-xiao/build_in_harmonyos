/* libdatrie 0.2.13 真实功能断言。
 *
 * 双数组 Trie 是纯数据结构：无外部依赖、无平台相关行为，
 * 所以断言可以**全部可手算** —— 存什么取什么、走位到哪一步该成功该失败，都是定值。
 *
 * 特意包含"负例"（第②⑤条）：只验"存得进取得出"的话，
 * 一个永远返回成功的桩实现也能全绿。
 *
 * 不用 dlopen 探针：解析到 trie_new 不等于 trie 真能存取。
 */
#include <datrie/trie.h>
#include <stdio.h>
#include <string.h>

/* AlphaChar 是 uint32（datrie/triedefs.h:40）。字符串必须逐字符转，
 * 不能把 char* 直接强转 —— 那会按 4 字节一组乱读。 */
static void to_alpha(const char *s, AlphaChar *out, int cap)
{
    int i = 0;
    for (; s[i] && i < cap - 1; i++)
        out[i] = (AlphaChar)(unsigned char)s[i];
    out[i] = 0;
}

int main(void)
{
    AlphaMap *am;
    Trie *t;
    AlphaChar key[64];
    TrieData v;
    TrieState *st;
    size_t i;

    struct { const char *k; TrieData v; } items[] = {
        {"pango",      11},
        {"pangocairo", 22},
        {"graphviz",   33},
        {"gd",         44},
    };

    am = alpha_map_new();
    if (!am) { printf("FAIL alpha_map_new 返回空\n"); return 1; }
    /* 只映射 ASCII 可见区间；第⑤条会验范围外字符确实被拒 */
    if (alpha_map_add_range(am, 0x20, 0x7e) != 0) {
        printf("FAIL alpha_map_add_range\n"); alpha_map_free(am); return 1;
    }

    t = trie_new(am);
    alpha_map_free(am);                 /* trie_new 内部 clone，此处可释放 */
    if (!t) { printf("FAIL trie_new 返回空\n"); return 1; }

    /* ① 存取往返：值是定值，逐个比对 */
    for (i = 0; i < sizeof items / sizeof items[0]; i++) {
        to_alpha(items[i].k, key, 64);
        if (!trie_store(t, key, items[i].v)) {
            printf("FAIL trie_store(\"%s\")\n", items[i].k); trie_free(t); return 1;
        }
    }
    for (i = 0; i < sizeof items / sizeof items[0]; i++) {
        to_alpha(items[i].k, key, 64);
        v = TRIE_DATA_ERROR;
        if (!trie_retrieve(t, key, &v)) {
            printf("FAIL trie_retrieve(\"%s\") 未命中\n", items[i].k); trie_free(t); return 1;
        }
        if (v != items[i].v) {
            printf("FAIL \"%s\" 取出 %d，期望 %d\n", items[i].k, (int)v, (int)items[i].v);
            trie_free(t); return 1;
        }
    }
    printf("存取往返 OK: 4 个键逐个值一致\n");

    /* ② 负例：未存入的键必须取不到（"pang" 是 "pango" 的真前缀） */
    to_alpha("pang", key, 64);
    if (trie_retrieve(t, key, &v)) {
        printf("FAIL 未存入的真前缀 \"pang\" 竟命中（值 %d）\n", (int)v);
        trie_free(t); return 1;
    }
    to_alpha("zzz", key, 64);
    if (trie_retrieve(t, key, &v)) {
        printf("FAIL 未存入的 \"zzz\" 竟命中\n"); trie_free(t); return 1;
    }
    printf("负例 OK: 真前缀与无关键都正确未命中\n");

    /* ③ 前缀走位 —— trie 的核心能力，逐字符走，每步结果确定 */
    st = trie_root(t);
    if (!st) { printf("FAIL trie_root 返回空\n"); trie_free(t); return 1; }
    {
        const char *walk = "pango";
        int j;
        for (j = 0; walk[j]; j++) {
            if (!trie_state_walk(st, (AlphaChar)(unsigned char)walk[j])) {
                printf("FAIL 走到第 %d 个字符 '%c' 失败\n", j, walk[j]);
                trie_state_free(st); trie_free(t); return 1;
            }
        }
        if (!trie_state_is_terminal(st)) {
            printf("FAIL 走完 \"pango\" 不是终止态\n");
            trie_state_free(st); trie_free(t); return 1;
        }
        /* 走完后再走一个不存在的字符必须失败。
         * 注意顺序：先验越界失败，再取 data —— trie_state_walk 会改变 st，
         * 取 data 必须在 walk 之前做，否则取到的是走坏之后的状态。 */
        v = TRIE_DATA_ERROR;
        {
            TrieState *probe = trie_state_clone(st);
            if (!probe) { printf("FAIL trie_state_clone\n"); trie_state_free(st); trie_free(t); return 1; }
            if (!trie_state_walk(probe, (AlphaChar)0)) {   /* 走 0 = 到达数据节点 */
                printf("FAIL 终止态走不到数据节点\n");
                trie_state_free(probe); trie_state_free(st); trie_free(t); return 1;
            }
            v = trie_state_get_data(probe);
            trie_state_free(probe);
        }
        if (v != 11) {
            printf("FAIL 走位取值 %d != 11\n", (int)v);
            trie_state_free(st); trie_free(t); return 1;
        }
        if (trie_state_walk(st, (AlphaChar)'Z')) {
            printf("FAIL 从 \"pango\" 竟能走到 'Z'\n");
            trie_state_free(st); trie_free(t); return 1;
        }
    }
    trie_state_free(st);
    printf("前缀走位 OK: \"pango\" 逐字符到终止态、数据 11、越界走位正确失败\n");

    /* ④ 删除后取不到，且共享前缀的兄弟键不受牵连 */
    to_alpha("gd", key, 64);
    if (!trie_delete(t, key)) { printf("FAIL trie_delete(\"gd\")\n"); trie_free(t); return 1; }
    if (trie_retrieve(t, key, &v)) {
        printf("FAIL 删除后 \"gd\" 仍命中\n"); trie_free(t); return 1;
    }
    to_alpha("graphviz", key, 64);
    if (!trie_retrieve(t, key, &v) || v != 33) {
        printf("FAIL 删 \"gd\" 波及了 \"graphviz\"（取到 %d）\n", (int)v);
        trie_free(t); return 1;
    }
    /* "pangocairo" 与 "pango" 共享前缀，删了别的键后两者都要还在 */
    to_alpha("pangocairo", key, 64);
    if (!trie_retrieve(t, key, &v) || v != 22) {
        printf("FAIL \"pangocairo\" 受损（取到 %d）\n", (int)v);
        trie_free(t); return 1;
    }
    printf("删除 OK: 目标键消失、共享前缀的兄弟键完好\n");

    /* ⑤ 负例：超出 alpha_map 范围的字符必须存不进 ——
     *    证明 alpha_map 真在约束，而不是被忽略（被忽略的话前四条照样全绿） */
    key[0] = 0x4e2d;   /* 中文字符，不在 0x20-0x7e 内 */
    key[1] = 0;
    if (trie_store(t, key, 99)) {
        printf("FAIL 范围外字符竟存入成功 —— alpha_map 未生效\n");
        trie_free(t); return 1;
    }
    printf("alpha_map 约束 OK: 范围外字符正确拒绝\n");

    trie_free(t);
    printf("libdatrie 0.2.13: 全部断言通过\n");
    return 0;
}
