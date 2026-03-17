import struct
import math
from utime import sleep_ms


class IMU:
    def __init__(self, i2c, addr):
        """Initialize the IMU with a CONTROLLER-configured pyb.I2C object."""
        self.i2c = i2c
        self.i2c_addr = addr

    def change_mode(self, mode: str):
        """
        Change fusion mode.
        OPR_MODE register = 0x3D
        IMU = 0x08, COMPASS = 0x09, M4G = 0x0A, NDOF_FMC_OFF = 0x0B, NDOF = 0x0C
        """
        if mode == "IMU":
            val = 0x08
        elif mode == "COMPASS":
            val = 0x09
        elif mode == "M4G":
            val = 0x0A
        elif mode == "NDOF_FMC_OFF":
            val = 0x0B
        elif mode == "NDOF":
            val = 0x0C
        else:
            raise ValueError("Unknown IMU mode: {}".format(mode))

        self.i2c.mem_write(val, self.i2c_addr, 0x3D)
        sleep_ms(30)

    def get_cal_status(self):
        """Return calibration status (SYS, GYR, ACC, MAG), each 0..3."""
        buf = bytearray(1)
        self.i2c.mem_read(buf, self.i2c_addr, 0x35)
        sys_cal = (buf[0] >> 6) & 0x03
        gyr_cal = (buf[0] >> 4) & 0x03
        acc_cal = (buf[0] >> 2) & 0x03
        mag_cal = (buf[0] >> 0) & 0x03
        return sys_cal, gyr_cal, acc_cal, mag_cal

    def get_cal_coeff(self):
        """Read 22 bytes of calibration coefficients from 0x55."""
        buf = bytearray(22)
        self.i2c.mem_read(buf, self.i2c_addr, 0x55)
        return struct.unpack("<hhhhhhhhhhh", buf)

    def set_cal_coeff(self, *coeffs):
        """
        Write calibration coefficients (11 int16) to 0x55.
        Recommended: switch to CONFIG mode (0x00), write coeffs, restore previous mode.
        """
        # Read current mode
        lastmode = bytearray(1)
        self.i2c.mem_read(lastmode, self.i2c_addr, 0x3D)
        lastmode_val = lastmode[0] & 0x0F

        # Enter CONFIG mode
        self.i2c.mem_write(0x00, self.i2c_addr, 0x3D)
        sleep_ms(30)

        offsets = struct.pack("<hhhhhhhhhhh", *coeffs)
        self.i2c.mem_write(offsets, self.i2c_addr, 0x55)
        sleep_ms(30)

        # Restore mode
        self.i2c.mem_write(lastmode_val, self.i2c_addr, 0x3D)
        sleep_ms(30)

    def get_euler_angles(self):
        """
        Read Euler angles from 0x1A (6 bytes): heading, roll, pitch.
        Raw units: 1 LSB = 1/16 degree.
        """
        buf = bytearray(6)
        self.i2c.mem_read(buf, self.i2c_addr, 0x1A)
        return struct.unpack("<hhh", buf)

    def get_ang_velocity(self):
        """
        Read gyro from 0x14 (6 bytes): x, y, z.
        Raw units: 1 LSB = 1/16 deg/s (default unit setting).
        """
        buf = bytearray(6)
        self.i2c.mem_read(buf, self.i2c_addr, 0x14)
        return struct.unpack("<hhh", buf)

    # --------- Helpers for Lab 0x06 (units estimator expects) ---------
    def get_yaw_rad(self):
        heading, _, _ = self.get_euler_angles()
        return (heading / 16.0) * math.pi / 180.0

    def get_yaw_rate_rads(self):
        _, _, gz = self.get_ang_velocity()
        return (gz / 16.0) * math.pi / 180.0

    def get_yaw_and_rate(self):
        return self.get_yaw_rad(), self.get_yaw_rate_rads()

    # --------- Calibration file I/O ---------
    def save_cal_to_file(self, filename="calibration.txt"):
        """Read coeffs from IMU and save to a text file."""
        coeffs = self.get_cal_coeff()
        with open(filename, "w") as f:
            f.write(",".join(str(c) for c in coeffs))

    def load_cal_from_file(self, filename="calibration.txt"):
        """Load coeffs from file and write to IMU."""
        with open(filename, "r") as f:
            data = f.read().strip().split(",")
        coeffs = [int(x) for x in data]
        self.set_cal_coeff(*coeffs)