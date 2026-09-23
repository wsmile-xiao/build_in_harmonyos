#include <modulemd-2.0/modulemd.h>
#include <modulemd-2.0/modulemd-module-stream-v2.h>
#include <stdio.h>
#include <string.h>

/*
 * libmodulemd 消费者测试（R34：实质调用被测包 API，禁止空壳）。
 *
 * 覆盖 ModulemdModuleStream（创建/读写属性/NSVC/拷贝相等）与
 * ModulemdModuleIndex（建索引/加流/查询/导出 YAML）两条核心路径，
 * 共 8 个显式检查：任一失败即打印 FAIL 并返回非 0。
 */
static int failures = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s\n", msg); \
        failures++; \
    } else { \
        printf("ok: %s\n", msg); \
    } \
} while (0)

int main(void) {
    GError *error = NULL;

    /* 1) 创建 V2 流 */
    ModulemdModuleStream *stream =
        modulemd_module_stream_new(2, "testmodule", "teststream");
    CHECK(stream != NULL, "modulemd_module_stream_new(2)");

    /* 2) version 属性读写 */
    modulemd_module_stream_set_version(stream, 42);
    CHECK(modulemd_module_stream_get_version(stream) == 42,
          "stream version set/get == 42");

    /* 3) context 属性读写（10 字符，满足 MMD_MAXCONTEXTLEN） */
    modulemd_module_stream_set_context(stream, "c0ffee1234");
    const char *ctx = modulemd_module_stream_get_context(stream);
    CHECK(ctx != NULL && strcmp(ctx, "c0ffee1234") == 0,
          "stream context set/get == c0ffee1234");

    /* 4) 模块名/流名 */
    CHECK(strcmp(modulemd_module_stream_get_module_name(stream), "testmodule") == 0,
          "stream module name == testmodule");
    CHECK(strcmp(modulemd_module_stream_get_stream_name(stream), "teststream") == 0,
          "stream stream name == teststream");

    /* 5) NSVC 字符串 */
    char *nsvc = modulemd_module_stream_get_nsvc_as_string(stream);
    CHECK(nsvc != NULL && strcmp(nsvc, "testmodule:teststream:42:c0ffee1234") == 0,
          "stream NSVC == testmodule:teststream:42:c0ffee1234");
    g_free(nsvc);

    /* 6b) 补齐 dump/validate 必填字段（上游 v2 规范：summary/description/
     * module license 缺失即 dump 报错 "Summary is missing"，见上游
     * module_stream_v2_test_xmd_issue_290 / quoting 用例均先设三者再
     * add+dump）。仅补数据，不删减任何断言。 */
    modulemd_module_stream_v2_set_summary(
        MODULEMD_MODULE_STREAM_V2(stream), "Test summary");
    modulemd_module_stream_v2_set_description(
        MODULEMD_MODULE_STREAM_V2(stream), "Test description");
    modulemd_module_stream_v2_add_module_license(
        MODULEMD_MODULE_STREAM_V2(stream), "MIT");

    /* 6) 拷贝与相等判定 */
    ModulemdModuleStream *copy =
        modulemd_module_stream_copy(stream, NULL, NULL);
    CHECK(copy != NULL && modulemd_module_stream_equals(stream, copy),
          "stream copy equals original");
    g_object_unref(copy);

    /* 7) 索引：建索引、加入流、按名查回 */
    ModulemdModuleIndex *index = modulemd_module_index_new();
    CHECK(index != NULL, "modulemd_module_index_new()");
    CHECK(modulemd_module_index_add_module_stream(index, stream, &error),
          "index add_module_stream");
    if (error != NULL) {
        fprintf(stderr, "FAIL: add_module_stream error: %s\n", error->message);
        g_clear_error(&error);
        failures++;
    }
    ModulemdModule *module = modulemd_module_index_get_module(index, "testmodule");
    CHECK(module != NULL, "index get_module(testmodule)");

    /* 8) 索引导出 YAML 包含该模块 */
    char *dump = modulemd_module_index_dump_to_string(index, &error);
    CHECK(dump != NULL && strstr(dump, "testmodule") != NULL,
          "index dump_to_string contains testmodule");
    if (error != NULL) {
        fprintf(stderr, "FAIL: dump error: %s\n", error->message);
        g_clear_error(&error);
        failures++;
    }
    g_free(dump);

    g_object_unref(stream);
    g_object_unref(index);

    if (failures == 0) {
        printf("libmodulemd 2.15.3 OK: 8 checks passed\n");
    }
    return failures == 0 ? 0 : 1;
}
