// test_wserialization.cpp — boost1.84-wserialization 宽字符序列化往返测试
// 保存结构体到宽字符文本 archive（text_woarchive），再从宽字符文本 archive
// 读回（text_wiarchive），校验数据一致性（R34：实质调用被测包 API）。
#include <boost/archive/text_woarchive.hpp>
#include <boost/archive/text_wiarchive.hpp>
#include <boost/archive/xml_woarchive.hpp>
#include <boost/archive/xml_wiarchive.hpp>
#include <boost/serialization/string.hpp>
#include <boost/serialization/vector.hpp>
#include <boost/serialization/map.hpp>
#include <boost/serialization/nvp.hpp>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <map>

struct Record {
    int id;
    std::wstring name;
    std::vector<int> scores;
    std::map<std::wstring, int> attrs;
    template <class Archive>
    void serialize(Archive &ar, const unsigned int) {
        ar & BOOST_SERIALIZATION_NVP(id);
        ar & BOOST_SERIALIZATION_NVP(name);
        ar & BOOST_SERIALIZATION_NVP(scores);
        ar & BOOST_SERIALIZATION_NVP(attrs);
    }
};

int main() {
    Record out_rec;
    out_rec.id = 42;
    out_rec.name = L"鸿蒙宽字符测试-boost_wserialization";
    out_rec.scores = {95, 87, 100, 73};
    out_rec.attrs = {{L"宽度", 1920}, {L"高度", 1080}};

    // --- 宽字符文本 archive 往返 ---
    std::wostringstream woss;
    {
        boost::archive::text_woarchive oa(woss);
        oa << BOOST_SERIALIZATION_NVP(out_rec);
    }
    if (woss.str().empty()) {
        std::cerr << "text_woarchive: empty output" << std::endl;
        return 1;
    }

    Record in_rec;
    {
        std::wistringstream wiss(woss.str());
        boost::archive::text_wiarchive ia(wiss);
        ia >> BOOST_SERIALIZATION_NVP(in_rec);
    }
    if (in_rec.id != out_rec.id || in_rec.name != out_rec.name) {
        std::cerr << "text_w* round-trip mismatch" << std::endl;
        return 1;
    }
    if (in_rec.scores != out_rec.scores || in_rec.attrs != out_rec.attrs) {
        std::cerr << "text_w* container round-trip mismatch" << std::endl;
        return 1;
    }
    std::cout << "text_woarchive/text_wiarchive round-trip OK (id=" << in_rec.id << ")" << std::endl;

    // --- 宽字符 XML archive 往返 ---
    std::wostringstream xoss;
    {
        boost::archive::xml_woarchive oa(xoss);
        oa << BOOST_SERIALIZATION_NVP(out_rec);
    }
    Record xin_rec;
    {
        std::wistringstream xiss(xoss.str());
        boost::archive::xml_wiarchive ia(xiss);
        ia >> BOOST_SERIALIZATION_NVP(xin_rec);
    }
    if (xin_rec.id != out_rec.id || xin_rec.name != out_rec.name || xin_rec.scores != out_rec.scores) {
        std::cerr << "xml_w* round-trip mismatch" << std::endl;
        return 1;
    }
    std::cout << "xml_woarchive/xml_wiarchive round-trip OK (" << xoss.str().size() << L" wchars)" << std::endl;

    std::cout << "boost_wserialization: all wide-char archive round-trips OK" << std::endl;
    return 0;
}
