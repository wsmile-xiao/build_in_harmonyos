/* Minimal POMP runtime-table definition for opari 1.1 instrumented programs.
 *
 * opari's generated .opari.inc defines the per-region descriptors (omp_rd_N),
 * but pomp_lib.h declares:
 *     extern int POMP_MAX_ID;
 *     extern struct ompregdescr* pomp_rd_table[];
 * which must be DEFINED in the executable. The instrumented code references the
 * descriptors directly via &omp_rd_N, and pomp_init() tolerates a NULL
 * pomp_rd_table, so a zero-initialised table is sufficient to make the runtime
 * link and execute correctly.
 */
#include "pomp_lib.h"

int POMP_MAX_ID = 1;
struct ompregdescr* pomp_rd_table[1];
