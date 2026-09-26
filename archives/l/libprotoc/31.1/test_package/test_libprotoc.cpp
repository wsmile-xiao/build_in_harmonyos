// Consumer test for the packaged libprotoc compiler library.
//
// Drives libprotoc's public API directly (Importer / Descriptor /
// DescriptorPool / FileDescriptorProto) instead of shelling out to protoc,
// which is not part of this package.
#include <google/protobuf/compiler/importer.h>
#include <google/protobuf/descriptor.h>
#include <google/protobuf/descriptor.pb.h>
#include <google/protobuf/text_format.h>

#include <absl/strings/string_view.h>

#include <cstdio>
#include <string>

namespace {

int checks = 0;

#define CHECK_TRUE(condition)                                                   \
    do {                                                                        \
        if (!(condition)) {                                                     \
            std::fprintf(stderr, "check failed at line %d: %s\n", __LINE__,   \
                         #condition);                                           \
            return 1;                                                           \
        }                                                                       \
        ++checks;                                                               \
    } while (false)

// Collects compiler diagnostics so negative cases can be asserted on.
class CollectingErrorCollector
    : public google::protobuf::compiler::MultiFileErrorCollector {
  public:
    void RecordError(absl::string_view filename, int line, int column,
                     absl::string_view message) override {
        ++error_count_;
        last_error_ = std::string(filename) + ":" + std::to_string(line) + ":" +
                      std::to_string(column) + ": " + std::string(message);
    }

    int error_count() const { return error_count_; }
    const std::string& last_error() const { return last_error_; }

  private:
    int error_count_ = 0;
    std::string last_error_;
};

// Builds an Importer over the test schema directory.
class ImporterFixture {
  public:
    explicit ImporterFixture(const std::string& source_dir)
        : importer_(&source_tree_, &errors_) {
        source_tree_.MapPath("", source_dir);
    }

    google::protobuf::compiler::Importer& importer() { return importer_; }
    CollectingErrorCollector& errors() { return errors_; }
    const google::protobuf::FileDescriptor* Import(const std::string& name) {
        return importer_.Import(name);
    }

  private:
    google::protobuf::compiler::DiskSourceTree source_tree_;
    CollectingErrorCollector errors_;
    google::protobuf::compiler::Importer importer_;
};

// libprotoc must parse a proto3 file and expose its descriptors.
int TestDescriptor(const std::string& source_dir) {
    ImporterFixture fixture(source_dir);
    const google::protobuf::FileDescriptor* file =
        fixture.Import("libprotoc_test.proto");
    CHECK_TRUE(file != nullptr);
    CHECK_TRUE(fixture.errors().error_count() == 0);
    CHECK_TRUE(file->name() == "libprotoc_test.proto");
    CHECK_TRUE(file->package() == "libprotoc.test");

    CHECK_TRUE(file->message_type_count() == 2);
    CHECK_TRUE(file->enum_type_count() == 1);

    const google::protobuf::Descriptor* device =
        file->FindMessageTypeByName("DeviceInfo");
    CHECK_TRUE(device != nullptr);
    CHECK_TRUE(device->field_count() == 4);
    CHECK_TRUE(device->full_name() == "libprotoc.test.DeviceInfo");

    const google::protobuf::FieldDescriptor* name_field =
        device->FindFieldByName("name");
    CHECK_TRUE(name_field != nullptr);
    CHECK_TRUE(name_field->type() == google::protobuf::FieldDescriptor::TYPE_STRING);
    CHECK_TRUE(name_field->number() == 1);
    CHECK_TRUE(!name_field->is_repeated());

    const google::protobuf::FieldDescriptor* caps =
        device->FindFieldByName("capabilities");
    CHECK_TRUE(caps != nullptr);
    CHECK_TRUE(caps->is_repeated());
    CHECK_TRUE(caps->label() == google::protobuf::FieldDescriptor::LABEL_REPEATED);
    return 0;
}

// The descriptor pool libprotoc populates must be queryable by name.
int TestPool(const std::string& source_dir) {
    ImporterFixture fixture(source_dir);
    const google::protobuf::FileDescriptor* file =
        fixture.Import("libprotoc_test.proto");
    CHECK_TRUE(file != nullptr);

    const google::protobuf::DescriptorPool* pool = fixture.importer().pool();
    CHECK_TRUE(pool != nullptr);
    CHECK_TRUE(pool->FindFileByName("libprotoc_test.proto") == file);

    const google::protobuf::Descriptor* list =
        pool->FindMessageTypeByName("libprotoc.test.DeviceList");
    CHECK_TRUE(list != nullptr);
    CHECK_TRUE(list->field_count() == 2);

    const google::protobuf::EnumDescriptor* kind =
        pool->FindEnumTypeByName("libprotoc.test.DeviceKind");
    CHECK_TRUE(kind != nullptr);
    CHECK_TRUE(kind->value_count() == 3);
    CHECK_TRUE(kind->FindValueByName("DEVICE_KIND_PC") != nullptr);
    return 0;
}

// Importing the same file twice must be stable and return the same descriptor.
int TestImporter(const std::string& source_dir) {
    ImporterFixture fixture(source_dir);
    const google::protobuf::FileDescriptor* first =
        fixture.Import("libprotoc_test.proto");
    const google::protobuf::FileDescriptor* second =
        fixture.Import("libprotoc_test.proto");
    CHECK_TRUE(first != nullptr);
    CHECK_TRUE(first == second);
    CHECK_TRUE(fixture.errors().error_count() == 0);
    return 0;
}

// A missing file must be reported through the collector, not crash the process.
int TestDiagnostics(const std::string& source_dir) {
    ImporterFixture fixture(source_dir);
    const google::protobuf::FileDescriptor* missing =
        fixture.Import("no_such_schema.proto");
    CHECK_TRUE(missing == nullptr);
    CHECK_TRUE(fixture.errors().error_count() > 0);
    CHECK_TRUE(fixture.errors().last_error().find("no_such_schema.proto") !=
               std::string::npos);
    return 0;
}

// Descriptor protos produced by libprotoc must round-trip through the runtime
// text format, which is what downstream code generators rely on.
int TestRoundtrip(const std::string& source_dir) {
    ImporterFixture fixture(source_dir);
    const google::protobuf::FileDescriptor* file =
        fixture.Import("libprotoc_test.proto");
    CHECK_TRUE(file != nullptr);

    google::protobuf::FileDescriptorProto proto;
    file->CopyTo(&proto);
    CHECK_TRUE(proto.name() == "libprotoc_test.proto");
    CHECK_TRUE(proto.package() == "libprotoc.test");
    CHECK_TRUE(proto.message_type_size() == 2);

    std::string text;
    CHECK_TRUE(google::protobuf::TextFormat::PrintToString(proto, &text));
    CHECK_TRUE(text.find("libprotoc.test") != std::string::npos);

    google::protobuf::FileDescriptorProto parsed;
    CHECK_TRUE(google::protobuf::TextFormat::ParseFromString(text, &parsed));
    CHECK_TRUE(parsed.message_type_size() == 2);
    CHECK_TRUE(parsed.message_type(0).field_size() == 4);
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::fprintf(stderr,
                     "usage: %s descriptor|pool|importer|diagnostics|roundtrip"
                     " <source_dir>\n",
                     argv[0]);
        return 2;
    }

    const std::string mode(argv[1]);
    const std::string source_dir(argv[2]);
    int result = 2;
    if (mode == "descriptor") {
        result = TestDescriptor(source_dir);
    } else if (mode == "pool") {
        result = TestPool(source_dir);
    } else if (mode == "importer") {
        result = TestImporter(source_dir);
    } else if (mode == "diagnostics") {
        result = TestDiagnostics(source_dir);
    } else if (mode == "roundtrip") {
        result = TestRoundtrip(source_dir);
    } else {
        std::fprintf(stderr, "unknown test mode: %s\n", mode.c_str());
        return 2;
    }

    if (result == 0) {
        std::printf("libprotoc %s: %d assertions passed\n", mode.c_str(), checks);
    }
    return result;
}
