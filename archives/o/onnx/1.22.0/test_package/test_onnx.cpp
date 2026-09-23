// Consumer test for ONNX 1.22.0 on HarmonyOS PC.
//
// Asserts:
//  1. The packaged onnx.proto-toolchain headers (onnx/onnx_pb.h) are usable
//     and expose the ONNX IR message types (ModelProto/GraphProto/NodeProto).
//  2. A minimal valid ModelProto (Identity node, FLOAT tensor, opset 13)
//     constructed through the C++ API passes checker::check_model.
//  3. Binary round-trip serialization (SerializeToString/ParseFromString)
//     preserves graph name and node op_type.
//  4. onnx::Version::IR_VERSION is exposed from the generated proto enum.

#include <cstdio>
#include <string>

#include "onnx/checker.h"
#include "onnx/onnx_pb.h"

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

using ONNX_NAMESPACE::ModelProto;
using ONNX_NAMESPACE::TensorProto;
using ONNX_NAMESPACE::Version;

ModelProto MakeMinimalModel() {
    ModelProto model;
    model.set_ir_version(Version::IR_VERSION);
    model.set_producer_name("test_package");
    model.set_producer_version("1.22.0");
    model.set_domain("");
    model.set_model_version(1);

    auto* opset = model.add_opset_import();
    opset->set_domain("");
    opset->set_version(13);

    auto* graph = model.mutable_graph();
    graph->set_name("minimal_graph");

    auto* input = graph->add_input();
    input->set_name("X");
    input->mutable_type()->mutable_tensor_type()->set_elem_type(TensorProto::FLOAT);
    input->mutable_type()->mutable_tensor_type()->mutable_shape()->add_dim()->set_dim_value(1);

    auto* output = graph->add_output();
    output->set_name("Y");
    output->mutable_type()->mutable_tensor_type()->set_elem_type(TensorProto::FLOAT);
    output->mutable_type()->mutable_tensor_type()->mutable_shape()->add_dim()->set_dim_value(1);

    auto* node = graph->add_node();
    node->set_op_type("Identity");
    node->add_input("X");
    node->add_output("Y");

    return model;
}

}  // namespace

int main() {
    // IR_VERSION enum from the generated onnx.proto toolchain output.
    CHECK_TRUE(Version::IR_VERSION >= 9);

    ModelProto model = MakeMinimalModel();
    CHECK_TRUE(model.ir_version() == Version::IR_VERSION);
    CHECK_TRUE(model.graph().name() == "minimal_graph");
    CHECK_TRUE(model.graph().node_size() == 1);
    CHECK_TRUE(model.graph().node(0).op_type() == "Identity");

    // checker validation must pass for a well-formed minimal model.
    ONNX_NAMESPACE::checker::check_model(model);

    // Binary round-trip.
    std::string bytes;
    CHECK_TRUE(model.SerializeToString(&bytes));
    CHECK_TRUE(!bytes.empty());
    ModelProto parsed;
    CHECK_TRUE(parsed.ParseFromString(bytes));
    CHECK_TRUE(parsed.graph().name() == "minimal_graph");
    CHECK_TRUE(parsed.graph().node(0).op_type() == "Identity");
    CHECK_TRUE(parsed.opset_import(0).version() == 13);

    std::printf("test_onnx: all %d checks passed\n", checks);
    return 0;
}
