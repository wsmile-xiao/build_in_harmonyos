/* test_package consumer test for mustach 1.2.10 (OHOS PC adaptation).
 *
 * Exercises the DELIVERED libmustach through its documented public core
 * interface (struct mustach_itf + mustach_mem/mustach_file, README
 * "simplest way" integration path): variable interpolation, list section
 * iteration, inverted section, HTML escaping vs raw triple mustache,
 * standalone section lines, item-not-found error reporting, reported-size
 * contract, version macro, and file-output rendering, reported-size contract, item-not-found error and the
 * version macro. 13 assertions total.
 *
 * Deliberately backend-agnostic (no cjson/json-c/jansson headers): the JSON
 * wrapper paths are exercised by the upstream tool tests (test1..test8 run
 * in build() via the packaged mustach CLI); this consumer test links the
 * shipped libmustach and includes the shipped mustach.h exactly like an
 * external consumer.
 *
 * Note: output file is created in the current working directory on purpose
 * (device /tmp is read-only).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mustach/mustach.h>

static int g_checks = 0;

static void check(int cond, const char *what)
{
	g_checks++;
	if (!cond) {
		fprintf(stderr, "FAIL[%d]: %s\n", g_checks, what);
		exit(1);
	}
	printf("ok %d - %s\n", g_checks, what);
}

/* ---- minimal fixed test tree ---- */

struct node {
	const char *key;
	const char *value;            /* scalar payload */
	int truthy;                   /* section truth value */
	const struct node *items;     /* section children */
	size_t nitems;
};

static const struct node repo_items[] = {
	{ "name", "resque", 0, NULL, 0 },
	{ "name", "hub",    0, NULL, 0 },
	{ "name", "rip",    0, NULL, 0 },
};

static const struct node root_items[] = {
	{ "name",   "OHOS",  0, NULL,       0 },
	{ "raw",    "a<b&c", 0, NULL,       0 },
	{ "person", NULL,    0, NULL,       0 },  /* false */
	{ "repo",   NULL,    1, repo_items, 3 },
};

/* ---- itf implementation (scope/iterator frame stack) ----
 *
 * depth 0 is the root scope (lookup scans all entries by key); entering a
 * list section pushes an iterator frame whose "current item" is
 * items[index] — lookups there match only the current item, and next()
 * advances it (mustach enter/next/leave contract).
 */
struct frame {
	const struct node *items;
	size_t count;
	size_t index;
	int is_scope; /* 1: key-scan scope; 0: iterating section, current = items[index] */
};

static struct frame stack[MUSTACH_MAX_DEPTH];
static int depth; /* stack[0] = root scope */

static const struct node *lookup(const char *name)
{
	const struct frame *f = &stack[depth];
	size_t i;

	if (f->is_scope) {
		for (i = 0; i < f->count; i++)
			if (strcmp(f->items[i].key, name) == 0)
				return &f->items[i];
		return NULL;
	}
	if (f->index < f->count && strcmp(f->items[f->index].key, name) == 0)
		return &f->items[f->index];
	return NULL;
}

static int cb_enter(void *closure, const char *name)
{
	const struct node *n = lookup(name);

	(void)closure;
	if (n == NULL || !n->truthy || n->items == NULL || n->nitems == 0)
		return 0;
	depth++;
	stack[depth].items = n->items;
	stack[depth].count = n->nitems;
	stack[depth].index = 0;
	stack[depth].is_scope = 0;
	return 1;
}

static int cb_next(void *closure)
{
	(void)closure;
	if (stack[depth].index + 1 < stack[depth].count) {
		stack[depth].index++;
		return 1;
	}
	return 0;
}

static int cb_leave(void *closure)
{
	(void)closure;
	depth--;
	return MUSTACH_OK;
}

static int cb_get(void *closure, const char *name, struct mustach_sbuf *sbuf)
{
	const struct node *n = lookup(name);

	(void)closure;
	if (n == NULL || n->value == NULL)
		return MUSTACH_ERROR_ITEM_NOT_FOUND;
	sbuf->value = n->value;
	sbuf->length = strlen(n->value);
	sbuf->closure = NULL;
	sbuf->freecb = NULL;
	return MUSTACH_OK;
}

