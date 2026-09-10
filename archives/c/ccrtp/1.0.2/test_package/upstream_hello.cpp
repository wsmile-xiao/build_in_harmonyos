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
        RTPSession sess(addr, 5004);
        uint32 ssrc = sess.getLocalSSRC();
        (void)ssrc;
        std::string cname = defaultApplication().getSDESItem(SDESItemTypeCNAME);
        (void)cname;
    } catch (...) {}
    cout << "upstream_hello ok" << endl;
    return 0;
}
