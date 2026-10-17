/* test_package OHOS-specific test for libcyaml 1.4.2
 *
 * HarmonyOS-specific coverage beyond the upstream unit tests:
 *  1. UTF-8 Chinese YAML round-trip (load -> save -> reload) — exercises
 *     libcyaml UTF-8 handling on the OHOS platform.
 *  2. cyaml_save_data to memory then cyaml_load_data back (full round trip).
 *
 * Real executable assertions, not a print-only shell (R34/PF3).
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <stdint.h>
#include <cyaml/cyaml.h>

#define DOC \
	"标题: 鸿蒙适配\n" \
	"版本: 1.4.2\n" \
	"完成: true\n"

struct config {
	const char *title;
	const char *version;
	bool done;
};

static const cyaml_schema_field_t config_fields[] = {
	CYAML_FIELD_STRING_PTR("标题", CYAML_FLAG_POINTER, struct config, title, 0, CYAML_UNLIMITED),
	CYAML_FIELD_STRING_PTR("版本", CYAML_FLAG_POINTER, struct config, version, 0, CYAML_UNLIMITED),
	CYAML_FIELD_BOOL("完成", CYAML_FLAG_DEFAULT, struct config, done),
	CYAML_FIELD_END
};

static const cyaml_schema_value_t config_schema = {
	CYAML_VALUE_MAPPING(CYAML_FLAG_POINTER, struct config, config_fields),
};

static const cyaml_config_t config = {
	.log_fn = cyaml_log,
	.mem_fn = cyaml_mem,
	.log_level = CYAML_LOG_WARNING,
};

int main(void)
{
	struct config *cfg = NULL;
	cyaml_err_t err;
	unsigned int failed = 0;

	/* 1) load UTF-8 Chinese YAML from memory */
	err = cyaml_load_data((const uint8_t *)DOC, strlen(DOC),
			&config, &config_schema, (cyaml_data_t **)&cfg, NULL);
	if (err != CYAML_OK || cfg == NULL) {
		fprintf(stderr, "load failed: %s\n", cyaml_strerror(err));
		return 1;
	}
	if (strcmp(cfg->title, "鸿蒙适配") != 0) { failed++; }
	if (strcmp(cfg->version, "1.4.2") != 0) { failed++; }
	if (cfg->done != true) { failed++; }

	/* 2) save back to memory, then reload (round trip) */
	size_t len = 0;
	char *out = NULL;
	err = cyaml_save_data(&out, &len, &config, &config_schema,
			(cyaml_data_t *)cfg, 0);
	if (err != CYAML_OK || out == NULL || len == 0) {
		fprintf(stderr, "save failed: %s\n", cyaml_strerror(err));
		return 1;
	}

	struct config *cfg2 = NULL;
	err = cyaml_load_data((const uint8_t *)out, len,
			&config, &config_schema, (cyaml_data_t **)&cfg2, NULL);
	if (err != CYAML_OK || cfg2 == NULL) {
		fprintf(stderr, "reload failed: %s\n", cyaml_strerror(err));
		return 1;
	}
	if (strcmp(cfg2->title, "鸿蒙适配") != 0) { failed++; }
	if (cfg2->done != true) { failed++; }

	cyaml_free(&config, &config_schema, (cyaml_data_t *)cfg2, 0);
	cyaml_free(&config, &config_schema, (cyaml_data_t *)cfg, 0);
	/* output buffer from cyaml_save_data is caller-owned */
	free(out);

	if (failed != 0) {
		fprintf(stderr, "%u checks failed\n", failed);
		return 1;
	}

	printf("test libcyaml 1.4.2 OHOS-specific: OK (utf8 round-trip)\n");
	return 0;
}