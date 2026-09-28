#include <gav1/decoder.h>

int main() {
    libgav1::Decoder decoder;
    libgav1::DecoderSettings settings;
    return decoder.Init(&settings) == libgav1::kStatusOk ? 0 : 1;
}
