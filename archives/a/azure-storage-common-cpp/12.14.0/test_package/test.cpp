// test_package — L1 test for azure-storage-common-cpp 12.14.0
// Verifies that the library can be consumed: headers included, API linked.

#include <azure/storage/common/storage_common.hpp>
#include <azure/storage/common/storage_credential.hpp>
#include <cstdio>

int main(void)
{
    // Test 1: Verify header inclusion and basic type usage
    // Azure::Storage::Metadata is defined in storage_common.hpp
    Azure::Storage::Metadata metadata;
    (void)metadata;

    // Test 2: Verify connection string parsing (from storage_credential.hpp)
    auto connectionString = Azure::Storage::_internal::ParseConnectionString(
        "DefaultEndpointsProtocol=https;AccountName=testaccount;AccountKey=testkey");
    (void)connectionString;

    std::printf("test azure-storage-common-cpp 12.14.0: OK\n");
    return 0;
}