/* test_package consumer test for libcyaml 1.4.2
 *
 * Real consumer validation (R34/PF3): loads a YAML document through the
 * libcyaml public API (cyaml_load_data/cyaml_free) and checks fields actually
 * parsed from the document — not a print-only shell.
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <cyaml/cyaml.h>

#define DOC \
	"name: libcyaml\n" \
	"version: 1.4.2\n" \
	"count: 3\n"

struct config {
	const char *name;
	const char *version;
	uint32_t count;
};

static const cyaml_schema_value_t count_schema = {
	CYAML_VALUE_UINT(CYAML_FLAG_DEFAULT, uint32_t),
};

static const cyaml_schema_field_t config_fields[] = {
	CYAML_FIELD_STRING_PTR("name", CYAML_FLAG_POINTER, struct config, name, 0, CYAML_UNLIMITED),
	CYAML_FIELD_STRING_PTR("version", CYAML_FLAG_POINTER, struct config, version, 0, CYAML_UNLIMITED),
	CYAML_FIELD_UINT("count", CYAML_FLAG_DEFAULT, struct config, count),
	CYAML_FIELD_END
};

static const cyaml_schema_value_t config_schema = {
	CYAML_VALUE_MAPPING(CYAML_FLAG_POINTER, struct config, config_fields),
};

static const cyaml_config_t config = {
	.log_fn = cyaml_log,            /* Use the default logging function. */
	.mem_fn = cyaml_mem,            /* Use the default memory allocator. */
	.log_level = CYAML_LOG_WARNING, /* Logging errors and warnings only. */
};

int main(void)
{
	struct config *cfg = NULL;
	cyaml_err_t err;
	unsigned int failed = 0;

	err = cyaml_load_data((const uint8_t *)DOC, strlen(DOC),
			&config, &config_schema, (cyaml_data_t **)&cfg, NULL);
	if (err != CYAML_OK) {
		fprintf(stderr, "cyaml_load_data failed: %s\n", cyaml_strerror(err));
		return 1;
	}
	if (cfg == NULL) {
		fprintf(stderr, "cyaml_load_data returned NULL data\n");
		return 1;
	}

	if (strcmp(cfg->name, "libcyaml") != 0) { failed++; }
	if (strcmp(cfg->version, "1.4.2") != 0) { failed++; }
	if (cfg->count != 3) { failed++; }

	cyaml_free(&config, &config_schema, (cyaml_data_t *)cfg, 0);

	if (failed != 0) {
		fprintf(stderr, "parsed fields mismatch (%u checks failed)\n", failed);
		return 1;
	}

	printf("test libcyaml 1.4.2: OK\n");
	return 0;
}