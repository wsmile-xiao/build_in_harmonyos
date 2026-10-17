// test_package for boost1.84-serialization — 实质测试 Boost.Serialization API
// （R34：真实执行 text/binary/xml 三种归档的序列化 round-trip，非空壳测试）
#include <boost/archive/text_oarchive.hpp>
#include <boost/archive/text_iarchive.hpp>
#include <boost/archive/binary_oarchive.hpp>
#include <boost/archive/binary_iarchive.hpp>
#include <boost/archive/xml_oarchive.hpp>
#include <boost/archive/xml_iarchive.hpp>
#include <boost/serialization/nvp.hpp>
#include <boost/serialization/vector.hpp>
#include <boost/serialization/map.hpp>
#include <boost/serialization/string.hpp>
#include <iostream>
#include <sstream>
#include <vector>
#include <map>
#include <string>

struct Record {
    int id;
    std::string name;
    std::vector<double> values;
    std::map<std::string, int> index;

    template <class Archive>
    void serialize(Archive &ar, const unsigned int) {
        ar & BOOST_SERIALIZATION_NVP(id)
           & BOOST_SERIALIZATION_NVP(name)
           & BOOST_SERIALIZATION_NVP(values)
           & BOOST_SERIALIZATION_NVP(index);
    }
    bool operator==(const Record &o) const {
        return id == o.id && name == o.name && values == o.values && index == o.index;
    }
};

template <class OArch, class IArch>
int round_trip(const Record &in, const char *label) {
    std::ostringstream oss;
    {
        OArch oa(oss);
        oa << BOOST_SERIALIZATION_NVP(in);
    }
    Record out;
    {
        std::istringstream iss(oss.str());
        IArch ia(iss);
        ia >> BOOST_SERIALIZATION_NVP(out);
    }
    if (!(in == out)) {
        std::cerr << label << " round-trip mismatch\n";
        return 1;
    }
    return 0;
}

int main() {
    Record rec;
    rec.id = 42;
    rec.name = "boost1.84-serialization";
    rec.values = {3.14, 2.71, 1.41};
    rec.index = {{"alpha", 1}, {"beta", 2}, {"gamma", 3}};

    int failures = 0;
    failures += round_trip<boost::archive::text_oarchive,
                           boost::archive::text_iarchive>(rec, "text");
    failures += round_trip<boost::archive::binary_oarchive,
                           boost::archive::binary_iarchive>(rec, "binary");
    failures += round_trip<boost::archive::xml_oarchive,
                           boost::archive::xml_iarchive>(rec, "xml");

    if (failures == 0) {
        std::cout << "boost1.84-serialization test_package: ALL PASS (3 archives round-trip)\n";
        return 0;
    }
    std::cerr << failures << " failures\n";
    return 1;
}
