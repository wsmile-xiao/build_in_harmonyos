/* libgda6 test_package: smoke-test the library API (R34).
 * gda_init() is the entry point of libgda-6.0; it initializes the
 * provider/client configuration machinery and registers the built-in
 * SQLite provider from lib/libgda-6.0/providers. We then check that the
 * SQLite provider is visible through gda_config_list_providers().
 */
#include <stdio.h>
#include <libgda/libgda.h>

int main(void)
{
	GdaDataModel *providers;
	gint nrows, i;
	int found_sqlite = 0;

	gda_init();

	providers = gda_config_list_providers();
	nrows = gda_data_model_get_n_rows(providers);
	for (i = 0; i < nrows; i++) {
		const GValue *v = gda_data_model_get_value_at(providers, 0, i, NULL);
		const gchar *id = v && G_VALUE_HOLDS_STRING(v) ? g_value_get_string(v) : NULL;
		printf("provider: %s\n", id ? id : "(null)");
		if (id && g_str_has_prefix(id, "SQLite"))
			found_sqlite = 1;
	}

	if (!found_sqlite) {
		fprintf(stderr, "FAIL: built-in SQLite provider not registered\n");
		return 1;
	}
	printf("test libgda6 6.0.0: OK\n");
	return 0;
}
