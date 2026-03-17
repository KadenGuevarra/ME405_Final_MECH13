import micropython
import math
from utime import ticks_ms, ticks_diff, sleep_ms

S_WAIT = micropython.const(0)
S_CP0_CP1 = micropython.const(1)
S_BOX_FORWARD_50 = micropython.const(2)
S_BOX_TURN_RIGHT_115_A = micropython.const(3)
S_DRIVE_TO_BUMP = micropython.const(4)
S_BACKUP_200 = micropython.const(5)
S_FORWARD_50_AFTER_BLACK = micropython.const(6)
S_TURN_LEFT_60_AFTER_FORWARD = micropython.const(7)
S_LINE_FOLLOW_1 = micropython.const(8)
S_FORWARD_20_AFTER_WHITE = micropython.const(9)
S_TURN_RIGHT_60_AFTER_WHITE = micropython.const(10)
S_LINE_FOLLOW_2 = micropython.const(11)
S_TURN_LEFT_180_AFTER_WHITE = micropython.const(12)
S_LINE_FOLLOW_3 = micropython.const(13)
S_FINISHED = micropython.const(14)
S_FORWARD_200_FINAL = micropython.const(15)
S_TURN_LEFT_270_FINAL = micropython.const(16)
S_FORWARD_20_AFTER_SPIN = micropython.const(17)


