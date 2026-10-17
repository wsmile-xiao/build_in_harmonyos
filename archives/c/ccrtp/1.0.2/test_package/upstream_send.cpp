#include <ccrtp/rtp.h>
#include <ccrtp/formats.h>
#include <iostream>
#ifdef CCXX_NAMESPACES
using namespace ost;
using namespace std;
#endif
int main() {
    InetHostAddress addr("127.0.0.1");
    if (!addr) return 1;
    try {
        RTPSession sess(InetHostAddress("0.0.0.0"));
        sess.setPayloadFormat(StaticPayloadFormat(sptPCMU));
        uint32 ssrc = sess.getLocalSSRC();
        (void)ssrc;
    } catch (...) {}
    cout << "upstream_send ok" << endl;
    return 0;
}
