#include <stdio.h>
#include <string.h>
#include <pipewire/pipewire.h>

int main(void) {
	const char *version;

	pw_init(NULL, NULL);
	version = pw_get_library_version();
	if (version == NULL || strcmp(version, "1.4.9") != 0) {
		fprintf(stderr, "unexpected library version: %s\n", version ? version : "(null)");
		return 2;
	}
	printf("pipewire library version %s: OK\n", version);
	pw_deinit();
	return 0;
}
