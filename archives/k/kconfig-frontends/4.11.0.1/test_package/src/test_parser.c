#include <stdio.h>
#include <stdlib.h>

#include <kconfig/lkc.h>

int main(int argc, char **argv)
{
	const char *config_path;
	struct symbol *feature;

	if (argc != 2) {
		fprintf(stderr, "usage: %s <Kconfig>\n", argv[0]);
		return 2;
	}

	config_path = getenv("KCONFIG_CONFIG");
	if (!config_path || !*config_path) {
		fprintf(stderr, "KCONFIG_CONFIG must name the consumer output file\n");
		return 2;
	}

	conf_parse(argv[1]);
	if (conf_read(NULL) != 0) {
		fprintf(stderr, "conf_read() failed\n");
		return 3;
	}

	feature = sym_find("ENABLE_PARSER");
	if (!feature) {
		fprintf(stderr, "parser API did not expose ENABLE_PARSER\n");
		return 4;
	}
	sym_calc_value(feature);
	if (sym_get_tristate_value(feature) != yes) {
		fprintf(stderr, "parser API did not read ENABLE_PARSER=y\n");
		return 5;
	}
	if (!sym_set_tristate_value(feature, no)) {
		fprintf(stderr, "parser API could not change ENABLE_PARSER\n");
		return 6;
	}
	if (conf_write(config_path) != 0) {
		fprintf(stderr, "conf_write() failed\n");
		return 7;
	}

	return 0;
}
