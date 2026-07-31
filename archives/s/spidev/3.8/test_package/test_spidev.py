#!/usr/bin/env python3
import spidev


assert getattr(spidev, "__version__", None) == "3.8"
assert hasattr(spidev, "SpiDev")

spi = spidev.SpiDev()
assert hasattr(spi, "open")
assert hasattr(spi, "open_path")
assert hasattr(spi, "xfer2")
