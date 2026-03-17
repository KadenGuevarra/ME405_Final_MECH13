# estimator.py
from ulab import numpy as np

Ad = np.array([
    [0.7427, 0.0,    0.2494, 0.2494],
    [0.0,    0.1466, 0.0,    0.0   ],
    [-0.1212,0.0,    0.4153, 0.2134],
    [-0.1212,0.0,    0.2134, 0.4153],
])

Bd = np.array([
    [0.1962, 0.1962,  0.1287, 0.1287,  0.0,     0.0   ],
    [0.0,    0.0,    -0.0061, 0.0061,  0.0001,  0.0089],
    [0.9128, 0.2165,  0.0606, 0.0606,  0.0,    -1.1972],
    [0.2165, 0.9128,  0.0606, 0.0606,  0.0,     1.1972],
])

Cd = np.array([
    [1.0, -70.0, 0.0,   0.0 ],
    [1.0,  70.0, 0.0,   0.0 ],
    [0.0,   1.0, 0.0,   0.0 ],
    [0.0,   0.0, -0.25, 0.25],
])

# state estimate column vector
xhat = np.zeros((4, 1))

def step(uL, uR, sL, sR, psi, dpsi):
    """xhat_{k+1} = Ad*xhat_k + Bd*[uL uR sL sR psi dpsi]^T"""
    global xhat
    ustar = np.array([[uL],[uR],[sL],[sR],[psi],[dpsi]])
    xhat = np.dot(Ad, xhat) + np.dot(Bd, ustar)
    yhat = np.dot(Cd, xhat)   # optional
    return xhat, yhat