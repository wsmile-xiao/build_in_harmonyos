#include <cmath>
#include <iostream>

#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>

int main() {
    const glm::vec3 x(1.0f, 2.0f, 3.0f);
    const glm::vec3 y(2.0f, 0.0f, -1.0f);
    const float dot = glm::dot(x, y);
    if (std::fabs(dot - (-1.0f)) > 0.0001f) {
        std::cerr << "unexpected dot product: " << dot << '\n';
        return 1;
    }

    const glm::mat4 identity(1.0f);
    const glm::vec4 transformed = identity * glm::vec4(x, 1.0f);
    if (std::fabs(transformed.x - x.x) > 0.0001f ||
        std::fabs(transformed.y - x.y) > 0.0001f ||
        std::fabs(transformed.z - x.z) > 0.0001f) {
        std::cerr << "identity transform changed the vector\n";
        return 1;
    }

    std::cout << "glm consumer PASS version " << GLM_VERSION_MAJOR << '.'
              << GLM_VERSION_MINOR << '.' << GLM_VERSION_PATCH << '\n';
    return 0;
}
