import numpy as np

import eigenpy


assert eigenpy.__version__ == "3.13.0", eigenpy.__version__
assert eigenpy.checkVersionAtLeast(3, 13, 0)
assert not eigenpy.checkVersionAtLeast(3, 14, 0)

identity = np.eye(2)
perturbed = identity.copy()
perturbed[0, 0] += 1e-12
different = identity * 2.0

assert eigenpy.is_approx(identity, perturbed)
assert not eigenpy.is_approx(identity, different)
