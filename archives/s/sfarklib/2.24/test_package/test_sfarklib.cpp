#include <cstdio>
#include <cstdlib>
#include <iostream>

#include "sfArkLib.h"

#ifndef __OHOS__
#error "This test must be built with the HarmonyOS toolchain"
#endif

namespace {

int message_count = 0;
int progress_count = 0;
int license_count = 0;
int notes_count = 0;

void require(bool condition, const char *message)
{
    if (!condition) {
        std::cerr << "FAILED: " << message << std::endl;
        std::exit(EXIT_FAILURE);
    }
}

}  // namespace

void sfkl_msg(const char *message, int)
{
    if (message != nullptr && message[0] != '\0') {
        ++message_count;
    }
}

void sfkl_UpdateProgress(int)
{
    ++progress_count;
}

bool sfkl_GetLicenseAgreement(const char *, const char *)
{
    ++license_count;
    return true;
}

void sfkl_DisplayNotes(const char *, const char *)
{
    ++notes_count;
}

int main()
{
    const char *missing_input = "sfarklib-ohos-missing.sfArk";
    const char *unexpected_output = "sfarklib-ohos-unexpected.sf2";
    std::remove(missing_input);
    std::remove(unexpected_output);

    require(sfkl_GetVersion() == 300, "library version should be 3.00");
    const int result = sfkl_Decode(missing_input, unexpected_output);
    require(result == SFARKLIB_ERR_FILEIO, "missing input should report file I/O");
    require(message_count > 0, "file error should invoke the message callback");
    require(progress_count == 0, "file error should not report progress");
    require(license_count == 0, "file error should not request a license");
    require(notes_count == 0, "file error should not display notes");
    require(
        std::fopen(unexpected_output, "rb") == nullptr,
        "file error should not create an output file"
    );

    std::cout << "sfarklib HarmonyOS consumer test: 7 assertions passed"
              << std::endl;
    return EXIT_SUCCESS;
}
