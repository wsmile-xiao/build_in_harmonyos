// Real consumer test for the installed ONNX C++ API (R34).
#include <onnx/onnx_pb.h>

#include <iostream>
#include <string>

int main() {
  onnx::ModelProto model;
  model.set_ir_version(10);
  model.set_producer_name("ohos-onnx-consumer");
  model.add_opset_import()->set_version(20);

  onnx::GraphProto *graph = model.mutable_graph();
  graph->set_name("g");
  graph->add_input()->set_name("x");
  graph->add_output()->set_name("y");
  onnx::NodeProto *node = graph->add_node();
  node->set_op_type("Identity");
  node->add_input("x");
  node->add_output("y");

  std::string wire;
  if (!model.SerializeToString(&wire)) {
    std::cout << "serialize failed" << std::endl;
    return 1;
  }
  onnx::ModelProto back;
  if (!back.ParseFromString(wire)) {
    std::cout << "parse failed" << std::endl;
    return 2;
  }
  if (back.ir_version() != 10) return 3;
  if (back.graph().node_size() != 1) return 4;
  if (back.graph().node(0).op_type() != "Identity") return 5;
  if (back.opset_import_size() != 1 || back.opset_import(0).version() != 20) return 6;
  std::cout << "onnx consumer ok: ir=" << back.ir_version()
            << " nodes=" << back.graph().node_size()
            << " opset=" << back.opset_import(0).version() << std::endl;
  return 0;
}
