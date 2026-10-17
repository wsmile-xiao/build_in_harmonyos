#include <cereal/archives/binary.hpp>
#include <cereal/types/string.hpp>
#include <cereal/types/vector.hpp>

#include <sstream>
#include <string>
#include <vector>

struct Snapshot {
    int id{};
    std::string label;
    std::vector<int> samples;

    template <class Archive>
    void serialize(Archive& archive) {
        archive(id, label, samples);
    }
};

int main() {
    const Snapshot original{42, "ohos-cereal", {1, 3, 5, 8, 13}};
    std::stringstream stream;

    {
        cereal::BinaryOutputArchive output(stream);
        output(original);
    }

    Snapshot restored;
    {
        cereal::BinaryInputArchive input(stream);
        input(restored);
    }

    if (restored.id != original.id) {
        return 1;
    }
    if (restored.label != original.label) {
        return 2;
    }
    if (restored.samples != original.samples) {
        return 3;
    }
    return 0;
}
