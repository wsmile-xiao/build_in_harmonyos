/*
 * Consumer test for the installed unqlite 1.2.1 package.
 *
 * Drives the real engine behaviour of the library through its public API:
 *  1) key/value engine — opens an in-memory database, stores a record,
 *     fetches it back, deletes it, and verifies the record is gone;
 *  2) Jx9 document store — compiles and executes a Jx9 script that creates
 *     a collection, stores JSON records and fetches them with a filter
 *     callback, asserting real VM output.
 * All checks assert actual behaviour via return codes and data comparison.
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

/* Jx9 VM output consumer: appends the VM output to a buffer. */
static int vm_output_consumer(const void *pOut, unsigned int nLen, void *pUserData)
{
	char *buf = (char *)pUserData;
	unsigned int cur = (unsigned int)strlen(buf);
	if(cur + nLen < 256)
	{
		memcpy(buf + cur, pOut, nLen);
		buf[cur + nLen] = 0;
	}
	return UNQLITE_OK;
}

int main(void)
{
	unqlite *pDb = NULL;
	const char key[] = "greeting";
	const char val[] = "Hello HarmonyOS";
	unqlite_int64 len = 0;
	char buf[64];

	memset(buf, 0, sizeof(buf));

	/* ---------- Key/value engine ---------- */
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

	/* ---------- Jx9 document store ---------- */
	pDb = NULL;
	{
		unqlite_vm *pVm = NULL;
		char vmout[256];

		const char *zJx9 =
			"if( !db_exists('users') ){"
			"  $rc = db_create('users');"
			"  if( !$rc ){ print db_errlog(); return; }"
			"}"
			"$zRec = ["
			"  { name : 'alice', age : 27, mail : 'a@example.com' },"
			"  { name : 'bob',   age : 35, mail : 'b@example.com' },"
			"  { name : 'carol', age : 47, mail : 'c@example.com' }"
			"];"
			"$rc = db_store('users',$zRec);"
			"if( !$rc ){ print db_errlog(); return; }"
			"$zCallback = function($rec){ if( $rec.age < 30 ){ return FALSE; } return TRUE; };"
			"$data = db_fetch_all('users',$zCallback);"
			"foreach($data as $value){ print $value..JX9_EOL; }";

		check(unqlite_open(&pDb, ":mem:", UNQLITE_OPEN_IN_MEMORY) == UNQLITE_OK,
			"open in-memory db for Jx9");

		memset(vmout, 0, sizeof(vmout));
		check(unqlite_compile(pDb, zJx9, -1, &pVm) == UNQLITE_OK,
			"jx9 compile of document-store script");

		check(unqlite_vm_config(pVm, UNQLITE_VM_CONFIG_OUTPUT,
			vm_output_consumer, vmout) == UNQLITE_OK,
			"jx9 vm_config installs output consumer");

		check(unqlite_vm_exec(pVm) == UNQLITE_OK,
			"jx9 vm_exec runs the script");

		check(strstr(vmout, "\"bob\"") != NULL
			&& strstr(vmout, "\"carol\"") != NULL
			&& strstr(vmout, "\"alice\"") == NULL,
			"jx9 doc-store filter keeps age>=30 records only");

		check(unqlite_vm_release(pVm) == UNQLITE_OK,
			"jx9 vm_release frees the VM");

		if(pDb != NULL)
			unqlite_close(pDb);
	}

	if(failures != 0)
	{
		printf("%d check(s) FAILED\n", failures);
		return 1;
	}
	printf("all unqlite 1.2.1 consumer checks passed\n");
	return 0;
}
