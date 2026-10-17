#include <zim/zim.h>
#include <zim/archive.h>
#include <zim/item.h>
#include <zim/writer/creator.h>
#include <zim/writer/item.h>
#include <zim/writer/contentProvider.h>

#include <cstdio>
#include <string>

class StringProvider : public zim::writer::ContentProvider {
public:
    explicit StringProvider(const std::string& data) : m_data(data) {}
    zim::size_type getSize() const override { return m_data.size(); }
    zim::Blob feed() override {
        return zim::Blob(m_data.data(), m_data.size());
    }
private:
    std::string m_data;
};

class TestItem : public zim::writer::Item {
public:
    std::string getPath() const override { return "A/test"; }
    std::string getTitle() const override { return "Test Item"; }
    std::string getMimeType() const override { return "text/plain"; }
    std::unique_ptr<zim::writer::ContentProvider> getContentProvider() const override {
        return std::make_unique<StringProvider>("Hello libzim!");
    }
};

int main() {
    const char* fname = "test_libzim_output.zim";
    zim::writer::Creator creator;
    creator.configIndexing(true, "eng");
    creator.startZimCreation(fname);
    auto witem = std::make_shared<TestItem>();
    creator.addItem(witem);
    creator.finishZimCreation();

    // Verify the created ZIM with the reader API
    zim::Archive archive(fname);
    if (!archive.hasEntryByPath("A/test")) {
        std::fprintf(stderr, "FAIL: entry not found\n");
        return 1;
    }
    auto entry = archive.getEntryByPath("A/test");
    auto ritem = entry.getItem();
    auto blob = ritem.getData();
    std::string content(blob.data(), blob.size());
    if (content != "Hello libzim!") {
        std::fprintf(stderr, "FAIL: unexpected content: %s\n", content.c_str());
        return 2;
    }
    std::remove(fname);
    std::printf("libzim API test PASSED: wrote %zu bytes, read back '%s'\n",
                content.size(), content.c_str());
    return 0;
}
