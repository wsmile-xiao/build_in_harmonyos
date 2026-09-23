#define PKGCONFIG_IS_STATIC

#include <libpkgconf/stdinc.h>
#include <libpkgconf/libpkgconf.h>

#include <stdio.h>
#include <string.h>

static int
fail(pkgconf_list_t *paths, const char *message)
{
	pkgconf_path_free(paths);
	fprintf(stderr, "FAIL: %s\n", message);
	return 1;
}

int
main(void)
{
	pkgconf_list_t paths = PKGCONF_LIST_INITIALIZER;

	if (LIBPKGCONF_VERSION != 30006)
		return fail(&paths, "LIBPKGCONF_VERSION is not 30006");
	if (strcmp(LIBPKGCONF_VERSION_STR, "3.0.6") != 0)
		return fail(&paths, "LIBPKGCONF_VERSION_STR is not 3.0.6");
	if (pkgconf_compare_version("3.0.6", LIBPKGCONF_VERSION_STR) != 0)
		return fail(&paths, "version comparison failed");

	const char *input = "/alpha" PKG_CONFIG_PATH_SEP_S "/beta";
	size_t count = pkgconf_path_split(input, &paths, false);
	if (count != 2)
		return fail(&paths, "pkgconf_path_split did not return two paths");
	if (paths.length != 2 || paths.head == NULL || paths.tail == NULL)
		return fail(&paths, "path list shape is invalid");

	pkgconf_path_t *first = paths.head->data;
	pkgconf_path_t *second = paths.head->next != NULL
		? paths.head->next->data
		: NULL;
	if (first == NULL || strcmp(first->path, "/alpha") != 0)
		return fail(&paths, "first split path is incorrect");
	if (second == NULL || strcmp(second->path, "/beta") != 0)
		return fail(&paths, "second split path is incorrect");

	pkgconf_path_free(&paths);
	if (paths.length != 0 || paths.head != NULL || paths.tail != NULL)
	{
		fprintf(stderr, "FAIL: pkgconf_path_free did not reset the list\n");
		return 1;
	}

	puts("LIBPKGCONF_VERSION=30006");
	puts("PATH_SPLIT_COUNT=2");
	puts("API_ASSERTIONS=12");
	return 0;
}
