/* Consumer TU for the packaged static-library flavour:
 * default <search.h> -> tsearch.h -> links libnaive-tsearch.a */
#include <search.h>

#ifndef NAIVE_TSEARCH_SEARCH_H_
#error "package header search.h was not used — fell back to system <search.h>"
#endif

#define CONSUMER_CHECKS run_static_checks
#include "consumer_checks.inc"
