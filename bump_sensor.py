from pyb import Pin
import utime


class RomiBumpers:
    def __init__(self,
                 right_pins,
                 left_pins,
                 active_low=True,
                 debounce_ms=10):
        self.active_low = bool(active_low)
        self.debounce_ms = int(debounce_ms)

        self._right = self._init_pin_list(right_pins)
        self._left = self._init_pin_list(left_pins)

        self._raw_r = [self._read_raw(p) for p in self._right]
        self._raw_l = [self._read_raw(p) for p in self._left]

        self._stable_r = self._raw_r[:]
        self._stable_l = self._raw_l[:]

        now = utime.ticks_ms()
        self._tchange_r = [now] * len(self._right)
        self._tchange_l = [now] * len(self._left)

    @staticmethod
    def _init_pin_list(pin_cpu_iterable):
        pins = []
        for cpu_pin in pin_cpu_iterable:
            pins.append(Pin(cpu_pin, mode=Pin.IN, pull=Pin.PULL_UP))
        return pins

    @staticmethod
    def _read_raw(pin_obj):
        return 1 if pin_obj.value() else 0

    def _pressed_from_level(self, level):
        return (level == 0) if self.active_low else (level == 1)

    def update(self):
        now = utime.ticks_ms()

        for i, p in enumerate(self._right):
            raw = self._read_raw(p)
            if raw != self._raw_r[i]:
                self._raw_r[i] = raw
                self._tchange_r[i] = now
            else:
                if utime.ticks_diff(now, self._tchange_r[i]) >= self.debounce_ms:
                    self._stable_r[i] = raw

        for i, p in enumerate(self._left):
            raw = self._read_raw(p)
            if raw != self._raw_l[i]:
                self._raw_l[i] = raw
                self._tchange_l[i] = now
            else:
                if utime.ticks_diff(now, self._tchange_l[i]) >= self.debounce_ms:
                    self._stable_l[i] = raw

    def any(self):
        for x in self._stable_r:
            if self._pressed_from_level(x):
                return True
        for x in self._stable_l:
            if self._pressed_from_level(x):
                return True
        return False

    def bitmask(self):
        mask = 0

        for i, level in enumerate(self._stable_r):
            if self._pressed_from_level(level):
                mask |= (1 << i)

        for i, level in enumerate(self._stable_l):
            if self._pressed_from_level(level):
                mask |= (1 << (8 + i))

        return mask
