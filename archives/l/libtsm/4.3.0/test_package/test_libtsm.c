/*
 * test_package consumer for libtsm 4.3.0 — real use of the installed
 * shared library (libtsm.so.4, SONAME libtsm.so.4).
 *
 * The upstream test suite (test/meson.build, see MANIFEST.yml) compiles the
 * library sources directly into each test binary (meson declare_dependency
 * with `sources:`), so it never loads the shipped .so. This consumer program
 * is linked against the installed library and exercises the public API of the
 * delivered artifact: screen buffer, draw callback, VTE escape-sequence state
 * machine, SGR attributes (incl. the fork's 24-bit colour and named colour
 * palettes), wide-character handling, scrollback, selection copy and keyboard
 * encoding.
 *
 * SPDX-License-Identifier: MIT
 */
#include <libtsm.h>

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int checks_total;
static int checks_failed;

#define CHECK(cond, ...)                                                       \
	do {                                                                   \
		++checks_total;                                                \
		if (!(cond)) {                                                 \
			++checks_failed;                                       \
			printf("FAIL %s:%d: ", __FILE__, __LINE__);            \
			printf(__VA_ARGS__);                                   \
			printf("\n");                                          \
		}                                                              \
	} while (0)

/* keysyms (values are the X11 keysyms, same as xkbcommon-keysyms.h) */
#define KEY_UP 0xff52u
#define KEY_A 0x0061u
#define KEY_NONE 0x0000u /* KEY_NONE */

/* feed a literal escape/byte sequence through the state machine */
#define FEED(vte, s) tsm_vte_input((vte), (s), strlen(s))

/* ------------------------------------------------------------------ */
/* draw callback grid                                                  */
/* ------------------------------------------------------------------ */

#define GRID_MAX_X 80
#define GRID_MAX_Y 24

struct grid {
	uint32_t ch[GRID_MAX_Y][GRID_MAX_X];
	unsigned int width[GRID_MAX_Y][GRID_MAX_X];
	struct tsm_screen_attr attr[GRID_MAX_Y][GRID_MAX_X];
	unsigned int seen;
};

static int draw_cb(struct tsm_screen *con, uint64_t id, const uint32_t *ch,
		   size_t len, unsigned int width, unsigned int posx,
		   unsigned int posy, const struct tsm_screen_attr *attr,
		   tsm_age_t age, void *data)
{
	struct grid *g = data;

	(void)con;
	(void)id;
	(void)age;
	++g->seen;
	if (posx < GRID_MAX_X && posy < GRID_MAX_Y) {
		g->ch[posy][posx] = (len > 0) ? ch[0] : 0;
		g->width[posy][posx] = width;
		g->attr[posy][posx] = *attr;
	}
	return 0;
}

static void grid_capture(struct tsm_screen *con, struct grid *g)
{
	memset(g, 0, sizeof(*g));
	tsm_screen_draw(con, draw_cb, g);
}

/* copy row `y` into `out` as ASCII (non-ASCII cells become '?') */
static void grid_row(const struct grid *g, unsigned int y, char *out,
		     size_t out_len)
{
	unsigned int x;

	for (x = 0; x < GRID_MAX_X && x + 1 < out_len; ++x) {
		uint32_t c = g->ch[y][x];

		out[x] = (c >= 0x20 && c < 0x7f) ? (char)c : ' ';
	}
	out[x] = '\0';
}

/* true when row `y` starts with `text` and every following cell is blank */
static int grid_row_is(const struct grid *g, unsigned int y, const char *text)
{
	char row[GRID_MAX_X + 1];
	size_t i, n = strlen(text);

	grid_row(g, y, row, sizeof(row));
	if (strncmp(row, text, n) != 0)
		return 0;
	for (i = n; i < GRID_MAX_X; ++i) {
		if (g->ch[y][i] != 0 && g->ch[y][i] != ' ')
			return 0;
	}
	return 1;
}

/* ------------------------------------------------------------------ */
/* VTE output writer (keyboard / mouse replies)                        */
/* ------------------------------------------------------------------ */

struct writer {
	char buf[256];
	size_t len;
};

static void vte_write_cb(struct tsm_vte *vte, const char *u8, size_t len,
			 void *data)
{
	struct writer *w = data;

	(void)vte;
	if (w->len + len >= sizeof(w->buf))
		return;
	memcpy(w->buf + w->len, u8, len);
	w->len += len;
	w->buf[w->len] = '\0';
}

static void writer_reset(struct writer *w)
{
	memset(w, 0, sizeof(*w));
}

/* ------------------------------------------------------------------ */

