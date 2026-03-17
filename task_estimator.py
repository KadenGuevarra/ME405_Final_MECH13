import math
import utime
import estimator


class task_observer:
    def __init__(self, uL_share, uR_share, sL_share, sR_share, imu,
                 sHatShare, psiHatShare, xRShare, yRShare):
        self.uL = uL_share
        self.uR = uR_share
        self.sL = sL_share
        self.sR = sR_share
        self.imu = imu

        self.sHatShare = sHatShare
        self.psiHatShare = psiHatShare
        self.xRShare = xRShare
        self.yRShare = yRShare

        self.VBATT = 9.0

        self.xR = 0.0
        self.yR = 0.0

        self._inited = False
        self._have_prev_s = False
        self._s_prev = 0.0
        self._t_last_print = utime.ticks_ms()

    def run(self):
        state = 0

        while True:
            effL = float(self.uL.get())
            effR = float(self.uR.get())

            uL_v = (effL / 100.0) * self.VBATT
            uR_v = (effR / 100.0) * self.VBATT

            sL_mm = float(self.sL.get())
            sR_mm = float(self.sR.get())

            psi, dpsi = self.imu.get_yaw_and_rate()
            s_meas = 0.5 * (sL_mm + sR_mm)

            if not self._inited:
                estimator.xhat[0, 0] = s_meas
                estimator.xhat[1, 0] = psi
                estimator.xhat[2, 0] = 0.0
                estimator.xhat[3, 0] = 0.0

                self._s_prev = s_meas
                self._have_prev_s = True
                self._inited = True

            # Keep estimator running for compatibility/diagnostics,
            # but publish raw measured distance and raw yaw to navigation.
            xhat, yhat = estimator.step(uL_v, uR_v, sL_mm, sR_mm, psi, dpsi)

            if not self._have_prev_s:
                self._s_prev = s_meas
                self._have_prev_s = True

            ds = s_meas - self._s_prev
            self._s_prev = s_meas

            self.xR += ds * math.cos(psi)
            self.yR += ds * math.sin(psi)

            self.sHatShare.put(float(s_meas))
            self.psiHatShare.put(float(psi))
            self.xRShare.put(float(self.xR))
            self.yRShare.put(float(self.yR))

            now = utime.ticks_ms()
            if utime.ticks_diff(now, self._t_last_print) > 500:
                self._t_last_print = now
                print("s_hat=%.1f psi_hat=%.3f xR=%.1f yR=%.1f" %
                      (s_meas, psi, self.xR, self.yR))

            yield state