#include <stdio.h>
#include <cassandra.h>

int main(void) {
    /* Verify version macros match expected values */
    if (CASS_VERSION_MAJOR != 2 || CASS_VERSION_MINOR != 17 || CASS_VERSION_PATCH != 1) {
        printf("Version mismatch: %d.%d.%d\n", CASS_VERSION_MAJOR, CASS_VERSION_MINOR, CASS_VERSION_PATCH);
        return 1;
    }

    /* Create and free a cluster object to verify the library is functional */
    CassCluster *cluster = cass_cluster_new();
    if (cluster == NULL) {
        printf("Failed to create cluster\n");
        return 1;
    }
    cass_cluster_free(cluster);

    /* Create and free a session object */
    CassSession *session = cass_session_new();
    if (session == NULL) {
        printf("Failed to create session\n");
        return 1;
    }
    CassFuture *close_future = cass_session_close(session);
    cass_future_wait(close_future);
    cass_future_free(close_future);
    cass_session_free(session);

    printf("cassandra-cpp-driver 2.17.1 test: OK\n");
    return 0;
}
