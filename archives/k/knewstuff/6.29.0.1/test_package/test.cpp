#include <iostream>
#include <KNSCore/Entry>
#include <KNSCore/Author>

int main() {
    // Real KNewStuffCore API: create and manipulate an Entry object
    KNSCore::Entry entry;
    entry.setName("Test Asset");
    entry.setUniqueId("test-asset-001");
    entry.setCategory("test-category");
    entry.setSummary("A test entry for knewstuff smoke test");
    entry.setVersion("1.0.0");

    KNSCore::Author author;
    author.setName("OHOS Test Runner");
    entry.setAuthor(author);

    if (!entry.isValid()) {
        std::cerr << "FAIL: Entry should be valid after setting properties" << std::endl;
        return 1;
    }
    if (entry.name() != "Test Asset") {
        std::cerr << "FAIL: name mismatch: " << entry.name().toStdString() << std::endl;
        return 1;
    }
    if (entry.providerId().isEmpty()) {
        // providerId is empty for a freshly constructed Entry (not adopted) — expected
        std::cout << "OK: providerId empty (unadopted Entry as expected)" << std::endl;
    }
    std::cout << "PASS: KNewStuffCore Entry API smoke test" << std::endl;
    return 0;
}