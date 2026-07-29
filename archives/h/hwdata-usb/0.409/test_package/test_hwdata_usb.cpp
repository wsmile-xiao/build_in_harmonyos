#include <cctype>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <string>

static bool is_hex4(const std::string& value)
{
    if (value.size() != 4)
        return false;
    for (std::string::const_iterator it = value.begin(); it != value.end(); ++it)
    {
        if (!std::isxdigit(static_cast<unsigned char>(*it)))
            return false;
    }
    return true;
}

int main(int argc, char** argv)
{
    if (argc == 3 && std::string(argv[1]) == "--expect-missing")
    {
        std::ifstream missing(argv[2]);
        if (missing.is_open())
        {
            std::cerr << "fault path unexpectedly opened\n";
            return 1;
        }
        std::cout << "missing USB database rejected\n";
        return 0;
    }
    const char* usb_ids = NULL;
    if (argc == 1)
    {
        usb_ids = std::getenv("USB_IDS_FILE");
        if (usb_ids == NULL || usb_ids[0] == '\0')
        {
            std::cerr << "USB_IDS_FILE is not available in the run environment\n";
            return 2;
        }
    }
    else if (argc == 2)
    {
        usb_ids = argv[1];
    }
    else
    {
        std::cerr << "usage: test_hwdata_usb [usb.ids]\n";
        return 2;
    }

    std::ifstream input(usb_ids);
    if (!input)
    {
        std::cerr << "cannot open packaged usb.ids\n";
        return 3;
    }

    std::map<std::string, std::string> vendors;
    std::map<std::string, std::set<std::string> > products;
    std::string current_vendor;
    std::string previous_vendor;
    std::string previous_product;
    std::string line;
    std::size_t product_count = 0;

    while (std::getline(input, line))
    {
        if (!line.empty() && line.back() == '\r')
            line.pop_back();
        if (line.size() >= 6 && line[0] != '\t' && is_hex4(line.substr(0, 4)) &&
            std::isspace(static_cast<unsigned char>(line[4])))
        {
            current_vendor = line.substr(0, 4);
            if (!previous_vendor.empty() && current_vendor <= previous_vendor)
            {
                std::cerr << "vendor IDs are not strictly ordered\n";
                return 4;
            }
            vendors[current_vendor] = line.substr(6);
            previous_vendor = current_vendor;
            previous_product.clear();
        }
        else if (line.size() >= 7 && line[0] == '\t' &&
                 is_hex4(line.substr(1, 4)) &&
                 std::isspace(static_cast<unsigned char>(line[5])) &&
                 !current_vendor.empty())
        {
            const std::string product = line.substr(1, 4);
            if (!previous_product.empty() && product <= previous_product)
            {
                std::cerr << "product IDs are not strictly ordered within vendor "
                          << current_vendor << "\n";
                return 5;
            }
            products[current_vendor].insert(product);
            previous_product = product;
            ++product_count;
        }
    }

    if (vendors.size() < 3000 || product_count < 20000)
    {
        std::cerr << "USB database is unexpectedly small\n";
        return 6;
    }
    if (vendors["1d6b"].find("Linux Foundation") == std::string::npos)
    {
        std::cerr << "Linux Foundation vendor record is absent\n";
        return 7;
    }
    if (products["1d6b"].count("0002") != 1 ||
        products["1d6b"].count("0003") != 1)
    {
        std::cerr << "known Linux root-hub products are absent\n";
        return 8;
    }
    if (vendors.count("fffe") != 0)
    {
        std::cerr << "negative vendor lookup unexpectedly matched\n";
        return 9;
    }

    std::cout << "hwdata-usb semantic checks passed\n";
    return 0;
}
