/*
 * Minimal source-built terminfo fallback for pick on OHOS package builders.
 *
 * The upstream program only uses a small setupterm/tigetstr/tparm/tputs subset.
 * Building this file into a local archive avoids submitting prebuilt ncurses
 * binaries while keeping the terminal escape behavior needed by pick.
 */
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

struct cap_entry {
	const char *name;
	const char *value;
};

static const struct cap_entry caps[] = {
	{ "civis", "\033[?25l" },
	{ "cnorm", "\033[?25h" },
	{ "cr", "\r" },
	{ "cuf", "\033[%dC" },
	{ "cuu", "\033[%dA" },
	{ "ed", "\033[J" },
	{ "kcub1", "\033[D" },
	{ "kcud1", "\033[B" },
	{ "kcuf1", "\033[C" },
	{ "kcuu1", "\033[A" },
	{ "kdch1", "\033[3~" },
	{ "kend", "\033OF" },
	{ "khome", "\033OH" },
	{ "knp", "\033[6~" },
	{ "kpp", "\033[5~" },
	{ "rmcup", "\033[?1049l" },
	{ "rmkx", "" },
	{ "rmul", "\033[24m" },
	{ "sgr0", "\033[0m" },
	{ "smcup", "\033[?1049h" },
	{ "smkx", "" },
	{ "smso", "\033[7m" },
	{ "smul", "\033[4m" },
};

int
setupterm(char *term, int fd, int *errret)
{
	(void)term;
	(void)fd;
	if (errret != NULL)
		*errret = 1;
	return 0;
}

char *
tigetstr(const char *name)
{
	size_t i;

	for (i = 0; i < sizeof(caps) / sizeof(caps[0]); i++) {
		if (strcmp(caps[i].name, name) == 0)
			return (char *)caps[i].value;
	}

	return (char *)-1;
}

int
tigetnum(const char *name)
{
	if (strcmp(name, "cols") == 0)
		return 80;
	if (strcmp(name, "lines") == 0)
		return 24;
	return -2;
}

char *
tparm(const char *str, ...)
{
	static char buf[64];
	va_list ap;
	int value;

	if (str == NULL || str == (const char *)-1)
		return (char *)str;

	if (strstr(str, "%d") == NULL)
		return (char *)str;

	va_start(ap, str);
	value = va_arg(ap, int);
	va_end(ap);

	snprintf(buf, sizeof(buf), str, value);
	return buf;
}

int
tputs(const char *str, int affcnt, int (*putc_cb)(int))
{
	const unsigned char *cursor;

	(void)affcnt;
	if (str == NULL || str == (const char *)-1 || putc_cb == NULL)
		return -1;

	for (cursor = (const unsigned char *)str; *cursor != '\0'; cursor++)
		putc_cb(*cursor);
	return 0;
}
