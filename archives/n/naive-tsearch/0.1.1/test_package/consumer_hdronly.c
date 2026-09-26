/* Consumer TU for the packaged header-only flavour:
 * NAIVE_TSEARCH_HDRONLY <search.h> -> tsearch_hdronly.h (static impl,
 * self-contained in this translation unit). */
#define NAIVE_TSEARCH_HDRONLY
#include <search.h>

#ifndef NAIVE_TSEARCH_HDRONLY_H_
#error "package header tsearch_hdronly.h was not used — fell back to system <search.h>"
#endif

#define CONSUMER_CHECKS run_hdronly_checks
#include "consumer_checks.inc"
