/* test_package/test_librdata.c — 消费者侧功能测试（鸿蒙特有测试）
 *
 * 只使用 librdata 的公开 API（<rdata.h>）：
 *   1) 用 writer 写出一个 4 列 3 行的 .RData（workspace 格式，含 REAL / STRING /
 *      TIMESTAMP / DATE 四种列型，含 NaN 与 NULL 文本）；
 *   2) 用 parser + 默认 unistd IO 把它读回来，逐项断言表名、列名、列型、
 *      行数与取值；
 *   3) 再写一个 .rds（单对象格式）并读回，断言取值。
 *
 * 失败用例数记入 exit code，并打印一行机器可解析的汇总：
 *   test_librdata: PASS checks=<n> failures=0
 *   test_librdata: FAIL checks=<n> failures=<m>
 *
 * 注意：临时文件写在当前工作目录（不写 /tmp —— 鸿蒙设备上 /tmp 只读）。
 */
#include <fcntl.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <unistd.h>

#include <rdata.h>

static int checks = 0;
static int failures = 0;

static void check(int condition, const char *what) {
    checks++;
    if (!condition) {
        failures++;
        printf("  [FAIL] %s\n", what);
    } else {
        printf("  [ok]   %s\n", what);
    }
}

/* ── .RData 往返 ─────────────────────────────────────────────── */

#define RDATA_FILE "librdata_test_package.RData"

typedef struct {
    const char *table_name;
    int row_count;
    time_t timestamp;
    struct tm date;
    int table_seen;
    int column_count;
    int real_seen;
    int text_seen;
    double real_values[3];
    char text_values[3][32];
    int text_null[3];
    int bad;
} rdata_probe_t;

static void on_error(const char *message, void *ctx) {
    (void) ctx;
    printf("  [library error] %s\n", message);
}

static int on_table(const char *name, void *ctx) {
    rdata_probe_t *probe = (rdata_probe_t *) ctx;
    probe->table_seen++;
    return !(name != NULL && strcmp(name, probe->table_name) == 0);
}

static int on_column(const char *name, rdata_type_t type, void *data, long count, void *ctx) {
    rdata_probe_t *probe = (rdata_probe_t *) ctx;
    probe->column_count++;

    /* .RData/.rds 里列名有时在数据之后才出现，因此列名可能为 NULL；
     * 取值断言按 type 判（与上游 test_rdata.c 同口径），名字只在非 NULL 时校验。 */
    if (name != NULL) {
        if (strcmp(name, "column1") == 0 && type != RDATA_TYPE_REAL) {
            probe->bad = 1;
            return 1;
        }
        if (strcmp(name, "column2") == 0 && type != RDATA_TYPE_STRING) {
            probe->bad = 1;
            return 1;
        }
        if (strcmp(name, "column3") == 0 && type != RDATA_TYPE_TIMESTAMP) {
            probe->bad = 1;
            return 1;
        }
        if (strcmp(name, "column4") == 0 && type != RDATA_TYPE_DATE) {
            probe->bad = 1;
            return 1;
        }
    }

    if (data == NULL) {
        return 0;
    }
    if (count != probe->row_count) {
        probe->bad = 1;
        return 1;
    }

    if (type == RDATA_TYPE_REAL) {
        double *values = (double *) data;
        probe->real_seen++;
        probe->real_values[0] = values[0];
        probe->real_values[1] = values[1];
        probe->real_values[2] = values[2];
    } else if (type == RDATA_TYPE_TIMESTAMP) {
        double *values = (double *) data;
        int i;
        for (i = 0; i < 3; i++) {
            if ((time_t) values[i] != probe->timestamp) {
                probe->bad = 1;
                return 1;
            }
        }
    } else if (type == RDATA_TYPE_DATE) {
        double *values = (double *) data;
        int i;
        for (i = 0; i < 3; i++) {
            if (values[i] * 86400 != timegm(&probe->date)) {
                probe->bad = 1;
                return 1;
            }
        }
    }

    return 0;
}

