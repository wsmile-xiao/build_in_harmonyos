/* test_package consumer test — json 1.0.1 (header-only C99 JSON/SJSON parser)
 *
 * 消费者视角验证（R34：必须真实调用被测包 API，禁止空壳）：
 * 仅通过 json.h 公开头文件与公开 API（json_parse / sjson_parse /
 * json_token_t 结构字段）解析 JSON/SJSON，并断言可观察结果。
 */
#include <stdio.h>
#include <string.h>
#include <stddef.h>
#include <stdbool.h>
#include "json.h"

#define CHECK(cond, msg)                                                        \
	do {                                                                        \
		if (!(cond)) {                                                          \
			printf("FAIL: %s\n", msg);                                          \
			return 1;                                                           \
		}                                                                       \
	} while (0)

int main(void) {
	struct json_token_t tokens[32];
	memset(tokens, 0, sizeof(tokens));

	/* 1) 标准 JSON 解析（公开 API: json_parse） */
	const char* js = "{\"name\":\"json\",\"version\":1}";
	json_size_t num_tokens = json_parse(js, strlen(js), tokens,
	                                    sizeof(tokens) / sizeof(tokens[0]));
	CHECK(num_tokens > 0, "json_parse 应返回 token 数");
	CHECK(tokens[0].type == JSON_OBJECT, "根 token 应为 JSON_OBJECT");
	CHECK(tokens[1].type == JSON_STRING, "第 2 个 token 应为 JSON_STRING");

	/* 2) SJSON 解析（公开 API: sjson_parse，key 用 = 号） */
	const char* sjs = "name = json\nversion = 1";
	json_size_t sjson_tokens = sjson_parse(sjs, strlen(sjs), tokens,
	                                       sizeof(tokens) / sizeof(tokens[0]));
	CHECK(sjson_tokens > 0, "sjson_parse 应返回 token 数");
	CHECK(tokens[0].type == JSON_OBJECT, "SJSON 根 token 应为 JSON_OBJECT");

	/* 3) 可观察结果输出 */
	printf("json consumer test: parsed %d JSON tokens, %d SJSON tokens\n",
	       (int)num_tokens, (int)sjson_tokens);
	printf("test json 1.0.1: OK\n");
	return 0;
}
