// HarmonyOS-specific test for the packaged libprotoc.
//
// Verifies that the compiler library actually runs on the OHOS musl runtime,
// not merely that it compiles: descriptor import through the file-backed
// source tree, compiler diagnostics for a missing file (musl errno/strerror
// path), descriptor-pool construction, and text-format round trips.
//
// This is an additional check on top of the upstream protobuf test suite and
// does not replace the upstream test statistics.
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

// 1. libprotoc must import a schema and populate a queryable descriptor pool
//    on this runtime.
int TestImportOnOhos(const std::string& source_dir) {
    google::protobuf::compiler::DiskSourceTree source_tree;
    source_tree.MapPath("", source_dir);
    CollectingErrorCollector errors;
    google::protobuf::compiler::Importer importer(&source_tree, &errors);

    const google::protobuf::FileDescriptor* file =
        importer.Import("libprotoc_test.proto");
    CHECK_TRUE(file != nullptr);
    CHECK_TRUE(errors.error_count() == 0);
    CHECK_TRUE(file->package() == "libprotoc.test");
    CHECK_TRUE(file->message_type_count() == 2);

    const google::protobuf::Descriptor* device =
        file->FindMessageTypeByName("DeviceInfo");
    CHECK_TRUE(device != nullptr);
    CHECK_TRUE(device->field_count() == 4);
    CHECK_TRUE(device->FindFieldByName("capabilities")->is_repeated());

    const google::protobuf::DescriptorPool* pool = importer.pool();
    CHECK_TRUE(pool != nullptr);
    CHECK_TRUE(pool->FindFileByName("libprotoc_test.proto") == file);
    CHECK_TRUE(pool->FindMessageTypeByName("libprotoc.test.DeviceList") != nullptr);
    return 0;
}

// 2. Missing-file diagnostics must be reported rather than aborting (exercises
//    the musl errno/strerror path used for compiler error messages).
int TestDiagnosticsOnOhos(const std::string& source_dir) {
    google::protobuf::compiler::DiskSourceTree source_tree;
    source_tree.MapPath("", source_dir);
    CollectingErrorCollector errors;
    google::protobuf::compiler::Importer importer(&source_tree, &errors);

    const google::protobuf::FileDescriptor* missing =
        importer.Import("definitely_missing_schema.proto");
    CHECK_TRUE(missing == nullptr);
    CHECK_TRUE(errors.error_count() > 0);
    CHECK_TRUE(errors.last_error().find("definitely_missing_schema.proto") !=
               std::string::npos);
    return 0;
}

// 3. The runtime facilities libprotoc builds on must round-trip descriptor
//    protos, which is what downstream code generators consume.
int TestRuntimeFacilitiesOnOhos() {
    google::protobuf::FileDescriptorProto proto;
    proto.set_name("ohos_libprotoc_check.proto");
    proto.set_package("ohos.libprotoc.check");
    proto.set_syntax("proto3");
    google::protobuf::DescriptorProto* message = proto.add_message_type();
    message->set_name("Probe");
    google::protobuf::FieldDescriptorProto* field = message->add_field();
    field->set_name("id");
    field->set_number(1);
    field->set_label(google::protobuf::FieldDescriptorProto::LABEL_OPTIONAL);
    field->set_type(google::protobuf::FieldDescriptorProto::TYPE_UINT32);

    std::string text;
    CHECK_TRUE(google::protobuf::TextFormat::PrintToString(proto, &text));
    CHECK_TRUE(text.find("ohos_libprotoc_check.proto") != std::string::npos);
    CHECK_TRUE(text.find("Probe") != std::string::npos);

    google::protobuf::FileDescriptorProto parsed;
    CHECK_TRUE(google::protobuf::TextFormat::ParseFromString(text, &parsed));
    CHECK_TRUE(parsed.package() == "ohos.libprotoc.check");
    CHECK_TRUE(parsed.message_type_size() == 1);
    CHECK_TRUE(parsed.message_type(0).field(0).number() == 1);
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::fprintf(stderr, "usage: %s <source_dir>\n", argv[0]);
        return 2;
    }

    if (TestImportOnOhos(argv[1]) != 0) {
        return 1;
    }
    if (TestDiagnosticsOnOhos(argv[1]) != 0) {
        return 1;
    }
    if (TestRuntimeFacilitiesOnOhos() != 0) {
        return 1;
    }

    std::printf("libprotoc OHOS runtime: %d assertions passed\n", checks);
    return 0;
}