static int on_text_value(const char *value, int index, void *ctx) {
    rdata_probe_t *probe = (rdata_probe_t *) ctx;
    if (index < 0 || index > 2) {
        return 0;
    }
    probe->text_seen++;
    if (value == NULL) {
        probe->text_null[index] = 1;
    } else {
        snprintf(probe->text_values[index], sizeof(probe->text_values[index]), "%s", value);
    }
    return 0;
}

static ssize_t write_to_fd(const void *bytes, size_t len, void *ctx) {
    int fd = *(int *) ctx;
    return write(fd, bytes, len);
}

static int write_workspace_file(time_t timestamp, struct tm *date) {
    int row_count = 3;
    int fd = open(RDATA_FILE, O_CREAT | O_TRUNC | O_WRONLY, 0644);
    if (fd < 0) {
        printf("  [FAIL] cannot create %s\n", RDATA_FILE);
        failures++;
        return -1;
    }

    rdata_writer_t *writer = rdata_writer_init(&write_to_fd, RDATA_WORKSPACE);
    rdata_column_t *col1 = rdata_add_column(writer, "column1", RDATA_TYPE_REAL);
    rdata_column_t *col2 = rdata_add_column(writer, "column2", RDATA_TYPE_STRING);
    rdata_column_t *col3 = rdata_add_column(writer, "column3", RDATA_TYPE_TIMESTAMP);
    rdata_column_t *col4 = rdata_add_column(writer, "column4", RDATA_TYPE_DATE);
    check(col1 != NULL && col2 != NULL && col3 != NULL && col4 != NULL,
          "rdata_add_column returned 4 handles");

    rdata_begin_file(writer, &fd);
    rdata_begin_table(writer, "table1");

    rdata_begin_column(writer, col1, row_count);
    rdata_append_real_value(writer, 0.0);
    rdata_append_real_value(writer, 100.0);
    rdata_append_real_value(writer, NAN);
    rdata_end_column(writer, col1);

    rdata_begin_column(writer, col2, row_count);
    rdata_append_string_value(writer, "hello");
    rdata_append_string_value(writer, "goodbye");
    rdata_append_string_value(writer, NULL);
    rdata_end_column(writer, col2);

    rdata_begin_column(writer, col3, row_count);
    rdata_append_timestamp_value(writer, timestamp);
    rdata_append_timestamp_value(writer, timestamp);
    rdata_append_timestamp_value(writer, timestamp);
    rdata_end_column(writer, col3);

    rdata_begin_column(writer, col4, row_count);
    rdata_append_date_value(writer, date);
    rdata_append_date_value(writer, date);
    rdata_append_date_value(writer, date);
    rdata_end_column(writer, col4);

    rdata_end_table(writer, row_count, "test data set");
    rdata_end_file(writer);
    close(fd);
    return 0;
}

static void test_workspace_roundtrip(void) {
    struct timeval now;
    rdata_probe_t probe;
    rdata_parser_t *parser;
    rdata_error_t err;

    printf("== .RData (workspace) round trip ==\n");
    gettimeofday(&now, NULL);
    memset(&probe, 0, sizeof(probe));
    probe.table_name = "table1";
    probe.row_count = 3;
    probe.timestamp = now.tv_sec;
    probe.date.tm_year = 95;
    probe.date.tm_mon = 7;
    probe.date.tm_mday = 15;

    if (write_workspace_file(probe.timestamp, &probe.date) != 0) {
        return;
    }
    check(access(RDATA_FILE, F_OK) == 0, "writer produced a file");

    parser = rdata_parser_init();
    rdata_set_error_handler(parser, &on_error);
    rdata_set_table_handler(parser, &on_table);
    rdata_set_column_handler(parser, &on_column);
    rdata_set_text_value_handler(parser, &on_text_value);

    err = rdata_parse(parser, RDATA_FILE, &probe);
    check(err == RDATA_OK, "rdata_parse returned RDATA_OK");
    check(probe.table_seen == 1, "table handler called exactly once");
    check(probe.column_count == 4, "column handler called for 4 columns");
    check(probe.bad == 0, "no column-level mismatch reported");
    check(probe.real_seen == 1, "REAL column delivered inline data");
    check(probe.real_values[0] == 0.0, "real value[0] == 0.0");
    check(probe.real_values[1] == 100.0, "real value[1] == 100.0");
    check(isnan(probe.real_values[2]), "real value[2] is NaN");
    check(probe.text_seen == 3, "text handler called for 3 rows");
    check(strcmp(probe.text_values[0], "hello") == 0, "text value[0] == \"hello\"");
    check(strcmp(probe.text_values[1], "goodbye") == 0, "text value[1] == \"goodbye\"");
    check(probe.text_null[2] == 1, "text value[2] is NULL");

    rdata_parser_free(parser);
    unlink(RDATA_FILE);
}

