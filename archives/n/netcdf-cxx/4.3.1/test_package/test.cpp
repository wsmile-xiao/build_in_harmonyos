#include <netcdf>
#include <iostream>

using namespace netCDF;
using namespace netCDF::exceptions;

int main() {
    try {
        NcFile dataFile("test.nc", NcFile::replace);
        if (dataFile.isNull()) {
            std::cerr << "FAIL: NcFile is null" << std::endl;
            return 1;
        }
        std::cout << "OK: netCDF C++ library test passed" << std::endl;
        return 0;
    } catch (NcException& e) {
        std::cerr << "FAIL: NcException: " << e.what() << std::endl;
        return 1;
    }
}
