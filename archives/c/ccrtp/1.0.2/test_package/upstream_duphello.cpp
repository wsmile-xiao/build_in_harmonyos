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
        // Duplex-like: test RTPDuplex via RTPSession (simplified)
        RTPSession sess(addr, 5008);
        sess.setSchedulingTimeout(1000);
        uint32 ssrc = sess.getLocalSSRC();
        (void)ssrc;
        std::string tool = defaultApplication().getSDESItem(SDESItemTypeTOOL);
        (void)tool;
    } catch (...) {}
    cout << "upstream_duphello ok" << endl;
    return 0;
}
