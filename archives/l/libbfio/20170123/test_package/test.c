/* Consumer test for libbfio 20170123 on OpenHarmony.
 *
 * Exercises the installed library through its public file/handle API:
 * creates a real file with a known pattern, opens it through libbfio,
 * verifies size, sequential read, absolute seek and post-seek content.
 * Returns non-zero on any failed check.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libbfio.h>

#define TEST_PATTERN_SIZE 64

static int failures = 0;

#define CHECK(cond, msg) \
	do { \
		if( ( cond ) ) \
		{ \
			printf( "ok: %s\n", ( msg ) ); \
		} \
		else \
		{ \
			fprintf( stderr, "FAIL: %s (line %d)\n", ( msg ), __LINE__ ); \
			failures++; \
		} \
	} while( 0 )

int main( void )
{
	unsigned char pattern[ TEST_PATTERN_SIZE ];
	unsigned char buffer[ TEST_PATTERN_SIZE ];
	libbfio_handle_t *handle      = NULL;
	libbfio_error_t *error        = NULL;
	const char *version           = NULL;
	const char *filename          = "bfio_consumer_input.bin";
	size64_t size                 = 0;
	off64_t offset                = 0;
	ssize_t read_count            = 0;
	FILE *stream                  = NULL;
	int value                     = 0;

	for( value = 0; value < TEST_PATTERN_SIZE; value++ )
	{
		pattern[ value ] = (unsigned char)value;
	}

	stream = fopen( filename, "wb" );
	CHECK( stream != NULL, "create input file" );
	if( stream == NULL )
	{
		return( EXIT_FAILURE );
	}
	CHECK( fwrite( pattern, 1, TEST_PATTERN_SIZE, stream ) == TEST_PATTERN_SIZE, "write 64-byte pattern" );
	fclose( stream );

	version = libbfio_get_version();
	CHECK( version != NULL, "libbfio_get_version returns a string" );
	printf( "libbfio version: %s\n", version != NULL ? version : "(null)" );

	CHECK( libbfio_file_initialize( &handle, &error ) == 1, "libbfio_file_initialize" );
	if( handle == NULL )
	{
		remove( filename );

		return( EXIT_FAILURE );
	}

	CHECK( libbfio_file_set_name( handle, filename, strlen( filename ), &error ) == 1, "libbfio_file_set_name" );
	CHECK( libbfio_handle_open( handle, LIBBFIO_OPEN_READ, &error ) == 1, "libbfio_handle_open" );
	CHECK( libbfio_handle_get_size( handle, &size, &error ) == 1, "libbfio_handle_get_size" );
	CHECK( size == (size64_t)TEST_PATTERN_SIZE, "reported size is 64" );

	read_count = libbfio_handle_read_buffer( handle, buffer, TEST_PATTERN_SIZE, &error );
	CHECK( read_count == (ssize_t)TEST_PATTERN_SIZE, "read_buffer returns 64 bytes" );
	CHECK( memcmp( pattern, buffer, TEST_PATTERN_SIZE ) == 0, "sequential read matches pattern" );

	offset = libbfio_handle_seek_offset( handle, 16, SEEK_SET, &error );
	CHECK( offset == 16, "seek_offset(SEEK_SET, 16) reports 16" );

	memset( buffer, 0, sizeof( buffer ) );
	read_count = libbfio_handle_read_buffer( handle, buffer, 8, &error );
	CHECK( read_count == 8, "read_buffer after seek returns 8 bytes" );
	CHECK( memcmp( buffer, &pattern[ 16 ], 8 ) == 0, "post-seek content matches pattern offset 16" );

	CHECK( libbfio_handle_close( handle, &error ) == 0, "libbfio_handle_close" );
	libbfio_handle_free( &handle, &error );
	libbfio_error_free( &error );

	remove( filename );

	if( failures != 0 )
	{
		fprintf( stderr, "%d check(s) failed\n", failures );

		return( EXIT_FAILURE );
	}
	printf( "test_bfio: all checks passed\n" );

	return( EXIT_SUCCESS );
}
