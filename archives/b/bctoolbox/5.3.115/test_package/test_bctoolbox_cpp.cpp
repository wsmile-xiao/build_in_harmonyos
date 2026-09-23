/*
 * C++ API consumer test — bctbx_is_matching_regex + BctbxException.
 */
#include <bctoolbox/exception.hh>
#include <bctoolbox/regex.h>

#include <cstdio>
#include <exception>
#include <string>

static int g_failures = 0;

static void check(int cond, const char *name) {
	printf("[test] %s: %s\n", name, cond ? "PASS" : "FAIL");
	if (!cond)
		g_failures++;
}

int main() {
	/* C-facing regex helper implemented in the C++ part of the library */
	check(bctbx_is_matching_regex("bctoolbox-5.3.115", "^bctoolbox-[0-9.]+$") == TRUE,
	      "bctbx_is_matching_regex accept");
	check(bctbx_is_matching_regex("other", "^bctoolbox-[0-9.]+$") == FALSE,
	      "bctbx_is_matching_regex reject");

	/* C++ exception type exported by the library */
	bool caught = false;
	try {
		throw BctbxException("probe");
	} catch (const std::exception &e) {
		caught = std::string(e.what()).find("probe") != std::string::npos;
	}
	check(caught, "BctbxException throw and catch");

	printf("%s\n", g_failures == 0 ? "ALL C++ TESTS PASSED" : "C++ TESTS FAILED");
	return g_failures == 0 ? 0 : 1;
}
