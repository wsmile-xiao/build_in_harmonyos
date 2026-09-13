/* 消费者测试：真实调用 c-rbtree API。验证：按键插入后的有序性（中序正/反向遍历）、
 * 后序遍历恰好覆盖全部结点、结点移除后重插树仍有序、c_rbtree_move 搬移后内容一致。
 */
#include <assert.h>
#include <stdlib.h>
#include <c-rbtree.h>

typedef struct {
        int key;
        CRBNode rb;
} Node;

static Node *node_of(CRBNode *n) {
        return c_rbnode_entry(n, Node, rb);
}

/* 按键搜索插入槽位；返回 NULL 表示键已存在（上游惯例：升序比较） */
static CRBNode **find_slot(CRBTree *t, int key, CRBNode **parent) {
        CRBNode **slot = &t->root;
        *parent = NULL;
        while (*slot) {
                Node *e = node_of(*slot);
                if (key < e->key) {
                        *parent = *slot;
                        slot = &(*slot)->left;
                } else if (key > e->key) {
                        *parent = *slot;
                        slot = &(*slot)->right;
                } else {
                        return NULL;
                }
        }
        return slot;
}

static Node *insert(CRBTree *t, int key) {
        CRBNode *parent = NULL;
        CRBNode **slot = find_slot(t, key, &parent);
        assert(slot);
        Node *n = malloc(sizeof(*n));
        assert(n);
        n->key = key;
        c_rbnode_init(&n->rb);
        c_rbtree_add(t, parent, slot, &n->rb);
        return n;
}

int main(void) {
        CRBTree t;
        c_rbtree_init(&t);

        /* 乱序插入 9 个键，触发多次再平衡 */
        int keys[] = {5, 3, 8, 1, 4, 7, 9, 2, 6};
        for (size_t i = 0; i < sizeof(keys) / sizeof(*keys); ++i)
                insert(&t, keys[i]);

        /* 中序正向遍历必须严格升序 1..9 */
        size_t n = 0;
        int last_key = 0;
        for (CRBNode *i = c_rbtree_first(&t); i; i = c_rbnode_next(i)) {
                Node *e = node_of(i);
                assert(e->key == ++last_key);
                ++n;
        }
        assert(n == 9);

        /* 中序反向遍历必须严格降序 9..1 */
        n = 0;
        last_key = 10;
        for (CRBNode *i = c_rbtree_last(&t); i; i = c_rbnode_prev(i)) {
                Node *e = node_of(i);
                assert(e->key == --last_key);
                ++n;
        }
        assert(n == 9);

        /* 后序遍历恰好覆盖全部结点各一次 */
        n = 0;
        for (CRBNode *i = c_rbtree_first_postorder(&t); i; i = c_rbnode_next_postorder(i))
                ++n;
        assert(n == 9);

        /* 移除中间键后重插，树仍有序且计数不变 */
        CRBNode *mid = c_rbtree_first(&t);
        while (node_of(mid)->key != 5)
                mid = c_rbnode_next(mid);
        c_rbnode_unlink(mid);
        free(node_of(mid));
        insert(&t, 5);
        n = 0;
        last_key = 0;
        for (CRBNode *i = c_rbtree_first(&t); i; i = c_rbnode_next(i)) {
                Node *e = node_of(i);
                assert(e->key == ++last_key);
                ++n;
        }
        assert(n == 9);

        /* c_rbtree_move 搬移后内容一致，遍历仍有序（目标树须初始化且为空） */
        CRBTree t2;
        c_rbtree_init(&t2);
        c_rbtree_move(&t2, &t);
        n = 0;
        last_key = 0;
        for (CRBNode *i = c_rbtree_first(&t2); i; i = c_rbnode_next(i)) {
                Node *e = node_of(i);
                assert(e->key == ++last_key);
                ++n;
        }
        assert(n == 9);

        /* 清理全部结点 */
        CRBNode *i = c_rbtree_first(&t2);
        while (i) {
                CRBNode *next = c_rbnode_next(i);
                c_rbnode_unlink(i);
                free(node_of(i));
                i = next;
        }
        return 0;
}
