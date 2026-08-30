#include <eigenpy/version.hpp>

#include <iostream>
#include <stdexcept>
#include <string>

static void require(bool condition, const std::string& message) {
  if (!condition) {
    throw std::runtime_error(message);
  }
}

int main() {
  const std::string version = eigenpy::printVersion();
  require(version == "3.13.0", "unexpected eigenpy version: " + version);

  require(eigenpy::checkVersionAtLeast(3, 13, 0),
          "checkVersionAtLeast(3, 13, 0) failed");
  require(!eigenpy::checkVersionAtLeast(3, 14, 0),
          "checkVersionAtLeast(3, 14, 0) unexpectedly passed");
  require(!eigenpy::checkVersionAtLeast(4, 0, 0),
          "checkVersionAtLeast(4, 0, 0) unexpectedly passed");

  const std::string eigen_version = eigenpy::printEigenVersion();
  require(!eigen_version.empty(), "empty Eigen version");

  std::cout << "eigenpy " << version << " built with Eigen " << eigen_version
            << std::endl;
  return 0;
}