static void test_screen_and_vte(void)
{
	static struct grid g;
	static struct writer w;
	struct tsm_screen *con = NULL;
	struct tsm_vte *vte = NULL;
	struct tsm_screen_attr def;
	char row[GRID_MAX_X + 1];
	char *sel = NULL;
	int ret;

	/* --- screen construction and geometry --- */
	ret = tsm_screen_new(&con, NULL, NULL);
	CHECK(ret == 0, "tsm_screen_new ret=%d", ret);
	CHECK(con != NULL, "tsm_screen_new returned NULL screen");
	if (!con)
		return;
	CHECK(tsm_screen_get_width(con) == 80, "default width=%u",
	      tsm_screen_get_width(con));
	CHECK(tsm_screen_get_height(con) == 24, "default height=%u",
	      tsm_screen_get_height(con));
	CHECK(tsm_screen_resize(con, 40, 10) == 0, "tsm_screen_resize failed");
	CHECK(tsm_screen_get_width(con) == 40 && tsm_screen_get_height(con) == 10,
	      "resize not applied: %ux%u", tsm_screen_get_width(con),
	      tsm_screen_get_height(con));
	CHECK(tsm_screen_resize(con, 80, 24) == 0, "resize back failed");

	/* --- VTE state machine on top of the screen --- */
	writer_reset(&w);
	ret = tsm_vte_new(&vte, con, vte_write_cb, &w, NULL, NULL);
	CHECK(ret == 0 && vte != NULL, "tsm_vte_new ret=%d", ret);
	if (!vte)
		return;

	tsm_vte_get_def_attr(vte, &def);
	CHECK(def.fccode == TSM_COLOR_FOREGROUND, "default fg code=%d",
	      def.fccode);
	CHECK(def.bccode == TSM_COLOR_BACKGROUND, "default bg code=%d",
	      def.bccode);

	/* plain text through the escape-sequence parser */
	FEED(vte, "Hello");
	grid_capture(con, &g);
	grid_row(&g, 0, row, sizeof(row));
	CHECK(g.seen > 0, "draw callback never invoked (empty grid)");
	CHECK(grid_row_is(&g, 0, "Hello"), "row0=[%s]", row);
	CHECK(tsm_screen_get_cursor_x(con) == 5, "cursor x=%u",
	      tsm_screen_get_cursor_x(con));
	CHECK(tsm_screen_get_cursor_y(con) == 0, "cursor y=%u",
	      tsm_screen_get_cursor_y(con));

	/* SGR bold + red foreground (16 colour code path) */
	FEED(vte, "\033[1;31mR\033[0m");
	grid_capture(con, &g);
	CHECK(g.ch[0][5] == 'R', "SGR cell char=%u", g.ch[0][5]);
	CHECK(g.attr[0][5].bold == 1, "SGR bold=%u", g.attr[0][5].bold);
	CHECK(g.attr[0][5].fccode == TSM_COLOR_RED, "SGR fg code=%d",
	      g.attr[0][5].fccode);
	CHECK(g.attr[0][5].fr == 255 && g.attr[0][5].fg == 0 &&
	      g.attr[0][5].fb == 0, "SGR fg rgb=%u,%u,%u", g.attr[0][5].fr,
	      g.attr[0][5].fg, g.attr[0][5].fb);
	CHECK(g.attr[0][0].bold == 0, "SGR leaked to earlier cell");

	/* underline / italic / inverse (fork features) */
	FEED(vte, "\033[4;3;7mX\033[0m");
	grid_capture(con, &g);
	CHECK(g.attr[0][6].underline == 1, "underline=%u",
	      g.attr[0][6].underline);
	CHECK(g.attr[0][6].italic == 1, "italic=%u", g.attr[0][6].italic);
	CHECK(g.attr[0][6].inverse == 1, "inverse=%u", g.attr[0][6].inverse);

	/* 24-bit true colour (fork feature): fccode < 0 marks direct RGB */
	FEED(vte, "\033[38;2;1;2;3mT\033[0m");
	grid_capture(con, &g);
	CHECK(g.attr[0][7].fccode < 0, "truecolor fccode=%d",
	      g.attr[0][7].fccode);
	CHECK(g.attr[0][7].fr == 1 && g.attr[0][7].fg == 2 &&
	      g.attr[0][7].fb == 3, "truecolor rgb=%u,%u,%u", g.attr[0][7].fr,
	      g.attr[0][7].fg, g.attr[0][7].fb);

	/* named colour palettes are a 4.x fork feature */
	CHECK(tsm_vte_set_palette(vte, "solarized") == 0,
	      "tsm_vte_set_palette(solarized) failed");
	CHECK(tsm_vte_set_palette(vte, "base16-dark") == 0,
	      "tsm_vte_set_palette(base16-dark) failed");
	CHECK(tsm_vte_set_palette(vte, "no-such-palette") == 0,
	      "unknown palette must fall back to the legacy palette");
	CHECK(tsm_vte_set_palette(vte, NULL) == 0,
	      "tsm_vte_set_palette(NULL) failed");

	/* cursor addressing + erase display */
	FEED(vte, "\033[2J\033[5;10H");
	grid_capture(con, &g);
	grid_row(&g, 0, row, sizeof(row));
	CHECK(row[0] == ' ', "row0 after ED not empty: [%c]", row[0]);
	CHECK(g.ch[4][9] == 0, "cell(9,4) not empty after ED");
	CHECK(tsm_screen_get_cursor_x(con) == 9 &&
	      tsm_screen_get_cursor_y(con) == 4, "CUP cursor=%u,%u",
	      tsm_screen_get_cursor_x(con), tsm_screen_get_cursor_y(con));

	/* wide (double cell) character: U+4E2D CJK */
	FEED(vte, "\033[2J\033[H\xe4\xb8\xad");
	grid_capture(con, &g);
	CHECK(g.ch[0][0] == 0x4e2d, "wide char=%u (0x%x)", g.ch[0][0],
	      g.ch[0][0]);
	CHECK(g.width[0][0] == 2, "wide char width=%u", g.width[0][0]);

	/* scrollback buffer */
	tsm_screen_set_max_sb(con, 64);
	FEED(vte, "\033[2J\033[H");
	for (int i = 0; i < 40; ++i)
		FEED(vte, "line\r\n");
	grid_capture(con, &g);
	CHECK(tsm_screen_sb_get_line_count(con) > 0, "scrollback empty");
	tsm_screen_clear_sb(con);
	CHECK(tsm_screen_sb_get_line_count(con) == 0, "scrollback not cleared");

	/* selection copy returns the selected text as UTF-8 */
	FEED(vte, "\033[2J\033[Hhello world");
	tsm_screen_selection_start(con, 0, 0);
	tsm_screen_selection_target(con, 4, 0);
	ret = tsm_screen_selection_copy(con, &sel);
	/* returns the number of copied bytes (negative errno on failure) */
	CHECK(ret == 5, "selection_copy ret=%d", ret);
	CHECK(sel != NULL && strcmp(sel, "hello") == 0, "selection=[%s]",
	      sel ? sel : "(null)");
	free(sel);
	sel = NULL;

	/* keyboard encoding: normal vs. DEC cursor-key application mode */
	writer_reset(&w);
	CHECK(tsm_vte_handle_keyboard(vte, KEY_UP, KEY_NONE, 0, 0),
	      "handle_keyboard(Up) returned false");
	CHECK(strcmp(w.buf, "\033[A") == 0, "Up normal mode=[%s]",
	      w.buf);

	FEED(vte, "\033[?1h");
	writer_reset(&w);
	CHECK(tsm_vte_handle_keyboard(vte, KEY_UP, KEY_NONE, 0, 0),
	      "handle_keyboard(Up) returned false in DECCKM");
	CHECK(strcmp(w.buf, "\033OA") == 0, "Up application mode=[%s]", w.buf);
	CHECK((tsm_vte_get_flags(vte) & TSM_VTE_FLAG_CURSOR_KEY_MODE) != 0,
	      "DECCKM flag not set: 0x%x", tsm_vte_get_flags(vte));

	FEED(vte, "\033[?1l");
	writer_reset(&w);
	/* printable input is taken from the `unicode` argument */
	CHECK(tsm_vte_handle_keyboard(vte, KEY_A, KEY_A, 0, KEY_A),
	      "handle_keyboard('a') returned false");
	CHECK(strcmp(w.buf, "a") == 0, "plain key=[%s]", w.buf);

	/* unicode helpers */
	CHECK(tsm_ucs4_get_width(0x4e2d) == 2, "ucs4 width(0x4e2d)=%u",
	      tsm_ucs4_get_width(0x4e2d));
	CHECK(tsm_ucs4_get_width('a') == 1, "ucs4 width('a')=%u",
	      tsm_ucs4_get_width('a'));
	{
		char u8[8];
		size_t n = tsm_ucs4_to_utf8(0x4e2d, u8);

		CHECK(n == 3 && (unsigned char)u8[0] == 0xe4 &&
		      (unsigned char)u8[1] == 0xb8 &&
		      (unsigned char)u8[2] == 0xad,
		      "ucs4_to_utf8 len=%zu bytes=%02x %02x %02x", n,
		      (unsigned char)u8[0], (unsigned char)u8[1],
		      (unsigned char)u8[2]);
	}

	/* reference counting keeps the objects alive */
	tsm_vte_ref(vte);
	tsm_screen_ref(con);
	tsm_vte_unref(vte);
	tsm_screen_unref(con);
	tsm_vte_unref(vte);
	tsm_screen_unref(con);
}

int main(void)
{
	test_screen_and_vte();

	printf("CHECKS: %d/%d passed\n", checks_total - checks_failed,
	       checks_total);
	if (checks_failed || checks_total == 0) {
		printf("RESULT: FAIL\n");
		return 1;
	}
	printf("RESULT: PASS\n");
	return 0;
}
