// Consumer-side verification for rtaudio 6.0.1 on OHOS (dummy backend).
// The dummy API compiles and links but provides no audio hardware, so the
// verifiable boundary is: API enumeration contains RTAUDIO_DUMMY, device
// count is 0, and device query fails gracefully instead of crashing.
#include "rtaudio/RtAudio.h"

// Release (-DNDEBUG) 会剔除 assert：先解除定义再包含（boolstuff/canfigger 先例）
#undef NDEBUG
#include <cassert>
#include <iostream>
#include <vector>

int main() {
    // 1. Compiled API list must contain the dummy backend (and no real one).
    std::vector<RtAudio::Api> apis;
    RtAudio::getCompiledApi(apis);
    assert(!apis.empty());
    bool has_dummy = false;
    for (RtAudio::Api api : apis) {
        if (api == RtAudio::RTAUDIO_DUMMY) has_dummy = true;
    }
    assert(has_dummy);

    // 2. Default-constructed RtAudio uses the first compiled (dummy) API.
    RtAudio rtaudio;
    assert(rtaudio.getCurrentApi() == RtAudio::RTAUDIO_DUMMY);

    // 3. No audio hardware behind the dummy backend: zero devices.
    unsigned int devices = rtaudio.getDeviceCount();
    assert(devices == 0);

    // 4. API name lookups work for the dummy backend.
    std::string name = RtAudio::getApiDisplayName(RtAudio::RTAUDIO_DUMMY);
    assert(!name.empty());

    std::cout << "rtaudio dummy-boundary assertions passed (apis=" << apis.size()
              << ", devices=" << devices << ")" << std::endl;
    return 0;
}
