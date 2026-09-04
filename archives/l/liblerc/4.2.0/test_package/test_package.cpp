#include <iostream>
#include <vector>
#include <cstring>
#include <cmath>
#include <Lerc_c_api.h>

int main() {
    std::cout << "Testing liblerc " 
              << LERC_VERSION_MAJOR << "." 
              << LERC_VERSION_MINOR << "." 
              << LERC_VERSION_PATCH << std::endl;
    
    // Create a simple 10x10 image with float data
    const int nRows = 10;
    const int nCols = 10;
    const int nBands = 1;
    const int nDepth = 1;
    
    std::vector<float> data(nRows * nCols);
    for (int i = 0; i < nRows * nCols; i++) {
        data[i] = static_cast<float>(i) + 0.5f;  // Use non-integer values to test float compression
    }
    
    // Compute compressed size
    unsigned int numBytesNeeded = 0;
    double maxZError = 0.01;  // allow small compression error
    
    lerc_status status = lerc_computeCompressedSize(
        (void*)data.data(),
        6,  // dataType: 6 = float (dt_float in LERC)
        nDepth,
        nCols,
        nRows,
        nBands,
        0,  // nMasks
        nullptr,  // pValidBytes
        maxZError,
        &numBytesNeeded
    );
    
    if (status != 0) {
        std::cerr << "lerc_computeCompressedSize failed with status: " << status << std::endl;
        return 1;
    }
    
    std::cout << "Compressed size: " << numBytesNeeded << " bytes" << std::endl;
    
    // Allocate buffer and encode
    std::vector<unsigned char> compressed(numBytesNeeded);
    unsigned int numBytesWritten = 0;
    
    status = lerc_encode(
        (void*)data.data(),
        6,  // dataType: 6 = float (dt_float in LERC)
        nDepth,
        nCols,
        nRows,
        nBands,
        0,  // nMasks
        nullptr,  // pValidBytes
        maxZError,
        compressed.data(),
        numBytesNeeded,
        &numBytesWritten
    );
    
    if (status != 0) {
        std::cerr << "lerc_encode failed with status: " << status << std::endl;
        return 1;
    }
    
    std::cout << "Encoded " << numBytesWritten << " bytes" << std::endl;
    
    // Decode to verify
    std::vector<float> decoded(nRows * nCols);
    
    status = lerc_decode(
        compressed.data(),
        numBytesWritten,
        0,  // nMasks
        nullptr,  // pValidBytes
        nDepth,
        nCols,
        nRows,
        nBands,
        6,  // dataType: 6 = float (dt_float in LERC)
        (void*)decoded.data()
    );
    
    if (status != 0) {
        std::cerr << "lerc_decode failed with status: " << status << std::endl;
        return 1;
    }
    
    // Verify all values (not just first 5)
    bool success = true;
    for (int i = 0; i < nRows * nCols; i++) {
        float diff = std::fabs(data[i] - decoded[i]);
        if (diff > maxZError) {
            std::cerr << "Data mismatch at index " << i 
                      << ": original=" << data[i] 
                      << ", decoded=" << decoded[i] 
                      << ", diff=" << diff << std::endl;
            success = false;
        }
    }
    
    if (success) {
        std::cout << "liblerc test PASSED! All " << (nRows * nCols) << " float values verified." << std::endl;
        return 0;
    } else {
        std::cerr << "liblerc test FAILED!" << std::endl;
        return 1;
    }
}
