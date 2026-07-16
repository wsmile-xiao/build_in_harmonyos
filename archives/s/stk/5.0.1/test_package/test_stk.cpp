#include <cmath>
#include <iostream>

#include <stk/ADSR.h>
#include <stk/SineWave.h>
#include <stk/Stk.h>

int main() {
  stk::Stk::setSampleRate(44100.0);

  stk::SineWave sine;
  sine.setFrequency(440.0);

  stk::ADSR envelope;
  envelope.setAllTimes(0.001, 0.001, 0.5, 0.001);
  envelope.keyOn();

  double energy = 0.0;
  double peak = 0.0;
  for (int i = 0; i < 256; ++i) {
    const stk::StkFloat sample = sine.tick() * envelope.tick();
    energy += std::abs(sample);
    peak = std::max(peak, static_cast<double>(std::abs(sample)));
  }

  if (stk::Stk::sampleRate() != 44100.0) {
    std::cerr << "Unexpected sample rate: " << stk::Stk::sampleRate() << "\n";
    return 1;
  }
  if (!(energy > 0.01)) {
    std::cerr << "Synthesis energy too low: " << energy << "\n";
    return 1;
  }
  if (!(peak > 0.001 && peak <= 1.0)) {
    std::cerr << "Unexpected sample peak: " << peak << "\n";
    return 1;
  }

  std::cout << "stk synthesis test: energy=" << energy << " peak=" << peak
            << "\n";
  return 0;
}