static int cb_emit(void *closure, const char *buffer, size_t size, int escape, FILE *file)
{
	size_t i;

	(void)closure;
	if (!escape)
		return fwrite(buffer, 1, size, file) == size ? MUSTACH_OK : MUSTACH_ERROR_SYSTEM;
	for (i = 0; i < size; i++) {
		const char *rep;
		switch (buffer[i]) {
		case '<': rep = "&lt;";   break;
		case '>': rep = "&gt;";   break;
		case '&': rep = "&amp;";  break;
		case '"': rep = "&quot;"; break;
		default:  rep = NULL;     break;
		}
		if (rep == NULL)
			fputc(buffer[i], file);
		else
			fputs(rep, file);
	}
	return MUSTACH_OK;
}

int main(void)
{
	int rc;
	char *out = NULL;
	size_t size = 0;
	char buf[32];
	size_t got;
	FILE *f;
	const struct mustach_itf itf = {
		NULL, NULL,
		cb_enter, cb_next, cb_leave,
		NULL, cb_emit, cb_get, NULL,
	};

	stack[0].items = root_items;
	stack[0].count = 4;
	stack[0].index = 0;
	stack[0].is_scope = 1;
	depth = 0;

	check(MUSTACH_VERSION == 102, "header version macro is 1.2.x (MUSTACH_VERSION 102)");

	rc = mustach_mem("Hello {{name}}!", strlen("Hello {{name}}!"), &itf, NULL, 0, &out, &size);
	check(rc == MUSTACH_OK, "variable render returns 0");
	check(out != NULL && strcmp(out, "Hello OHOS!") == 0,
		"variable renders substituted value");
	check(size == strlen(out), "mustach_mem reports exact output size");
	free(out);

	out = NULL;
	rc = mustach_mem("{{#repo}}[{{name}}]{{/repo}}", strlen("{{#repo}}[{{name}}]{{/repo}}"), &itf, NULL, 0, &out, &size);
	check(rc == MUSTACH_OK && out != NULL && strcmp(out, "[resque][hub][rip]") == 0,
		"list section iterates array items in order");
	free(out);

	out = NULL;
	rc = mustach_mem("{{^person}}no person{{/person}}", strlen("{{^person}}no person{{/person}}"), &itf, NULL, 0, &out, &size);
	check(rc == MUSTACH_OK && out != NULL && strcmp(out, "no person") == 0,
		"inverted section renders when value is false");
	free(out);

	out = NULL;
	rc = mustach_mem("{{raw}}", strlen("{{raw}}"), &itf, NULL, 0, &out, &size);
	check(rc == MUSTACH_OK && out != NULL && strcmp(out, "a&lt;b&amp;c") == 0,
		"emit escaping rewrites HTML special characters");
	free(out);

	out = NULL;
	rc = mustach_mem("{{{raw}}}", strlen("{{{raw}}}"), &itf, NULL, 0, &out, &size);
	check(rc == MUSTACH_OK && out != NULL && strcmp(out, "a<b&c") == 0,
		"triple mustache emits unescaped raw value");
	free(out);

	out = NULL;
	rc = mustach_mem("{{missing}}", strlen("{{missing}}"), &itf, NULL, 0, &out, &size);
	check(rc == MUSTACH_ERROR_ITEM_NOT_FOUND, "unknown key reports ITEM_NOT_FOUND");

	rc = mustach_mem("A\n{{#person}}\nx\n{{/person}}\nB", strlen("A\n{{#person}}\nx\n{{/person}}\nB"), &itf, NULL, 0, &out, &size);
	check(rc == MUSTACH_OK && out != NULL && strcmp(out, "A\nB") == 0,
		"standalone section lines are removed");
	free(out);

	f = fopen("test_mustach_out.tmp", "w+");
	check(f != NULL, "local output file created");
	rc = mustach_file("{{name}}!", strlen("{{name}}!"), &itf, NULL, 0, f);
	check(rc == MUSTACH_OK, "file rendering returns 0");
	rewind(f);
	memset(buf, 0, sizeof buf);
	got = fread(buf, 1, sizeof buf - 1, f);
	fclose(f);
	remove("test_mustach_out.tmp");
	check(got == 5 && strcmp(buf, "OHOS!") == 0,
		"file output matches expected render");

	printf("test_mustach: all %d assertions passed\n", g_checks);
	return 0;
}
