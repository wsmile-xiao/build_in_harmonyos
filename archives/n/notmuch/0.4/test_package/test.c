/* test.c — notmuch 0.4 consumer smoke test
 *
 * 用 C API 实质调用 libnotmuch（对应上游测试功能语义）：
 *   1) 数据库创建（notmuch_database_create）+ 版本读取
 *   2) 邮件索引（notmuch_database_add_message）
 *   3) 搜索查询（notmuch_query_create / count_messages / search_messages）
 */
#include <notmuch.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include <dirent.h>

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

static int write_sample_mail(const char *path) {
    FILE *f = fopen(path, "w");
    if (f == NULL) return -1;
    fputs("From: Test User <testuser@example.org>\n", f);
    fputs("To: Recipient <rcpt@example.org>\n", f);
    fputs("Subject: hello from notmuch 0.4 consumer test\n", f);
    fputs("Date: Sat, 15 Aug 2026 10:00:00 +0800\n", f);
    fputs("Message-ID: <consumer-test-1@example.org>\n", f);
    fputs("\n", f);
    fputs("This is the body of the indexed message.\n", f);
    fclose(f);
    return 0;
}

int main(void) {
    const char *base = getenv("TMPDIR");
    if (base == NULL || *base == '\0') {
        base = "/storage/Users/currentUser/tmp";
    }
    char tmpl[512];
    snprintf(tmpl, sizeof(tmpl), "%s/notmuch04-test-XXXXXX", base);
    char *dir = mkdtemp(tmpl);
    if (dir == NULL) { perror("mkdtemp"); return 1; }

    notmuch_database_t *db = notmuch_database_create(dir);
    if (db == NULL) {
        fprintf(stderr, "notmuch_database_create failed\n");
        cleanup_dir(dir);
        return 1;
    }
    unsigned int ver = notmuch_database_get_version(db);
    if (ver == 0) {
        fprintf(stderr, "unexpected db version 0\n");
        notmuch_database_close(db);
        cleanup_dir(dir);
        return 1;
    }
    printf("notmuch database format version=%u OK\n", ver);

    char mail_path[1024];
    snprintf(mail_path, sizeof(mail_path), "%s/mail-1.eml", dir);
    if (write_sample_mail(mail_path) != 0) {
        fprintf(stderr, "failed to write sample mail\n");
        notmuch_database_close(db);
        cleanup_dir(dir);
        return 1;
    }
    notmuch_message_t *msg = NULL;
    notmuch_status_t st = notmuch_database_add_message(db, mail_path, &msg);
    if (st != NOTMUCH_STATUS_SUCCESS || msg == NULL) {
        fprintf(stderr, "notmuch_database_add_message failed: %d\n", (int)st);
        notmuch_database_close(db);
        cleanup_dir(dir);
        return 1;
    }
    const char *mid = notmuch_message_get_message_id(msg);
    if (mid == NULL || strstr(mid, "consumer-test-1") == NULL) {
        fprintf(stderr, "indexed message-id mismatch: %s\n", mid ? mid : "()");
        notmuch_message_destroy(msg);
        notmuch_database_close(db);
        cleanup_dir(dir);
        return 1;
    }
    printf("indexed message OK (id=%s)\n", mid);
    notmuch_message_destroy(msg);

    notmuch_query_t *q = notmuch_query_create(db, "from:testuser");
    if (q == NULL) {
        fprintf(stderr, "notmuch_query_create failed\n");
        notmuch_database_close(db);
        cleanup_dir(dir);
        return 1;
    }
    unsigned int count = notmuch_query_count_messages(q);
    if (count != 1) {
        fprintf(stderr, "count_messages(from:testuser) = %u, expected 1\n", count);
        notmuch_query_destroy(q);
        notmuch_database_close(db);
        cleanup_dir(dir);
        return 1;
    }
    printf("count_messages(from:testuser) = %u OK\n", count);

    notmuch_messages_t *results = notmuch_query_search_messages(q);
    if (results == NULL) {
        fprintf(stderr, "query_search_messages failed\n");
        notmuch_query_destroy(q);
        notmuch_database_close(db);
        cleanup_dir(dir);
        return 1;
    }
    int n = 0;
    for (; notmuch_messages_valid(results); notmuch_messages_move_to_next(results)) {
        notmuch_message_t *m = notmuch_messages_get(results);
        if (m == NULL) break;
        const char *subject = notmuch_message_get_header(m, "subject");
        if (subject == NULL || strstr(subject, "hello from notmuch 0.4") == NULL) {
            fprintf(stderr, "search result subject mismatch: %s\n",
                    subject ? subject : "()");
            notmuch_messages_destroy(results);
            notmuch_query_destroy(q);
            notmuch_database_close(db);
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
        notmuch_database_close(db);
        cleanup_dir(dir);
        return 1;
    }
    notmuch_messages_destroy(results);
    notmuch_query_destroy(q);
    notmuch_database_close(db);
    cleanup_dir(dir);
    printf("consumer test PASSED (create/version/index/search)\n");
    return 0;
}
