// Azure Identity SDK for C++ — credential provider smoke test.
// Exercise the public credential API surface (construction only;
// no network calls — token acquisition requires a live tenant).

#include <azure/identity.hpp>
#include <iostream>
#include <memory>
#include <vector>
#include <cassert>

int main() {
    // Test 1: ClientSecretCredential local construction
    Azure::Identity::ClientSecretCredentialOptions secretOptions;
    Azure::Identity::ClientSecretCredential clientSecretCredential(
        "test-tenant-id", "test-client-id", "test-client-secret", secretOptions);
    std::cout << "ClientSecretCredential constructed" << std::endl;

    // Test 2: EnvironmentCredential local construction
    Azure::Identity::EnvironmentCredential environmentCredential;
    std::cout << "EnvironmentCredential constructed" << std::endl;

    // Test 3: ChainedTokenCredential over multiple sources
    Azure::Identity::ChainedTokenCredential::Sources sources;
    sources.push_back(std::make_shared<Azure::Identity::ClientSecretCredential>(
        "test-tenant-id", "test-client-id", "test-client-secret"));
    Azure::Identity::ChainedTokenCredential chainedCredential(sources);
    std::cout << "ChainedTokenCredential constructed with "
              << static_cast<size_t>(sources.size()) << " source" << std::endl;
    assert(sources.size() == 1);

    // Test 4: DefaultAzureCredential constructs without network access
    Azure::Core::Credentials::TokenCredentialOptions defaultOptions;
    Azure::Identity::DefaultAzureCredential defaultCredential(defaultOptions);
    std::cout << "DefaultAzureCredential constructed" << std::endl;

    std::cout << "All Azure Identity credential construction tests passed!" << std::endl;
    return 0;
}