#include <azure/core.hpp>
#include <azure/core/datetime.hpp>
#include <azure/core/context.hpp>
#include <azure/core/uuid.hpp>
#include <azure/core/url.hpp>
#include <iostream>
#include <string>
#include <cassert>

int main() {
    // Test 1: UUID generation
    auto uuid = Azure::Core::Uuid::CreateUuid();
    std::cout << "UUID: " << uuid.ToString() << std::endl;
    assert(!uuid.ToString().empty());

    // Test 2: DateTime parsing
    auto dt = Azure::DateTime::Parse("2026-08-22T12:00:00Z", Azure::DateTime::DateFormat::Rfc3339);
    std::cout << "DateTime: " << dt.ToString() << std::endl;

    // Test 3: URL parsing
    Azure::Core::Url url("https://example.com/path?query=value");
    std::cout << "URL scheme: " << url.GetScheme() << std::endl;
    std::cout << "URL host: " << url.GetHost() << std::endl;
    assert(url.GetScheme() == "https");
    assert(url.GetHost() == "example.com");

    // Test 4: Context
    Azure::Core::Context ctx;
    auto childCtx = ctx.WithDeadline(std::chrono::system_clock::now() + std::chrono::seconds(30));
    std::cout << "Context deadline set" << std::endl;

    std::cout << "All Azure Core tests passed!" << std::endl;
    return 0;
}