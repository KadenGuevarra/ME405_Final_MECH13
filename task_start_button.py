import pyb


class task_start_button:
    def __init__(self,
                 lineSensor,
                 baseSpeedShare,
                 lineKpShare,
                 lineKiShare,
                 autoRunShare,
                 leftMotorGo,
                 rightMotorGo):

        self._line = lineSensor
        self._baseSpeed = baseSpeedShare
        self._lineKp = lineKpShare
        self._lineKi = lineKiShare
        self._auto = autoRunShare
        self._goL = leftMotorGo
        self._goR = rightMotorGo

        self._button = pyb.Switch()
        self._pressed_latch = False

        self.START_SPEED = 90.0
        self.START_KP = 2.9
        self.START_KI = 0.1

        self.WHITE_CAL = [2155, 2230, 1761, 2167, 1989, 2093, 2143]
        self.BLACK_CAL = [2826, 2721, 2571, 2786, 2648, 2863, 2750]

        print("Start button task instantiated")

    def run(self):
        while True:
            pressed = self._button()

            if pressed and not self._pressed_latch:
                self._baseSpeed.put(self.START_SPEED)
                self._lineKp.put(self.START_KP)
                self._lineKi.put(self.START_KI)

                self._line.set_calibration(self.WHITE_CAL, self.BLACK_CAL)

                self._goL.put(1)
                self._goR.put(1)
                self._auto.put(1)

                print("START BUTTON PRESSED")
                print("baseSpeed =", self.START_SPEED)
                print("lineKp =", self.START_KP)
                print("lineKi =", self.START_KI)
                print("white cal =", self.WHITE_CAL)
                print("black cal =", self.BLACK_CAL)

            self._pressed_latch = pressed
            yield 0