/* ── .rds 往返 ───────────────────────────────────────────────── */

#define RDS_FILE "librdata_test_package.rds"

static void test_rds_roundtrip(void) {
    int row_count = 3;
    int fd;
    rdata_writer_t *writer;
    rdata_column_t *col;
    rdata_parser_t *parser;
    rdata_probe_t probe;
    rdata_error_t err;

    printf("== .rds (single object) round trip ==\n");
    fd = open(RDS_FILE, O_CREAT | O_TRUNC | O_WRONLY, 0644);
    check(fd >= 0, "created the .rds file");
    if (fd < 0) {
        return;
    }

    writer = rdata_writer_init(&write_to_fd, RDATA_SINGLE_OBJECT);
    col = rdata_add_column(writer, "column1", RDATA_TYPE_REAL);
    check(col != NULL, "rdata_add_column returned a handle");

    rdata_begin_file(writer, &fd);
    rdata_begin_column(writer, col, row_count);
    rdata_append_real_value(writer, 42.0);
    rdata_append_real_value(writer, -7.0);
    rdata_append_real_value(writer, NAN);
    rdata_end_column(writer, col);
    rdata_end_file(writer);
    close(fd);

    memset(&probe, 0, sizeof(probe));
    probe.table_name = "";
    probe.row_count = row_count;
    parser = rdata_parser_init();
    rdata_set_error_handler(parser, &on_error);
    rdata_set_column_handler(parser, &on_column);
    err = rdata_parse(parser, RDS_FILE, &probe);

    check(err == RDATA_OK, "rdata_parse(.rds) returned RDATA_OK");
    check(probe.column_count == 1, "column handler called for 1 column");
    check(probe.real_values[0] == 42.0, "rds value[0] == 42.0");
    check(probe.real_values[1] == -7.0, "rds value[1] == -7.0");
    check(isnan(probe.real_values[2]), "rds value[2] is NaN");

    rdata_parser_free(parser);
    unlink(RDS_FILE);
}

int main(void) {
    const char *message;
    rdata_parser_t *parser;
    rdata_error_t err;

    test_workspace_roundtrip();
    test_rds_roundtrip();

    /* 交付物指纹：错误串是产物自报内容，可用于确认链接到的确实是本包 */
    message = rdata_error_message(RDATA_ERROR_PARSE);
    check(message != NULL && strcmp(message, "Invalid file, or file has unsupported features") == 0,
          "rdata_error_message(RDATA_ERROR_PARSE) matches the upstream string");

    /* 负向路径：不存在的文件必须报 RDATA_ERROR_OPEN（=1） */
    parser = rdata_parser_init();
    err = rdata_parse(parser, "librdata_no_such_file.RData", NULL);
    check(err == RDATA_ERROR_OPEN, "parsing a missing file returns RDATA_ERROR_OPEN");
    rdata_parser_free(parser);

    if (failures == 0) {
        printf("test_librdata: PASS checks=%d failures=0\n", checks);
        return 0;
    }
    printf("test_librdata: FAIL checks=%d failures=%d\n", checks, failures);
    return 1;
}
