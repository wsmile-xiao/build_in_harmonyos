#include <stdio.h>
#include <string.h>

#include <nih/alloc.h>
#include <nih/list.h>
#include <nih/string.h>

/* Consumer test for libnih: exercises alloc + string + list APIs.
 * Each block prints PASS on success and bumps failures on error;
 * exit code is non-zero when any check fails (R34: real API calls).
 */

typedef struct item {
	NihList entry;
	char *text;
} Item;

int
main (void)
{
	int failures = 0;
	/* nih_new(parent, type) takes exactly 2 args (see nih/alloc.h:
	 * #define nih_new(parent, type) ... nih_alloc(parent, sizeof(type)));
	 * a bare byte context has no struct type, so use nih_alloc directly. */
	void *ctx = nih_alloc (NULL, 1);

	/* 1. nih_alloc: parent-tracked allocation works */
	if (ctx == NULL) {
		printf ("FAIL: nih_alloc returned NULL\n");
		failures++;
	} else {
		printf ("PASS: nih_alloc allocated context\n");
	}

	/* 2. nih_string: strdup duplicates content */
	if (ctx != NULL) {
		char *dup = nih_strdup (ctx, "harmonyos");
		if (dup == NULL || strcmp (dup, "harmonyos") != 0) {
			printf ("FAIL: nih_strdup mismatch\n");
			failures++;
		} else {
			printf ("PASS: nih_strdup round-trip ok\n");
		}
	}

	/* 3. nih_list: build a 2-item list and count it */
	if (ctx != NULL) {
		NihList *head = nih_list_new (ctx);
		Item *a = nih_new (head, Item);
		Item *b = nih_new (head, Item);
		int count = 0;

		if (head == NULL || a == NULL || b == NULL) {
			printf ("FAIL: nih_list_new/nih_new returned NULL\n");
			failures++;
		} else {
			nih_list_init (&a->entry);
			nih_list_init (&b->entry);
			a->text = nih_strdup (a, "one");
			b->text = nih_strdup (b, "two");
			nih_list_add (head, &a->entry);
			nih_list_add (head, &b->entry);

			NIH_LIST_FOREACH (head, iter) {
				count++;
				(void)iter;
			}
			if (count != 2) {
				printf ("FAIL: nih_list count=%d, want 2\n", count);
				failures++;
			} else if (strcmp (a->text, "one") != 0
				   || strcmp (b->text, "two") != 0) {
				printf ("FAIL: nih_list payload mismatch\n");
				failures++;
			} else {
				printf ("PASS: nih_list holds 2 items\n");
			}
		}
	}

	if (ctx != NULL)
		nih_free (ctx);

	if (failures == 0)
		printf ("libnih consumer test: all 3 checks passed\n");
	else
		printf ("libnih consumer test: %d check(s) failed\n", failures);

	return failures ? 1 : 0;
}
