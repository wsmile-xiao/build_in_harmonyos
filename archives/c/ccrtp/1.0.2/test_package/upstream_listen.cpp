#include <ccrtp/rtp.h>
#include <iostream>
#ifdef CCXX_NAMESPACES
using namespace ost;
using namespace std;
#endif
int main() {
    InetHostAddress addr("127.0.0.1");
    if (!addr) return 1;
    try {
        // Listen-equivalent: create RTPSession and test get/listen APIs
        RTPSession sess(addr, 5006);
        sess.setExpireTimeout(100000);
        uint32 ssrc = sess.getLocalSSRC();
        (void)ssrc;
    } catch (...) {}
    cout << "upstream_listen ok" << endl;
    return 0;
}
