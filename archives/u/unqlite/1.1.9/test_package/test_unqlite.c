/*
 * Consumer test for the installed unqlite package.
 *
 * Drives the real key/value engine of the library: opens an in-memory
 * database, stores a record, fetches it back, deletes it, and verifies
 * the record is gone. All checks assert actual behaviour via return codes
 * and data comparison.
 */
#include <stdio.h>
#include <string.h>

#include "unqlite.h"

static int failures = 0;

static void check(int cond, const char* what)
{
	if(cond)
		printf("PASS: %s\n", what);
	else
	{
		printf("FAIL: %s\n", what);
		failures++;
	}
}

int main(void)
{
	unqlite *pDb = NULL;
	const char key[] = "greeting";
	const char val[] = "Hello HarmonyOS";
	unqlite_int64 len = 0;
	char buf[64];

	memset(buf, 0, sizeof(buf));

	check(unqlite_open(&pDb, ":mem:", UNQLITE_OPEN_IN_MEMORY) == UNQLITE_OK,
		"open in-memory database");

	check(unqlite_kv_store(pDb, key, -1, val,
		(unqlite_int64)strlen(val)) == UNQLITE_OK,
		"kv_store persists a record");

	check(unqlite_kv_fetch(pDb, key, -1, NULL, &len) == UNQLITE_OK
		&& len == (unqlite_int64)strlen(val),
		"kv_fetch reports the stored length");

	check(unqlite_kv_fetch(pDb, key, -1, buf, &len) == UNQLITE_OK
		&& strcmp(buf, val) == 0,
		"kv_fetch round-trips the stored value");

	check(unqlite_kv_delete(pDb, key, -1) == UNQLITE_OK,
		"kv_delete removes the record");

	check(unqlite_kv_fetch(pDb, key, -1, NULL, &len) == UNQLITE_NOTFOUND,
		"kv_fetch after delete reports UNQLITE_NOTFOUND");

	if(pDb != NULL)
		unqlite_close(pDb);

	if(failures != 0)
	{
		printf("%d check(s) FAILED\n", failures);
		return 1;
	}
	printf("all unqlite consumer checks passed\n");
	return 0;
}
