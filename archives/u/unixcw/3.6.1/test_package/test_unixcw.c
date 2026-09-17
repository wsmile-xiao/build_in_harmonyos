/*
 * test_unixcw.c — consumer test for the unixcw (libcw) package.
 *
 * Exercises the public libcw API without any audio hardware:
 *   - library version query
 *   - generator lifecycle (new / delete)
 *   - parameter control (frequency)
 *   - Morse sending (character / string)
 * The CW_AUDIO_NULL backend performs timing only and never touches
 * ALSA / PulseAudio / OSS / console devices.
 */

#include <libcw.h>

#include <stdio.h>

#define CHECK(cond, label)                                                   \
	do {                                                                   \
		if (!(cond)) {                                                     \
			fprintf(stderr, "FAIL: %s\n", (label));                        \
			return 1;                                                      \
		}                                                                  \
		printf("ok: %s\n", (label));                                       \
	} while (0)

int main(void)
{
	int version = cw_version();
	printf("libcw version: %d\n", version);
	CHECK(version > 0, "cw_version() returns a positive version");

	CHECK(cw_generator_new(CW_AUDIO_NULL, NULL) == CW_SUCCESS,
	      "cw_generator_new(NULL audio backend)");

	CHECK(cw_set_frequency(600) == CW_SUCCESS, "cw_set_frequency(600)");
	CHECK(cw_get_frequency() == 600, "cw_get_frequency() == 600");

	CHECK(cw_send_character('A') == CW_SUCCESS, "cw_send_character('A')");
	CHECK(cw_send_string("SOS") == CW_SUCCESS, "cw_send_string(\"SOS\")");

	cw_generator_delete();
	CHECK(1, "cw_generator_delete()");

	printf("test_unixcw: all API checks passed\n");
	return 0;
}
