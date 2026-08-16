// test_ice.cpp — real consumer smoke test for the ZeroC Ice package.
//
// Links against libIce, initializes a Communicator, exercises the Ice runtime
// API (properties + version), then shuts it down cleanly.
//
// NOTE (Ice 3.8): setProperty/getProperty were removed from Ice::Communicator
// in 3.7; the property store now lives in Ice::Properties, reached via
// communicator->getProperties().
#include <Ice/Ice.h>
#include <cstdio>
#include <string>

int main(int argc, char* argv[])
{
    int status = 0;
    try
    {
        Ice::CommunicatorHolder ich(argc, argv);
        Ice::CommunicatorPtr communicator = ich.communicator();

        // Exercise real Ice runtime API: property round-trip through the runtime
        auto props = communicator->getProperties();
        props->setProperty("Test.RoundTrip", "42");
        std::string value = props->getProperty("Test.RoundTrip");
        if (value != "42")
        {
            std::printf("test ice 3.8.2: FAILED (property round-trip got '%s')\n", value.c_str());
            return 1;
        }

        // Validate the version macros against the packaged release (3.8.2).
        if (std::string(ICE_STRING_VERSION) != "3.8.2" || ICE_INT_VERSION != 30802)
        {
            std::printf("test ice 3.8.2: FAILED (version mismatch: string=%s int=%d)\n",
                        ICE_STRING_VERSION, ICE_INT_VERSION);
            return 1;
        }

        std::printf("test ice 3.8.2: OK (ICE_STRING_VERSION=%s, ICE_INT_VERSION=%d)\n",
                    ICE_STRING_VERSION, ICE_INT_VERSION);
        communicator->destroy();
    }
    catch (const std::exception& ex)
    {
        std::printf("test ice 3.8.2: FAILED (%s)\n", ex.what());
        status = 1;
    }
    return status;
}
