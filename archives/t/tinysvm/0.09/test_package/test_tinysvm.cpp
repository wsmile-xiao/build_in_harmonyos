#include <TinySVM/model.h>

#include <cmath>
#include <cstdlib>
#include <iostream>

namespace {

void require(bool condition, const char *message) {
  if (!condition) {
    std::cerr << "FAILED: " << message << std::endl;
    std::exit(EXIT_FAILURE);
  }
}

}  // namespace

int main(int argc, char **argv) {
  require(argc == 2, "model path argument is required");

  TinySVM::Model model;
  require(model.read(argv[1]) != 0, "installed API can read a trained model");
  require(model.getSVnum() > 0, "model contains support vectors");
  require(model.getTrainingDataSize() == 6, "model records six training examples");

  const double positive = model.classify("1:1.5 2:1.5");
  const double negative = model.classify("1:-1.5 2:-1.5");
  require(std::isfinite(positive), "positive distance is finite");
  require(std::isfinite(negative), "negative distance is finite");
  require(positive > 0.0, "positive sample is classified positive");
  require(negative < 0.0, "negative sample is classified negative");
  require(positive * negative < 0.0, "classification distances have opposite signs");

  std::cout << "TinySVM public API: 9 assertions passed" << std::endl;
  return EXIT_SUCCESS;
}