class task_navigator:
    def __init__(self,
                 lineSensor,
                 imu,
                 baseSpeedShare,
                 lineKpShare,
                 lineKiShare,
                 setpointLeft,
                 setpointRight,
                 leftMotorGo,
                 rightMotorGo,
                 sHatShare,
                 psiHatShare,
                 xRShare,
                 yRShare,
                 bumpMaskShare,
                 autoRunShare,
                 bumpAckShare=None):

        self._line = lineSensor
        self._imu = imu

        self._baseSpeed = baseSpeedShare
        self._lineKp = lineKpShare
        self._lineKi = lineKiShare

        self._setL = setpointLeft
        self._setR = setpointRight
        self._goL = leftMotorGo
        self._goR = rightMotorGo

        self._sHat = sHatShare
        self._psiHat = psiHatShare
        self._xR = xRShare
        self._yR = yRShare

        self._bumpMask = bumpMaskShare
        self._bumpAck = bumpAckShare
        self._auto = autoRunShare

        self._state = S_WAIT
        self._s0 = 0.0
        self._psi_ref = 0.0
        self._t_prev = ticks_ms()
        self._i_term = 0.0
        self._last_centroid = 0.0
        self._line_lost_count = 0

        # for large final spin tracking
        self._spin_accum = 0.0
        self._spin_prev_psi = 0.0

        # distances
        self.BOX_FORWARD_DISTANCE = 190.0
        self.BACKUP_DISTANCE = 130.0
        self.FORWARD_AFTER_BLACK_DISTANCE = 50.0
        self.FORWARD_AFTER_WHITE_DISTANCE = 20.0
        self.FORWARD_FINAL_DISTANCE = 195.0
        self.FORWARD_AFTER_SPIN_DISTANCE = 30.0

        # thresholds
        self.LINE_SEEN_THRESH = 0.12
        self.LINE_LOST_COUNT_MIN = 2

        # black detection threshold
        self.BLACK_THRESH = 0.55
        self.BLACK_COUNT_MIN = 5

        # branch preference for final line-follow after 180 turn
        self.LINE3_RIGHT_BIAS = 8.0

        # angles
        self.TURN_RIGHT = math.radians(114.50)
        self.TURN_LEFT_AFTER_FORWARD = math.radians(60.0)
        self.TURN_RIGHT_AFTER_WHITE = math.radians(60.0)
        self.TURN_LEFT_180 = math.radians(180.0)
        self.TURN_LEFT_270 = math.radians(240.0)
        self.TURN_TOL = math.radians(8.0)

        # speeds
        self.V_MIN = -140.0
        self.V_MAX = 140.0
        self.BOX_FORWARD_CMD = 120.0
        self.BACKUP_CMD = 80.0
        self.FORWARD_AFTER_BLACK_CMD = 90.0
        self.FORWARD_AFTER_WHITE_CMD = 90.0
        self.FORWARD_FINAL_CMD = 90.0
        self.FORWARD_AFTER_SPIN_CMD = 90.0
        self.TURN_CMD = 120.0
        self.DRIVE_TO_BUMP_CMD = 120.0
        self.TURN_SETTLE_MS = 120

        print("Navigator task instantiated")

    def _clamp(self, x, lo, hi):
        if x < lo:
            return lo
        if x > hi:
            return hi
        return x

    def _wrap_pi(self, ang):
        while ang > math.pi:
            ang -= 2.0 * math.pi
        while ang < -math.pi:
            ang += 2.0 * math.pi
        return ang

    def _set_speed(self, vL, vR):
        vL = self._clamp(vL, self.V_MIN, self.V_MAX)
        vR = self._clamp(vR, self.V_MIN, self.V_MAX)
        self._setL.put(float(vL))
        self._setR.put(float(vR))

    def _stop(self):
        self._set_speed(0.0, 0.0)

    def _drive_straight(self, cmd):
        self._set_speed(cmd, cmd)

    def _s_hat(self):
        return float(self._sHat.get())

    def _seg_dist(self):
        return self._s_hat() - self._s0

    def _psi_hat(self):
        return float(self._psiHat.get())

    def _heading_err(self, target):
        return self._wrap_pi(target - self._psi_hat())

    def _line_seen(self):
        return self._line.line_seen(self.LINE_SEEN_THRESH)

    def _black_seen(self):
        return self._line.dark_count(self.BLACK_THRESH) >= self.BLACK_COUNT_MIN

    def _enter(self, new_state):
        print("NAV: enter state", new_state)
        self._state = new_state
        self._t_prev = ticks_ms()
        self._i_term = 0.0
        self._line_lost_count = 0

        if new_state in (
            S_CP0_CP1,
            S_BOX_FORWARD_50,
            S_BACKUP_200,
            S_FORWARD_50_AFTER_BLACK,
            S_LINE_FOLLOW_1,
            S_FORWARD_20_AFTER_WHITE,
            S_LINE_FOLLOW_2,
            S_LINE_FOLLOW_3,
            S_FORWARD_200_FINAL,
            S_FORWARD_20_AFTER_SPIN,
        ):
            self._s0 = self._s_hat()

        if new_state == S_TURN_LEFT_270_FINAL:
            self._spin_accum = 0.0
            self._spin_prev_psi = self._psi_hat()

    def _line_follow(self, target_centroid=0.0):
        now = ticks_ms()
        dt = ticks_diff(now, self._t_prev) / 1000
        self._t_prev = now
        if dt <= 0:
            dt = 0.02

        base = float(self._baseSpeed.get())
        kp = float(self._lineKp.get())
        ki = float(self._lineKi.get())

        if self._line_seen():
            centroid = float(self._line.findCentroid())
            self._last_centroid = centroid
        else:
            centroid = self._last_centroid

        error = target_centroid - centroid

        self._i_term += error * dt
        self._i_term = self._clamp(self._i_term, -100, 100)

        turn = kp * error + ki * self._i_term

        left_sp = self._clamp(base + turn, self.V_MIN, self.V_MAX)
        right_sp = self._clamp(base - turn, self.V_MIN, self.V_MAX)

        self._set_speed(left_sp, right_sp)

    def _turn_to_fixed(self, psi_target, turn_cmd):
        err = self._heading_err(psi_target)

        if abs(err) <= self.TURN_TOL:
            self._stop()
            return True

        u = abs(turn_cmd)

        if err > 0:
            self._set_speed(u, -u)
        else:
            self._set_speed(-u, u)

        return False

    def _turn_relative_left(self, target_angle, turn_cmd):
        psi_now = self._psi_hat()
        dpsi = self._wrap_pi(psi_now - self._spin_prev_psi)
        self._spin_prev_psi = psi_now

        self._spin_accum += abs(dpsi)

        if self._spin_accum >= target_angle:
            self._stop()
            return True

        u = abs(turn_cmd)
        self._set_speed(-u, u)
        return False

    def run(self):
        while True:
            auto_on = bool(self._auto.get())

            if self._state == S_WAIT:
                self._stop()

                if auto_on:
                    self._goL.put(1)
                    self._goR.put(1)
                    self._enter(S_CP0_CP1)

            elif self._state == S_CP0_CP1:
                self._line_follow()

                if self._line_seen():
                    self._line_lost_count = 0
                else:
                    self._line_lost_count += 1

                if self._line_lost_count >= self.LINE_LOST_COUNT_MIN:
                    self._enter(S_BOX_FORWARD_50)

            elif self._state == S_BOX_FORWARD_50:
                self._drive_straight(self.BOX_FORWARD_CMD)

                if abs(self._seg_dist()) >= self.BOX_FORWARD_DISTANCE:
                    self._stop()
                    self._psi_ref = self._psi_hat()
                    self._enter(S_BOX_TURN_RIGHT_115_A)

            elif self._state == S_BOX_TURN_RIGHT_115_A:
                target = self._wrap_pi(self._psi_ref + self.TURN_RIGHT)

                if self._turn_to_fixed(target, self.TURN_CMD):
                    sleep_ms(self.TURN_SETTLE_MS)
                    self._enter(S_DRIVE_TO_BUMP)

            elif self._state == S_DRIVE_TO_BUMP:
                self._drive_straight(self.DRIVE_TO_BUMP_CMD)

                if int(self._bumpMask.get()) != 0:
                    self._stop()
                    self._enter(S_BACKUP_200)

            elif self._state == S_BACKUP_200:
                self._drive_straight(-self.BACKUP_CMD)

                if abs(self._seg_dist()) >= self.BACKUP_DISTANCE:
                    self._stop()
                    self._enter(S_FORWARD_50_AFTER_BLACK)

            elif self._state == S_FORWARD_50_AFTER_BLACK:
                self._drive_straight(self.FORWARD_AFTER_BLACK_CMD)

                if abs(self._seg_dist()) >= self.FORWARD_AFTER_BLACK_DISTANCE:
                    self._stop()
                    self._psi_ref = self._psi_hat()
                    self._enter(S_TURN_LEFT_60_AFTER_FORWARD)

            elif self._state == S_TURN_LEFT_60_AFTER_FORWARD:
                target = self._wrap_pi(self._psi_ref - self.TURN_LEFT_AFTER_FORWARD)

                if self._turn_to_fixed(target, self.TURN_CMD):
                    sleep_ms(self.TURN_SETTLE_MS)
                    self._enter(S_LINE_FOLLOW_1)

            elif self._state == S_LINE_FOLLOW_1:
                self._line_follow()

                if self._line_seen():
                    self._line_lost_count = 0
                else:
                    self._line_lost_count += 1

                if self._line_lost_count >= self.LINE_LOST_COUNT_MIN:
                    self._stop()
                    self._enter(S_FORWARD_20_AFTER_WHITE)

            elif self._state == S_FORWARD_20_AFTER_WHITE:
                self._drive_straight(self.FORWARD_AFTER_WHITE_CMD)

                if abs(self._seg_dist()) >= self.FORWARD_AFTER_WHITE_DISTANCE:
                    self._stop()
                    self._psi_ref = self._psi_hat()
                    self._enter(S_TURN_RIGHT_60_AFTER_WHITE)

            elif self._state == S_TURN_RIGHT_60_AFTER_WHITE:
                target = self._wrap_pi(self._psi_ref + self.TURN_RIGHT_AFTER_WHITE)

                if self._turn_to_fixed(target, self.TURN_CMD):
                    sleep_ms(self.TURN_SETTLE_MS)
                    self._enter(S_LINE_FOLLOW_2)

            elif self._state == S_LINE_FOLLOW_2:
                self._line_follow()

                if self._line_seen():
                    self._line_lost_count = 0
                else:
                    self._line_lost_count += 1

                if self._line_lost_count >= self.LINE_LOST_COUNT_MIN:
                    self._stop()
                    self._psi_ref = self._psi_hat()
                    self._enter(S_TURN_LEFT_180_AFTER_WHITE)

            elif self._state == S_TURN_LEFT_180_AFTER_WHITE:
                target = self._wrap_pi(self._psi_ref - self.TURN_LEFT_180)

                if self._turn_to_fixed(target, self.TURN_CMD):
                    sleep_ms(self.TURN_SETTLE_MS)
                    self._enter(S_LINE_FOLLOW_3)

            elif self._state == S_LINE_FOLLOW_3:
                self._line_follow(self.LINE3_RIGHT_BIAS)

                if self._line_seen():
                    self._line_lost_count = 0
                else:
                    self._line_lost_count += 1

                if self._line_lost_count >= self.LINE_LOST_COUNT_MIN:
                    self._stop()
                    self._enter(S_FORWARD_200_FINAL)

            elif self._state == S_FORWARD_200_FINAL:
                self._drive_straight(self.FORWARD_FINAL_CMD)

                if abs(self._seg_dist()) >= self.FORWARD_FINAL_DISTANCE:
                    self._stop()
                    self._enter(S_TURN_LEFT_270_FINAL)

            elif self._state == S_TURN_LEFT_270_FINAL:
                if self._turn_relative_left(self.TURN_LEFT_270, self.TURN_CMD):
                    sleep_ms(self.TURN_SETTLE_MS)
                    self._enter(S_FORWARD_20_AFTER_SPIN)

            elif self._state == S_FORWARD_20_AFTER_SPIN:
                self._drive_straight(self.FORWARD_AFTER_SPIN_CMD)

                if abs(self._seg_dist()) >= self.FORWARD_AFTER_SPIN_DISTANCE:
                    self._stop()
                    self._enter(S_FINISHED)

            elif self._state == S_FINISHED:
                self._stop()
                self._goL.put(0)
                self._goR.put(0)
                self._auto.put(0)

            yield self._state