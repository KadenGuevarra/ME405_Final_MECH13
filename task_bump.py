import micropython
from utime import ticks_ms, ticks_diff

S0_RUN = micropython.const(0)


class task_bump:
    def __init__(self,
                 bump,
                 bumpMaskShare,
                 leftMotorGo=None, rightMotorGo=None,
                 setpointLeft=None, setpointRight=None,
                 stepResponse=None,
                 stop_on_bump=False,
                 print_on_bump=True,
                 min_print_period_ms=250,
                 bumpAckShare=None):          # <- optional ack share
        self._bump = bump
        self._mask = bumpMaskShare
        self._ack = bumpAckShare

        self._leftMotorGo = leftMotorGo
        self._rightMotorGo = rightMotorGo
        self._setpointLeft = setpointLeft
        self._setpointRight = setpointRight
        self._stepResponse = stepResponse

        self._stop_on_bump = bool(stop_on_bump)
        self._print_on_bump = bool(print_on_bump)

        self._latched = False
        self._min_print_ms = int(min_print_period_ms)
        self._t_last_print = ticks_ms()

    def _force_stop(self):
        if self._leftMotorGo is not None:
            self._leftMotorGo.put(0)
        if self._rightMotorGo is not None:
            self._rightMotorGo.put(0)
        if self._stepResponse is not None:
            self._stepResponse.put(0)
        if self._setpointLeft is not None:
            self._setpointLeft.put(0.0)
        if self._setpointRight is not None:
            self._setpointRight.put(0.0)

    def run(self):
        state = S0_RUN

        while True:
            # update hardware first
            self._bump.update()
            hw_mask = int(self._bump.bitmask())

            # if an ack share exists and reads 1, present a cleared mask (0)
            try:
                if self._ack is not None and int(self._ack.get()) == 1:
                    m = 0
                else:
                    m = hw_mask
            except Exception:
                # conservative fallback: if ack not readable, use hw mask
                m = hw_mask

            self._mask.put(m)

            if self._stop_on_bump and m != 0:
                self._force_stop()

            if m != 0:
                if self._print_on_bump and (not self._latched):
                    now = ticks_ms()
                    if ticks_diff(now, self._t_last_print) >= self._min_print_ms:
                        self._t_last_print = now
                        print("BUMP: mask=0x%04X" % m)
                    self._latched = True
            else:
                self._latched = False

            yield state