#include <Ice/Ice.h>
#include <iostream>

int
main(int argc, char* argv[])
{
    try
    {
        //
        // Initialize a communicator (exercises full library load, plugin
        // machinery and config handling) and print the header version.
        //
        Ice::CommunicatorHolder ich(argc, argv);
        std::cout << "Ice version: " << ICE_STRING_VERSION << std::endl;
    }
    catch(const std::exception& ex)
    {
        std::cerr << "test failed: " << ex.what() << std::endl;
        return 1;
    }
    return 0;
}
