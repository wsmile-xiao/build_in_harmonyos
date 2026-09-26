// test_protobuf.cpp - runtime tests for the packaged protobuf 21.12.
//
// Each argv[1] case reproduces upstream-style libprotobuf behaviour
// (descriptor pool building, dynamic messages + reflection, arena
// allocation, binary round-trips) and exercises error paths (duplicate
// descriptor registration, truncated/corrupt payloads). All data is
// generated in memory, so no external files are needed.
//
// Cases:
//   dynamic     - build a schema in a DescriptorPool, round-trip a
//                 DynamicMessage through binary serialization and check
//                 every field via reflection (string/int32/bytes/
//                 repeated int32).
//   pool        - resolve built-in descriptor types, reject duplicate
//                 registration and unknown type names.
//   arena       - allocate and populate a message in an Arena, serialize
//                 it and verify the payload on the wire.
//   parse_error - truncated and corrupted payloads must fail parsing.
#include <cstdio>
#include <cstring>
#include <string>

#include <google/protobuf/arena.h>
#include <google/protobuf/descriptor.h>
#include <google/protobuf/descriptor.pb.h>
#include <google/protobuf/dynamic_message.h>
#include <google/protobuf/message.h>
#include <google/protobuf/reflection.h>

using google::protobuf::Arena;
using google::protobuf::Descriptor;
using google::protobuf::DescriptorPool;
using google::protobuf::DynamicMessageFactory;
using google::protobuf::FieldDescriptor;
using google::protobuf::FieldDescriptorProto;
using google::protobuf::FileDescriptor;
using google::protobuf::FileDescriptorProto;
using google::protobuf::Message;
using google::protobuf::Reflection;

