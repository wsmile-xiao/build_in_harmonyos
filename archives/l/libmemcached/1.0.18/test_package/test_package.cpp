#include <libmemcached/memcached.h>
#include <stdio.h>
int main(void) {
    memcached_st *memc = memcached_create(NULL);
    if (!memc) { fprintf(stderr, "Failed\n"); return 1; }
    memcached_return_t rc = memcached_server_add(memc, "127.0.0.1", 11211);
    printf("version: %s\n", LIBMEMCACHED_VERSION_STRING);
    printf("server_add: %s\n", memcached_strerror(NULL, rc));
    memcached_free(memc);
    printf("PASSED\n");
    return 0;
}
