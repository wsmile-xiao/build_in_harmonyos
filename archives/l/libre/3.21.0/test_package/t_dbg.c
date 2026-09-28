#include <re.h>
/* re_dbg.h requires the module/level macros to be defined before it is
   included, otherwise it emits a #warning (upstream test files do the same). */
#define DEBUG_MODULE "t_dbg"
#define DEBUG_LEVEL 5
#include <re_dbg.h>
#include "_check.h"

static char cap[256];
static size_t capcalls;
static int caplevel = -1;

static void handler(int level, const char *p, size_t len, void *arg)
{
	(void)arg;
	caplevel = level;
	if (len >= sizeof(cap))
		len = sizeof(cap) - 1;
	memcpy(cap, p, len);
	cap[len] = '\0';
	++capcalls;
}

int main(void)
{

	CHECK(libre_init() == 0);
	const char *w, *i;

	dbg_init(DBG_INFO, DBG_NONE);
	dbg_handler_set(handler, NULL);

	dbg_printf(DBG_WARNING, "hello %s", "dbg");
	CHECK(capcalls == 1);
	CHECK(strcmp(cap, "hello dbg") == 0);
	CHECK(caplevel == DBG_WARNING);

	dbg_printf(DBG_DEBUG, "below threshold");
	CHECK(capcalls == 1);

	w = dbg_level_str(DBG_WARNING);
	i = dbg_level_str(DBG_INFO);
	CHECK(w != NULL && i != NULL);
	CHECK(strcmp(w, i) != 0);

	dbg_handler_set(NULL, NULL);
	dbg_close();

	libre_close();

	return errors ? 1 : 0;
}
