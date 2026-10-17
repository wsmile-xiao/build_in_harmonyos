"""Functional consumer test for the packaged aggdraw C++ extension."""
import aggdraw


assert aggdraw.__version__ == "1.4.1", aggdraw.__version__
path = aggdraw.Path()
path.moveto(1, 2)
path.lineto(11, 2)
path.lineto(11, 12)
path.close()
coords = path.coords()
assert len(coords) >= 6, coords
pen = aggdraw.Pen("red", 2.0)
brush = aggdraw.Brush((0, 128, 255), 200)
assert pen is not None and brush is not None
print("aggdraw native Path/Pen/Brush API: PASSED")
