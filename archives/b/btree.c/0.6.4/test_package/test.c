#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <btree.h>

/* 业务模拟：用 B-tree 实现一个按姓名排序、可范围扫描的员工索引。
 * 仅使用 btree.h 公开 API（btree_new/btree_set/btree_get/btree_ascend/
 * btree_count/btree_free）。 */

struct user {
    char name[32];
    int age;
};

static int user_compare(const void *a, const void *b, void *udata) {
    const struct user *ua = a;
    const struct user *ub = b;
    return strcmp(ua->name, ub->name);
}

static bool user_print(const void *a, void *udata) {
    const struct user *user = a;
    int *count = udata;
    printf("  %s (age=%d)\n", user->name, user->age);
    (*count)++;
    return true;
}

int main(void) {
    struct btree *tr = btree_new(sizeof(struct user), 0, user_compare, NULL);
    if (!tr) {
        fprintf(stderr, "FAIL: btree_new returned NULL\n");
        return 1;
    }

    const struct user users[] = {
        { .name = "Dale Murphy", .age = 44 },
        { .name = "Roger Craig", .age = 68 },
        { .name = "Jane Murphy", .age = 47 },
        { .name = "Tom Buffalo", .age = 29 },
    };
    for (size_t i = 0; i < sizeof(users) / sizeof(users[0]); i++) {
        if (btree_set(tr, &users[i]) == NULL && btree_oom(tr)) {
            fprintf(stderr, "FAIL: btree_set oom\n");
            btree_free(tr);
            return 1;
        }
    }

    /* 精确查找公开 API */
    struct user key = { .name = "Jane Murphy" };
    const struct user *got = btree_get(tr, &key);
    if (!got || got->age != 47) {
        fprintf(stderr, "FAIL: btree_get Jane Murphy\n");
        btree_free(tr);
        return 1;
    }
    printf("get Jane Murphy -> age=%d\n", got->age);

    /* 缺失项 */
    key.name[0] = 'X';
    if (btree_get(tr, &key) != NULL) {
        fprintf(stderr, "FAIL: btree_get missing item\n");
        btree_free(tr);
        return 1;
    }

    /* 计数 */
    if (btree_count(tr) != 4) {
        fprintf(stderr, "FAIL: btree_count=%zu want 4\n", btree_count(tr));
        btree_free(tr);
        return 1;
    }

    /* 升序扫描（迭代公开 API + 可观察结果） */
    printf("ascend:\n");
    int scanned = 0;
    if (!btree_ascend(tr, NULL, user_print, &scanned) || scanned != 4) {
        fprintf(stderr, "FAIL: btree_ascend scanned=%d want 4\n", scanned);
        btree_free(tr);
        return 1;
    }

    /* 删除后计数 */
    if (btree_delete(tr, &(struct user){ .name = "Tom Buffalo" }) == NULL) {
        fprintf(stderr, "FAIL: btree_delete Tom Buffalo\n");
        btree_free(tr);
        return 1;
    }
    if (btree_count(tr) != 3) {
        fprintf(stderr, "FAIL: count after delete=%zu want 3\n", btree_count(tr));
        btree_free(tr);
        return 1;
    }

    btree_free(tr);
    printf("CONSUMER_PASS\n");
    return 0;
}
