from motor_driver import motor_driver
from encoder import encoder
from task_share import Share, Queue
from utime import ticks_us, ticks_diff
import micropython

S0_INIT = micropython.const(0)
S1_WAIT = micropython.const(1)
S2_RUN = micropython.const(2)


class task_motor:
    def __init__(self,
                 mot: motor_driver, enc: encoder,
                 goFlag: Share, dataValues: Queue, timeValues: Queue,
                 gain: Share, setpoint: Share, stepResponse: Share,
                 effortShare: Share, distanceShare: Share,
                 flip_velocity: bool = True):

        self._state = S0_INIT

        self._mot = mot
        self._enc = enc
        self._goFlag = goFlag
        self._dataValues = dataValues
        self._timeValues = timeValues
        self._startTime = 0
        self._gain = gain
        self._setpoint = setpoint
        self._stepResponse = stepResponse
        self._effortShare = effortShare
        self._distanceShare = distanceShare
        self._flip_velocity = flip_velocity

        print("Motor Task object instantiated")

    def _sat_effort(self, u):
        if u > 100.0:
            return 100.0
        if u < -100.0:
            return -100.0
        return u

    def run(self):
        while True:

            if self._state == S0_INIT:
                self._enc.zero()
                self._mot.disable()
                self._mot.set_effort(0)
                self._effortShare.put(0.0)
                self._distanceShare.put(0.0)
                self._state = S1_WAIT

            elif self._state == S1_WAIT:
                self._mot.disable()
                self._mot.set_effort(0)
                self._enc.update()
                self._effortShare.put(0.0)
                self._distanceShare.put(float(self._enc.get_position()))
                if self._goFlag.get():
                    self._startTime = ticks_us()
                    self._state = S2_RUN

            elif self._state == S2_RUN:

                if not self._goFlag.get():
                    self._mot.disable()
                    self._mot.set_effort(0)
                    self._effortShare.put(0.0)
                    self._state = S1_WAIT
                    yield self._state
                    continue

                self._enc.update()
                raw_vel = self._enc.get_velocity()
                vel = -raw_vel if self._flip_velocity else raw_vel

                sp = float(self._setpoint.get())
                k = float(self._gain.get())

                err = sp - vel
                u = self._sat_effort(err * k)

                self._mot.enable()
                self._mot.set_effort(u)

                self._effortShare.put(float(u))
                self._distanceShare.put(float(self._enc.get_position()))

                if self._stepResponse.get():
                    t = ticks_us()
                    self._dataValues.put(float(vel))
                    self._timeValues.put(float(ticks_diff(t, self._startTime)) / 1_000_000)

                    if self._dataValues.full():
                        self._stepResponse.put(False)
                        self._goFlag.put(False)
                        self._mot.disable()
                        self._state = S1_WAIT

            yield self._state