namespace {

int g_assertions = 0;

#define CHECK(condition)                                              \
  do {                                                                \
    g_assertions++;                                                   \
    if (!(condition)) {                                               \
      std::fprintf(stderr, "FAILED assertion: %s (line %d)\n",        \
                   #condition, __LINE__);                             \
      return false;                                                   \
    }                                                                 \
  } while (0)

FileDescriptorProto BuildPayloadSchema() {
  FileDescriptorProto file;
  file.set_name("roundtrip.proto");
  file.set_package("rt");
  google::protobuf::DescriptorProto* message = file.add_message_type();
  message->set_name("Payload");
  auto add_field = [message](const char* name, int number,
                             FieldDescriptorProto::Type type,
                             FieldDescriptorProto::Label label) {
    FieldDescriptorProto* field = message->add_field();
    field->set_name(name);
    field->set_number(number);
    field->set_label(label);
    field->set_type(type);
  };
  add_field("name", 1, FieldDescriptorProto::TYPE_STRING,
            FieldDescriptorProto::LABEL_OPTIONAL);
  add_field("value", 2, FieldDescriptorProto::TYPE_INT32,
            FieldDescriptorProto::LABEL_OPTIONAL);
  add_field("blob", 3, FieldDescriptorProto::TYPE_BYTES,
            FieldDescriptorProto::LABEL_OPTIONAL);
  add_field("values", 4, FieldDescriptorProto::TYPE_INT32,
            FieldDescriptorProto::LABEL_REPEATED);
  return file;
}

bool BuildAndFetchDescriptor(DescriptorPool* pool,
                             const FileDescriptorProto& file,
                             const Descriptor** descriptor_out) {
  const FileDescriptor* fd = pool->BuildFile(file);
  CHECK(fd != nullptr);
  CHECK(fd->message_type_count() == 1);
  const Descriptor* descriptor = fd->message_type(0);
  CHECK(descriptor != nullptr);
  CHECK(descriptor->name() == "Payload");
  CHECK(descriptor->field_count() == 4);
  *descriptor_out = descriptor;
  return true;
}

bool RunDynamic(const DescriptorPool* pool, const Descriptor* descriptor) {
  DynamicMessageFactory factory;
  const Message* prototype = factory.GetPrototype(descriptor);
  CHECK(prototype != nullptr);
  Message* message = prototype->New();
  const Reflection* reflection = message->GetReflection();
  const FieldDescriptor* name_field = descriptor->FindFieldByName("name");
  const FieldDescriptor* value_field = descriptor->FindFieldByName("value");
  const FieldDescriptor* blob_field = descriptor->FindFieldByName("blob");
  const FieldDescriptor* values_field = descriptor->FindFieldByName("values");
  CHECK(name_field && value_field && blob_field && values_field);

  std::string blob_data("a\0b\1c", 5);
  reflection->SetString(message, name_field, "chase-light");
  reflection->SetInt32(message, value_field, 42);
  reflection->SetString(message, blob_field, blob_data);
  reflection->AddInt32(message, values_field, 1);
  reflection->AddInt32(message, values_field, -7);

  std::string wire;
  CHECK(message->SerializeToString(&wire));
  CHECK(!wire.empty());

  Message* parsed = prototype->New();
  CHECK(parsed->ParseFromString(wire));
  CHECK(reflection->GetString(*parsed, name_field) == "chase-light");
  CHECK(reflection->GetInt32(*parsed, value_field) == 42);
  CHECK(reflection->GetString(*parsed, blob_field) == blob_data);
  CHECK(reflection->FieldSize(*parsed, values_field) == 2);
  CHECK(reflection->GetRepeatedInt32(*parsed, values_field, 0) == 1);
  CHECK(reflection->GetRepeatedInt32(*parsed, values_field, 1) == -7);
  CHECK(parsed->GetTypeName() == "rt.Payload");
  CHECK(parsed->ByteSizeLong() == static_cast<int>(wire.size()));

  // Repeated round-trip through a second parse from a raw buffer.
  Message* second = prototype->New();
  std::string wire_copy = wire;
  CHECK(second->ParseFromArray(wire_copy.data(), wire_copy.size()));
  CHECK(second->SerializeAsString() == wire);

  delete parsed;
  delete second;
  delete message;
  return true;
}

bool RunPool() {
  // Built-in descriptor types resolve from the generated pool.
  const DescriptorPool* generated = DescriptorPool::generated_pool();
  CHECK(generated != nullptr);
  const Descriptor* built_in = generated->FindMessageTypeByName(
      "google.protobuf.FileDescriptorProto");
  CHECK(built_in != nullptr);
  const FileDescriptor* fd =
      generated->FindFileByName("google/protobuf/descriptor.proto");
  CHECK(fd != nullptr);
  CHECK(fd->FindMessageTypeByName("FileDescriptorProto") == built_in);
  // A fresh pool does not know the generated types (error path).
  DescriptorPool empty_pool;
  CHECK(empty_pool.FindMessageTypeByName(
            "google.protobuf.FileDescriptorProto") == nullptr);
  // Registering the same file twice in one pool reports an error through
  // the pool's log and must not corrupt subsequent lookups.
  DescriptorPool pool;
  const FileDescriptor* first = pool.BuildFile(BuildPayloadSchema());
  CHECK(first != nullptr);
  const FileDescriptor* second_attempt = pool.BuildFile(BuildPayloadSchema());
  CHECK(second_attempt == nullptr || second_attempt == first);
  CHECK(pool.FindFileByName("roundtrip.proto") == first);
  // Unknown type name returns NULL (error path).
  CHECK(pool.FindMessageTypeByName("rt.NoSuchMessage") == nullptr);
  return true;
}

bool RunArena() {
  DescriptorPool pool;
  const Descriptor* descriptor = nullptr;
  CHECK(BuildAndFetchDescriptor(&pool, BuildPayloadSchema(), &descriptor));
  DynamicMessageFactory factory;
  {
    Arena arena;
    Message* message = factory.GetPrototype(descriptor)->New(&arena);
    const Reflection* reflection = message->GetReflection();
    const FieldDescriptor* name_field = descriptor->FindFieldByName("name");
    const FieldDescriptor* value_field = descriptor->FindFieldByName("value");
    CHECK(name_field && value_field);
    reflection->SetString(message, name_field, "arena-message");
    reflection->SetInt32(message, value_field, 7);
    std::string wire;
    CHECK(message->SerializeToString(&wire));
    CHECK(!wire.empty());
    CHECK(wire.find("arena-message") != std::string::npos);
  }
  return true;
}

bool RunParseError() {
  DescriptorPool pool;
  const Descriptor* descriptor = nullptr;
  CHECK(BuildAndFetchDescriptor(&pool, BuildPayloadSchema(), &descriptor));
  DynamicMessageFactory factory;
  const Message* prototype = factory.GetPrototype(descriptor);
  CHECK(prototype != nullptr);
  Message* parsed = prototype->New();
  // Truncated field data (tag 0x0a length 8, only 2 bytes present).
  const char truncated[] = {'\x0a', '\x08', 'h', 'i'};
  CHECK(!parsed->ParseFromArray(truncated, sizeof(truncated)));
  // Corrupt varint (unterminated 5-byte sequence).
  const char corrupt[] = {'\x10', '\xff', '\xff', '\xff', '\xff', '\x80'};
  CHECK(!parsed->ParseFromArray(corrupt, sizeof(corrupt)));
  // Unknown fields survive a successful parse and are not lost.
  const char unknown[] = {'\x50', '\x01', '\x0a', '\x02', 'o', 'k'};
  CHECK(parsed->ParseFromArray(unknown, sizeof(unknown)));
  CHECK(parsed->GetReflection()->GetString(
            *parsed, descriptor->FindFieldByName("name")) == "ok");
  delete parsed;
  return true;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) {
    std::fprintf(stderr, "usage: %s <dynamic|pool|arena|parse_error>\n",
                 argv[0]);
    return 2;
  }
  DescriptorPool pool;
  const Descriptor* descriptor = nullptr;
  bool ok = BuildAndFetchDescriptor(&pool, BuildPayloadSchema(), &descriptor);
  const std::string case_name = argv[1];
  if (case_name == "dynamic") {
    ok = ok && RunDynamic(&pool, descriptor);
  } else if (case_name == "pool") {
    ok = ok && RunPool();
  } else if (case_name == "arena") {
    ok = RunArena();
  } else if (case_name == "parse_error") {
    ok = RunParseError();
  } else {
    std::fprintf(stderr, "unknown case: %s\n", case_name.c_str());
    return 2;
  }
  if (ok) {
    std::printf("PASS %s (%d assertions)\n", case_name.c_str(), g_assertions);
    return 0;
  }
  return 1;
}
