#include <cstdio>
#include <sys/time.h>

#include <vrpn_Connection.h>
#include <vrpn_Shared.h>

int main(void) {
    struct timeval tv;
    if (vrpn_gettimeofday(&tv, NULL) != 0) {
        std::printf("vrpn 07.36: vrpn_gettimeofday failed\n");
        return 1;
    }
    /* Real libvrpn linkage: connection factory for an endpoint that cannot
       connect (loopback port 1 refused). Exercises the vrpn_Connection API
       from the packaged library. VRPN public headers are C++ headers. */
    vrpn_Connection *conn = vrpn_get_connection_by_name("@127.0.0.1:1");
    if (conn != NULL) {
        conn->removeReference();
    }
    std::printf("vrpn 07.36: API OK (vrpn_gettimeofday tv_sec=%ld)\n", (long)tv.tv_sec);
    return 0;
}
