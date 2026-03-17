from pyb import USB_VCP
import micropython

S0_INIT = micropython.const(0)
S1_CMD = micropython.const(1)
S2_SET = micropython.const(2)
S3_CALW = micropython.const(3)
S4_CALB = micropython.const(4)

HELP_MENU = (
    "\r\n+------------------------------------------------------------------------------+\r\n"
    "| ME 405 Romi Mission Interface                                                |\r\n"
    "+---+--------------------------------------------------------------------------+\r\n"
    "| h | Print help menu                                                          |\r\n"
    "| c | Calibrate line sensor                                                    |\r\n"
    "| m | Start mission                                                            |\r\n"
    "| x | Stop mission                                                             |\r\n"
    "| s | Set base speed                                                           |\r\n"
    "| p | Set line Kp                                                              |\r\n"
    "| i | Set line Ki                                                              |\r\n"
    "| l | Set left motor gain                                                      |\r\n"
    "| r | Set right motor gain                                                     |\r\n"
    "| k | Set both motor gains                                                     |\r\n"
    "+---+--------------------------------------------------------------------------+\r\n"
)

TERMINATORS = {"\r", "\n"}
DIGITS = set("0123456789.-")


class task_user:
    def __init__(self,
                 leftMotorGo, rightMotorGo,
                 gainLeft, gainRight,
                 baseSpeed, lineKp, lineKi,
                 setpointLeft, setpointRight,
                 lineSensor,
                 autoRunShare):

        self._ser = USB_VCP()

        self._leftMotorGo = leftMotorGo
        self._rightMotorGo = rightMotorGo
        self._gainL = gainLeft
        self._gainR = gainRight
        self._baseSpeed = baseSpeed
        self._lineKp = lineKp
        self._lineKi = lineKi
        self._setpointLeft = setpointLeft
        self._setpointRight = setpointRight
        self._lineSensor = lineSensor
        self._autoRun = autoRunShare

        self._state = S0_INIT
        self._setting_key = None
        self._char_buf = ""

        print("User Task object instantiated")

    def _println(self, text=""):
        self._ser.write(text + "\r\n")

    def _flush_input(self):
        while self._ser.any():
            self._ser.read(1)

    def _read_cmd_char(self):
        while self._ser.any():
            ch = self._ser.read(1)
            if not ch:
                return None
            try:
                s = ch.decode()
            except:
                continue
            if s in TERMINATORS:
                continue
            return s.lower()
        return None

    def _read_number(self):
        while self._ser.any():
            raw = self._ser.read(1)
            if not raw:
                return None

            try:
                ch = raw.decode()
            except:
                continue

            if ch in ("\x08", "\x7f"):
                if self._char_buf:
                    self._char_buf = self._char_buf[:-1]
                    self._ser.write("\b \b")
                continue

            if ch in TERMINATORS:
                if self._char_buf:
                    try:
                        val = float(self._char_buf)
                    except ValueError:
                        self._println("\r\nInvalid number.")
                        self._char_buf = ""
                        return None
                    self._char_buf = ""
                    return val
                return None

            if ch in DIGITS:
                self._char_buf += ch
                self._ser.write(ch)

        return None

    def _apply_setting(self, value):
        if self._setting_key == "speed":
            self._baseSpeed.put(value)
            self._println("\r\nBase speed set to {}".format(value))

        elif self._setting_key == "kp":
            self._lineKp.put(value)
            self._println("\r\nLine Kp set to {}".format(value))

        elif self._setting_key == "ki":
            self._lineKi.put(value)
            self._println("\r\nLine Ki set to {}".format(value))

        elif self._setting_key == "left_gain":
            self._gainL.put(value)
            self._println("\r\nLeft gain set to {}".format(value))

        elif self._setting_key == "right_gain":
            self._gainR.put(value)
            self._println("\r\nRight gain set to {}".format(value))

        elif self._setting_key == "both_gain":
            self._gainL.put(value)
            self._gainR.put(value)
            self._println("\r\nBoth gains set to {}".format(value))

        self._setting_key = None

    def run(self):
        while True:

            if self._state == S0_INIT:
                self._ser.write(HELP_MENU)
                self._state = S1_CMD

            elif self._state == S1_CMD:
                cmd = self._read_cmd_char()
                if cmd is not None:

                    if cmd == "h":
                        self._state = S0_INIT

                    elif cmd == "c":
                        self._println("Place sensor on WHITE. Press Enter.")
                        self._flush_input()
                        self._state = S3_CALW

                    elif cmd == "m":
                        self._leftMotorGo.put(1)
                        self._rightMotorGo.put(1)
                        self._autoRun.put(1)
                        self._println("Mission started.")
                        self._state = S1_CMD

                    elif cmd == "x":
                        self._autoRun.put(0)
                        self._leftMotorGo.put(0)
                        self._rightMotorGo.put(0)
                        self._setpointLeft.put(0.0)
                        self._setpointRight.put(0.0)
                        self._println("Mission stopped.")
                        self._state = S1_CMD

                    elif cmd == "s":
                        self._println("Enter base speed:")
                        self._setting_key = "speed"
                        self._char_buf = ""
                        self._state = S2_SET

                    elif cmd == "p":
                        self._println("Enter line Kp:")
                        self._setting_key = "kp"
                        self._char_buf = ""
                        self._state = S2_SET

                    elif cmd == "i":
                        self._println("Enter line Ki:")
                        self._setting_key = "ki"
                        self._char_buf = ""
                        self._state = S2_SET

                    elif cmd == "l":
                        self._println("Enter left motor gain:")
                        self._setting_key = "left_gain"
                        self._char_buf = ""
                        self._state = S2_SET

                    elif cmd == "r":
                        self._println("Enter right motor gain:")
                        self._setting_key = "right_gain"
                        self._char_buf = ""
                        self._state = S2_SET

                    elif cmd == "k":
                        self._println("Enter both motor gains:")
                        self._setting_key = "both_gain"
                        self._char_buf = ""
                        self._state = S2_SET

            elif self._state == S2_SET:
                val = self._read_number()
                if val is not None:
                    self._println("")
                    self._apply_setting(val)
                    self._state = S1_CMD

            elif self._state == S3_CALW:
                if self._ser.any():
                    self._ser.read(1)
                    self._lineSensor.calwhite()
                    self._println("White done. Place sensor on BLACK. Press Enter.")
                    self._flush_input()
                    self._state = S4_CALB

            elif self._state == S4_CALB:
                if self._ser.any():
                    self._ser.read(1)
                    self._lineSensor.calblack()
                    self._println("Black done.")
                    self._state = S1_CMD

            yield self._state