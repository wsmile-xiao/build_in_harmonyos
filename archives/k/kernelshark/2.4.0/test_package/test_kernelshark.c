/*
 * test_kernelshark.c — kernelshark/2.4.0 真实消费方探针
 *
 * 基于 upstream examples/configio.c 的 API 路径（会话创建 → 流分配 →
 * 哈希过滤器 → json-c 配置文档导出 → 落盘 → 重新读回校验），加硬断言。
 * 过滤器序列化改用公共 API kshark_export_filter_array /
 * kshark_import_filter_array（直接操作 hash 过滤器）：
 * kshark_export_all_filters 依赖 kshark_get_data_stream() 要求的
 * stream->interface，仅在打开真实 tep 数据文件后成立；裸
 * kshark_add_stream() 流在所有平台（含 Linux）都使其返回 NULL，
 * upstream 示例对该返回值未做检查。断言点：
 *   1. kshark_instance/kshark_add_stream 成功（核心上下文）
 *   2. kshark_hash_id_add 写入 pid 314/42 后集合语义（重复添加不增计数）
 *   3. kshark_filter_config_new + kshark_export_filter_array 走 json-c
 *      序列化（json_object 真实参与，libkshark-configio 闭包）
 *   4. conf.json 落盘 → kshark_hash_id_clear 清空 → kshark_open_config_file
 *      读回 → kshark_import_filter_array 反序列化 → pid 集合与
 *      "Hello Kernel" 消息逐项相等（真实 round-trip，非内存复读）
 * 任何一个断言失败即非零退出。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <kernelshark/libkshark.h>

#define CHECK(cond, msg)						\
	do {								\
		if (!(cond)) {						\
			fprintf(stderr, "FAIL: %s (line %d)\n", msg, __LINE__); \
			return 1;					\
		}							\
	} while (0)

int main(void)
{
	struct kshark_config_doc *conf, *filter, *hello;
	struct kshark_context *kshark_ctx = NULL;
	struct kshark_data_stream *stream;
	int sd, *ids = NULL;
	size_t i;
	int seen_314 = 0, seen_42 = 0;

	/* 1. 核心会话与流 */
	CHECK(kshark_instance(&kshark_ctx), "kshark_instance");
	sd = kshark_add_stream(kshark_ctx);
	CHECK(sd >= 0, "kshark_add_stream");
	stream = kshark_ctx->stream[sd];
	CHECK(stream != NULL, "stream pointer");

	/* 2. 哈希过滤器（libkshark-hash.c），集合语义 */
	kshark_hash_id_add(stream->show_task_filter, 314);
	kshark_hash_id_add(stream->show_task_filter, 42);
	CHECK(stream->show_task_filter->count == 2, "filter count");
	kshark_hash_id_add(stream->show_task_filter, 314);
	CHECK(stream->show_task_filter->count == 2, "hash set semantics");

	/* 3. json-c 配置文档导出（libkshark-configio.c）：
	 *    filter 文档必须带 "kshark.config.filter" type，
	 *    import 侧的 kshark_json_type_check 才认。 */
	conf = kshark_config_new("foo.bar.config", KS_CONFIG_JSON);
	CHECK(conf != NULL, "kshark_config_new");
	filter = kshark_filter_config_new(KS_CONFIG_JSON);
	CHECK(filter != NULL, "kshark_filter_config_new");
	CHECK(kshark_export_filter_array(stream->show_task_filter,
					  KS_SHOW_TASK_FILTER_NAME, filter),
	      "kshark_export_filter_array");
	CHECK(kshark_config_doc_add(conf, "Filters", filter), "doc add Filters");
	hello = kshark_string_config_alloc();
	hello->conf_doc = "Hello Kernel";
	CHECK(kshark_config_doc_add(conf, "Message", hello), "doc add Message");
	CHECK(kshark_save_config_file("conf.json", conf),
	      "kshark_save_config_file");

	/* 4. 清空后从文件读回（真实 round-trip） */
	kshark_hash_id_clear(stream->show_task_filter);
	CHECK(stream->show_task_filter->count == 0, "filter cleared");
	conf = kshark_open_config_file("conf.json", "foo.bar.config");
	CHECK(conf != NULL, "kshark_open_config_file");
	filter = kshark_config_alloc(KS_CONFIG_JSON);
	CHECK(filter != NULL, "kshark_config_alloc");
	CHECK(kshark_config_doc_get(conf, "Filters", filter),
	      "retrieve Filters doc");
	CHECK(kshark_import_filter_array(stream->show_task_filter,
					    KS_SHOW_TASK_FILTER_NAME, filter),
	      "kshark_import_filter_array");
	CHECK(stream->show_task_filter->count == 2, "round-trip count");
	ids = kshark_hash_ids(stream->show_task_filter);
	CHECK(ids != NULL, "kshark_hash_ids");
	for (i = 0; i < stream->show_task_filter->count; ++i) {
		if (ids[i] == 314)
			seen_314 = 1;
		if (ids[i] == 42)
			seen_42 = 1;
	}
	CHECK(seen_314 && seen_42, "pid round-trip 314/42");

	hello = kshark_string_config_alloc();
	CHECK(kshark_config_doc_get(conf, "Message", hello), "retrieve Message");
	CHECK(strcmp((char *) hello->conf_doc, "Hello Kernel") == 0,
	      "message round-trip");

	free(filter);
	free(hello);
	free(ids);
	kshark_free_config_doc(conf);
	kshark_close(kshark_ctx, sd);
	kshark_free(kshark_ctx);

	/* 测试产物自清理：conan create 的 test 阶段 cwd 是源码 test_package/
	 * 目录，不清理会在工作树留下 conf.json 运行时垃圾。 */
	remove("conf.json");

	printf("kernelshark probe OK: session+stream+hash-filters+json-c config round-trip\n");
	return 0;
}
