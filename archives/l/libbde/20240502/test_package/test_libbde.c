/* Consumer test for libbde — calls the real public API (8 checks).
 *
 * Covers: libbde_get_version, libbde_get_access_flags_read,
 * libbde_get_codepage / libbde_set_codepage round-trip,
 * libbde_notify_set_verbose, libbde_volume_initialize /
 * libbde_volume_free lifecycle. Each check prints PASS on success;
 * the program exits 0 only when all 8 checks pass.
 */
#include <stdio.h>

#include <libbde.h>

int main(void)
{
	int checks_passed = 0;
	const int checks_total = 8;
	const char *version = NULL;
	int access_flags = 0;
	int codepage = -1;
	libbde_error_t *error = NULL;
	libbde_volume_t *volume = NULL;

	/* 1/8: library version is available. */
	version = libbde_get_version();
	if( version != NULL && version[ 0 ] != 0 )
	{
		printf( "PASS 1/8: libbde_get_version=%s\n", version );
		checks_passed++;
	}
	else
	{
		printf( "FAIL 1/8: libbde_get_version returned NULL or empty\n" );
		return 1;
	}

	/* 2/8: read access flags are non-zero. */
	access_flags = libbde_get_access_flags_read();
	if( access_flags != 0 )
	{
		printf( "PASS 2/8: libbde_get_access_flags_read=%d\n", access_flags );
		checks_passed++;
	}
	else
	{
		printf( "FAIL 2/8: read access flags are 0\n" );
		return 1;
	}

	/* 3/8: current codepage can be retrieved. */
	if( libbde_get_codepage( &codepage, &error ) == 1 )
	{
		printf( "PASS 3/8: libbde_get_codepage=%d\n", codepage );
		checks_passed++;
	}
	else
	{
		printf( "FAIL 3/8: libbde_get_codepage failed\n" );
		goto on_error;
	}

	/* 4/8: codepage round-trip (set back what we just read). */
	if( libbde_set_codepage( codepage, &error ) == 1 )
	{
		printf( "PASS 4/8: libbde_set_codepage=%d\n", codepage );
		checks_passed++;
	}
	else
	{
		printf( "FAIL 4/8: libbde_set_codepage failed\n" );
		goto on_error;
	}

	/* 5/8: notify verbosity switch (void API, must not crash). */
	libbde_notify_set_verbose( 0 );
	printf( "PASS 5/8: libbde_notify_set_verbose\n" );
	checks_passed++;

	/* 6/8: volume object can be created. */
	if( libbde_volume_initialize( &volume, &error ) == 1 && volume != NULL )
	{
		printf( "PASS 6/8: libbde_volume_initialize\n" );
		checks_passed++;
	}
	else
	{
		printf( "FAIL 6/8: libbde_volume_initialize failed\n" );
		goto on_error;
	}

	/* 7/8: volume object can be released. */
	if( libbde_volume_free( &volume, &error ) == 1 )
	{
		printf( "PASS 7/8: libbde_volume_free\n" );
		checks_passed++;
	}
	else
	{
		printf( "FAIL 7/8: libbde_volume_free failed\n" );
		goto on_error;
	}

	/* 8/8: no error leaked from the successful path. */
	if( error == NULL )
	{
		printf( "PASS 8/8: no error object leaked\n" );
		checks_passed++;
	}
	else
	{
		printf( "FAIL 8/8: unexpected error object\n" );
		goto on_error;
	}

	printf( "RESULT: %d/%d libbde checks passed\n", checks_passed, checks_total );

	return ( checks_passed == checks_total ) ? 0 : 1;

on_error:
	if( error != NULL )
	{
		libbde_error_free( &error );
	}
	if( volume != NULL )
	{
		if( libbde_volume_free( &volume, &error ) != 1 && error != NULL )
		{
			libbde_error_free( &error );
		}
	}
	return 1;
}
