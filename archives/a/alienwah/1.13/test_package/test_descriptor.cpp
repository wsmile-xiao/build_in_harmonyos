#include <cstring>
#include <iostream>

#include <dlfcn.h>
#include <ladspa.h>

using DescriptorFn = const LADSPA_Descriptor *(*)(unsigned long);

int main(int argc, char **argv) {
    if (argc != 2) {
        std::cerr << "usage: test_descriptor <aw.so>\n";
        return 2;
    }

    void *handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        std::cerr << dlerror() << "\n";
        return 1;
    }

    auto descriptor = reinterpret_cast<DescriptorFn>(dlsym(handle, "ladspa_descriptor"));
    if (!descriptor) {
        std::cerr << "ladspa_descriptor symbol not found\n";
        return 1;
    }

    const LADSPA_Descriptor *mono = descriptor(0);
    const LADSPA_Descriptor *stereo = descriptor(1);
    const LADSPA_Descriptor *missing = descriptor(2);

    if (!mono || !stereo || missing) {
        std::cerr << "unexpected descriptor table shape\n";
        return 1;
    }
    if (std::strcmp(mono->Label, "alienwah_mono") != 0 || mono->PortCount != 6) {
        std::cerr << "unexpected mono descriptor\n";
        return 1;
    }
    if (std::strcmp(stereo->Label, "alienwah_stereo") != 0 || stereo->PortCount != 8) {
        std::cerr << "unexpected stereo descriptor\n";
        return 1;
    }
    if (!mono->instantiate || !mono->connect_port || !mono->run || !mono->cleanup) {
        std::cerr << "mono descriptor is missing required callbacks\n";
        return 1;
    }
    if (!stereo->instantiate || !stereo->connect_port || !stereo->run || !stereo->cleanup) {
        std::cerr << "stereo descriptor is missing required callbacks\n";
        return 1;
    }

    dlclose(handle);
    return 0;
}
