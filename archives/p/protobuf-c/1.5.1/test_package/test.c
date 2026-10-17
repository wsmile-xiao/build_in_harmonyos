/* Consumer (HarmonyOS-side) test for protobuf-c 1.5.1.

Drives the packaged libprotobuf-c through its public runtime API: version
reporting, ProtobufCBufferSimple growth (the in-library realloc path) and
ProtobufCEnumDescriptor lookups (the in-library binary search).

Counted as 14 cases: CHECK() below is evaluated 14 times at run time. Upstream's
own 11 test programs are executed separately by the recipe's build() phase.
*/

#include <protobuf-c/protobuf-c.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int checks_run;
static int checks_failed;

#define CHECK(cond, what)                                                      \
	do {                                                                   \
		checks_run++;                                                   \
		if (!(cond)) {                                                  \
			checks_failed++;                                         \
			printf("FAIL: %s\n", (what));                           \
		} else {                                                        \
			printf("ok: %s\n", (what));                             \
		}                                                               \
	} while (0)

/* Hand-built, in the exact shape protoc-gen-c emits: values sorted by number,
 * aliases sorted by name, one contiguous range plus the terminating sentinel. */
static const ProtobufCEnumValue color_values[3] = {
	{"ZERO", "V_ZERO", 0},
	{"ONE", "V_ONE", 1},
	{"TWO", "V_TWO", 2}
};

static const ProtobufCEnumValueIndex color_values_by_name[3] = {
	{"ONE", 1},
	{"TWO", 2},
	{"ZERO", 0}
};

static const ProtobufCIntRange color_ranges[2] = {
	{0, 0},
	{0, 3}
};

static const ProtobufCEnumDescriptor color_descriptor = {
	PROTOBUF_C__ENUM_DESCRIPTOR_MAGIC,
	"t.Color",
	"Color",
	"T__Color",
	"t",
	3, color_values,
	3, color_values_by_name,
	1, color_ranges,
	NULL, NULL, NULL, NULL
};

int main(void)
{
	const char *version = protobuf_c_version();
	CHECK(version != NULL && version[0] != '\0', "protobuf_c_version() is usable");
	CHECK(version != NULL && strcmp(version, "1.5.1") == 0, "runtime version is 1.5.1");
	CHECK(PROTOBUF_C_VERSION_NUMBER == 1005001, "PROTOBUF_C_VERSION_NUMBER is 1005001");
	CHECK((unsigned) protobuf_c_version_number() == PROTOBUF_C_VERSION_NUMBER,
	      "protobuf_c_version_number() matches the header");

	uint8_t pad[128];
	ProtobufCBufferSimple simple = PROTOBUF_C_BUFFER_SIMPLE_INIT(pad);
	ProtobufCBuffer *buffer = (ProtobufCBuffer *) &simple;
	const uint8_t head[4] = { 0xde, 0xad, 0xbe, 0xef };

	buffer->append(buffer, sizeof(head), head);
	CHECK(simple.len == sizeof(head), "small append advances len");
	CHECK(memcmp(simple.data, head, sizeof(head)) == 0, "small append copies the bytes");
	CHECK(simple.alloced == sizeof(pad) && simple.data == pad,
	      "small append stays inside the caller's buffer");

	uint8_t big[4096];
	unsigned i;
	for (i = 0; i < sizeof(big); i++)
		big[i] = (uint8_t) (i * 7u + 1u);
	buffer->append(buffer, sizeof(big), big);
	CHECK(simple.len == sizeof(head) + sizeof(big), "oversized append grows len");
	CHECK(simple.must_free_data == 1 && simple.data != pad,
	      "oversized append reallocates and takes ownership");
	CHECK(simple.data[simple.len - 1] == big[sizeof(big) - 1],
	      "grown buffer keeps the tail bytes intact");
	PROTOBUF_C_BUFFER_SIMPLE_CLEAR(&simple);

	const ProtobufCEnumValue *by_number =
		protobuf_c_enum_descriptor_get_value(&color_descriptor, 2);
	CHECK(by_number != NULL && strcmp(by_number->c_name, "V_TWO") == 0,
	      "enum lookup by numeric value hits V_TWO");
	CHECK(protobuf_c_enum_descriptor_get_value(&color_descriptor, 99) == NULL,
	      "enum lookup by numeric value rejects 99");

	const ProtobufCEnumValue *by_name =
		protobuf_c_enum_descriptor_get_value_by_name(&color_descriptor, "ONE");
	CHECK(by_name != NULL && by_name->value == 1, "enum lookup by name hits ONE");
	CHECK(protobuf_c_enum_descriptor_get_value_by_name(&color_descriptor, "NOPE") == NULL,
	      "enum lookup by name rejects an unknown name");

	printf("test_protobuf_c: %d/%d checks passed\n", checks_run - checks_failed, checks_run);
	return checks_failed == 0 ? 0 : 1;
}
