/* Vendored libpaper-compatible shim: static paper size table.
 * Values are PostScript points, identical to libpaper's paperspecs for the
 * listed names (ISO 216 A/B series + common US sizes).
 */
#include "paper.h"

#include <strings.h>

static const paper paper_table[] = {
	{ "a0", 2384, 3370 },
	{ "a1", 1684, 2384 },
	{ "a2", 1191, 1684 },
	{ "a3", 842, 1191 },
	{ "a4", 595, 842 },
	{ "a5", 420, 595 },
	{ "a6", 298, 420 },
	{ "a7", 210, 298 },
	{ "a8", 147, 210 },
	{ "a9", 105, 147 },
	{ "a10", 74, 105 },
	{ "b0", 2835, 4008 },
	{ "b1", 2004, 2835 },
	{ "b2", 1417, 2004 },
	{ "b3", 1001, 1417 },
	{ "b4", 709, 1001 },
	{ "b5", 499, 709 },
	{ "b6", 354, 499 },
	{ "letter", 612, 792 },
	{ "legal", 612, 1008 },
	{ "executive", 522, 756 },
	{ "tabloid", 792, 1224 },
	{ "ledger", 1224, 792 },
	{ "statement", 396, 612 },
	{ "folio", 612, 936 },
	{ "quarto", 610, 780 },
	{ "10x14", 720, 1008 },
	{ 0, 0, 0 }
};

const paper *paperinfo(const char *name)
{
	int i;

	if (!name)
		return 0;
	for (i = 0; paper_table[i].name; i++) {
		if (strcasecmp(paper_table[i].name, name) == 0)
			return &paper_table[i];
	}
	return 0;
}

int paperpswidth(const paper *p)
{
	return p ? p->pswidth : 0;
}

int paperpsheight(const paper *p)
{
	return p ? p->psheight : 0;
}
