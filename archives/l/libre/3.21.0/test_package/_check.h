#ifndef QC2_TCHECK_H
#define QC2_TCHECK_H
#include <stdio.h>
#include <string.h>
#define DEBUG_MODULE "qc2test"
#define DEBUG_LEVEL 5
static int errors;
#define CHECK(c)                                                           \
	do {                                                             \
		if (!(c)) {                                              \
			printf("FAIL %s:%d %s\n",                      \
			       __FILE__, __LINE__, #c);                \
			++errors;                                        \
		}                                                        \
	} while (0)
#endif
