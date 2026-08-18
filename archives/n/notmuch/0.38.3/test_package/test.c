/* test.c — notmuch consumer smoke test
 *
 * 验证 libnotmuch 核心功能（对应上游 T000-basic/T060-count/T080-search 的
 * 功能语义，用 C API 等价实现——完整 TAP 框架依赖 bash+emacs+test 辅助程序，
 * OHOS headless 无法运行，见 manifest runnable_note）：
 *   1) 数据库创建 + 版本读取
 *   2) 邮件索引（notmuch_database_add_message）
 *   3) 搜索查询（notmuch_query_create / search_messages / count_messages）
 */
#include <notmuch.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include <dirent.h>

/* 递归删除目录（不用 system("rm -rf ...")——避免 shell 注入与未检查返回值，
   也覆盖 mkdtemp 后所有错误返回路径的临时目录清理） */
static void cleanup_dir(const char *path) {
    DIR *d = opendir(path);
    if (d == NULL) return;
    struct dirent *e;
    while ((e = readdir(d)) != NULL) {
        if (strcmp(e->d_name, ".") == 0 || strcmp(e->d_name, "..") == 0) continue;
        char full[1024];
        snprintf(full, sizeof(full), "%s/%s", path, e->d_name);
        struct stat st;
        if (lstat(full, &st) == 0 && S_ISDIR(st.st_mode)) {
            cleanup_dir(full);
        } else {
            unlink(full);
        }
    }
    closedir(d);
    rmdir(path);
}

/* 写一封最小 RFC822 邮件（索引/搜索的输入样本） */
static int write_sample_mail(const char *path) {
    FILE *f = fopen(path, "w");
    if (f == NULL) return -1;
    fputs("From: Test User <testuser@example.org>\n", f);
    fputs("To: Recipient <rcpt@example.org>\n", f);
    fputs("Subject: hello from notmuch consumer test\n", f);
    fputs("Date: Sat, 15 Aug 2026 10:00:00 +0800\n", f);
    fputs("Message-ID: <consumer-test-1@example.org>\n", f);
    fputs("\n", f);
    fputs("This is the body of the indexed message.\n", f);
    fclose(f);
    return 0;
}

int main(void) {
    /* 用可写临时目录真实创建数据库（/tmp 在 OHOS 只读 → 用 TMPDIR） */
    const char *base = getenv("TMPDIR");
    if (base == NULL || *base == '\0') {
        base = "/storage/Users/currentUser/tmp";
    }
    char tmpl[512];
    snprintf(tmpl, sizeof(tmpl), "%s/notmuch-test-XXXXXX", base);
    char *dir = mkdtemp(tmpl);
    if (dir == NULL) {
        perror("mkdtemp");
        return 1;
    }
    notmuch_database_t *db = NULL;
    notmuch_status_t st = notmuch_database_create(dir, &db);
    if (st != NOTMUCH_STATUS_SUCCESS) {
        fprintf(stderr, "notmuch_database_create failed: %d\n", (int)st);
        cleanup_dir(dir);
        return 1;
    }
    unsigned int ver = notmuch_database_get_version(db);
    if (ver == 0) {
        fprintf(stderr, "unexpected version 0\n");
        notmuch_database_destroy(db);
        cleanup_dir(dir);
        return 1;
    }
    /* 注意：notmuch_database_get_version 返回的是数据库格式版本（0.38.3 为 3），
     * 非库版本号——仅校验非 0 即可（数据库格式合法） */
    printf("notmuch database format version=%u OK\n", ver);

    /* 2) 邮件索引：写入样本邮件并 add_message（对应 T060-count 的索引语义） */
    char mail_path[1024];
    snprintf(mail_path, sizeof(mail_path), "%s/mail-1.eml", dir);
    if (write_sample_mail(mail_path) != 0) {
        fprintf(stderr, "failed to write sample mail\n");
        notmuch_database_destroy(db);
        cleanup_dir(dir);
        return 1;
    }
    notmuch_message_t *msg = NULL;
    st = notmuch_database_add_message(db, mail_path, &msg);
    if (st != NOTMUCH_STATUS_SUCCESS) {
        fprintf(stderr, "notmuch_database_add_message failed: %d\n", (int)st);
        notmuch_database_destroy(db);
        cleanup_dir(dir);
        return 1;
    }
    const char *mid = notmuch_message_get_message_id(msg);
    if (mid == NULL || strstr(mid, "consumer-test-1") == NULL) {
        fprintf(stderr, "indexed message-id mismatch: %s\n", mid ? mid : "(null)");
        notmuch_message_destroy(msg);
        notmuch_database_destroy(db);
        cleanup_dir(dir);
        return 1;
    }
    printf("indexed message OK (id=%s)\n", mid);
    notmuch_message_destroy(msg);

    /* 3) 搜索查询：from:testuser 应命中 1 封（对应 T080-search 的查询语义） */
    notmuch_query_t *q = notmuch_query_create(db, "from:testuser");
    if (q == NULL) {
        fprintf(stderr, "notmuch_query_create failed\n");
        notmuch_database_destroy(db);
        cleanup_dir(dir);
        return 1;
    }
    unsigned int count = 0;
    st = notmuch_query_count_messages(q, &count);
    if (st != NOTMUCH_STATUS_SUCCESS || count != 1) {
        fprintf(stderr, "count_messages(from:testuser) = %u (rc=%d), expected 1\n", count, (int)st);
        notmuch_query_destroy(q);
        notmuch_database_destroy(db);
        cleanup_dir(dir);
        return 1;
    }
    printf("count_messages(from:testuser) = %u OK\n", count);

    notmuch_messages_t *results = NULL;
    st = notmuch_query_search_messages(q, &results);
    if (st != NOTMUCH_STATUS_SUCCESS || results == NULL) {
        fprintf(stderr, "query_search_messages failed: %d\n", (int)st);
        notmuch_query_destroy(q);
        notmuch_database_destroy(db);
        cleanup_dir(dir);
        return 1;
    }
    int n = 0;
    for (; notmuch_messages_valid(results); notmuch_messages_move_to_next(results)) {
        /* notmuch_messages_get 返回借用引用（由迭代器内部管理），
         * 不能 notmuch_message_destroy（否则迭代器内部对象被释放 →
         * 后续 move_to_next 访问已释放内存 UAF / 最终 destroy 双重释放） */
        notmuch_message_t *m = notmuch_messages_get(results);
        if (m == NULL) break;
        const char *subject = notmuch_message_get_header(m, "subject");
        if (subject == NULL || strstr(subject, "hello from notmuch") == NULL) {
            fprintf(stderr, "search result subject mismatch: %s\n",
                    subject ? subject : "(null)");
            notmuch_messages_destroy(results);
            notmuch_query_destroy(q);
            notmuch_database_destroy(db);
            cleanup_dir(dir);
            return 1;
        }
        printf("search result[%d] subject='%s' OK\n", n, subject);
        n++;
    }
    if (n != 1) {
        fprintf(stderr, "search returned %d messages, expected 1\n", n);
        notmuch_messages_destroy(results);
        notmuch_query_destroy(q);
        notmuch_database_destroy(db);
        cleanup_dir(dir);
        return 1;
    }
    notmuch_messages_destroy(results);
    notmuch_query_destroy(q);
    notmuch_database_destroy(db);
    /* 清理临时目录（递归删除，无 shell 注入风险） */
    cleanup_dir(dir);
    printf("consumer test PASSED (create/version/index/search)\n");
    return 0;
}
