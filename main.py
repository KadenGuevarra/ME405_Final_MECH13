print("main starting")

from motor_driver import motor_driver
from encoder import encoder
from linesensor_driver import linesensor
from task_motor import task_motor
from task_user import task_user
from task_bump import task_bump
from task_navigator import task_navigator
from task_estimator import task_observer
from bump_sensor import RomiBumpers
from task_start_button import task_start_button

from task_share import Share, Queue, show_all
from cotask import Task, task_list
from gc import collect
from pyb import Pin, I2C
from utime import sleep_ms

from imu_driver import IMU

print("imports done")

# ----------------------------
# Hardware
# ----------------------------
leftMotor = motor_driver(3, 20000, 1, Pin.cpu.B4, Pin.cpu.B5, Pin.cpu.B3)
rightMotor = motor_driver(4, 20000, 1, Pin.cpu.B6, Pin.cpu.A7, Pin.cpu.A6)

leftEncoder = encoder(1, 0xFFFF, 0, Pin.cpu.A9, Pin.cpu.A8)
rightEncoder = encoder(2, 0xFFFF, 0, Pin.cpu.A1, Pin.cpu.A0)

# Known working line sensor order
myLineSensor = linesensor(
    (
        Pin.cpu.C4,
        Pin.cpu.A4,
        Pin.cpu.B0,
        Pin.cpu.C1,
        Pin.cpu.C0,
        Pin.cpu.C2,
        Pin.cpu.C3
    ),
    8
)

RIGHT_BUMP_PINS = (
    Pin.cpu.B15,
    Pin.cpu.B14,
    Pin.cpu.B13
)

LEFT_BUMP_PINS = (
    Pin.cpu.C8,
    Pin.cpu.C6,
    Pin.cpu.C5
)

myBumpers = RomiBumpers(
    right_pins=RIGHT_BUMP_PINS,
    left_pins=LEFT_BUMP_PINS,
    active_low=True,
    debounce_ms=10
)

print("hardware objects done")

# ----------------------------
# I2C / IMU
# ----------------------------
sleep_ms(1500)

Pin('PB8', mode=Pin.ANALOG)
Pin('PB9', mode=Pin.ANALOG)
sleep_ms(50)

Pin('PB8', mode=Pin.ALT_OPEN_DRAIN, pull=Pin.PULL_UP, alt=4)
Pin('PB9', mode=Pin.ALT_OPEN_DRAIN, pull=Pin.PULL_UP, alt=4)
sleep_ms(50)

i2c1 = I2C(1, I2C.CONTROLLER, baudrate=100000)
sleep_ms(200)

scan = []
for _ in range(10):
    scan = i2c1.scan()
    if scan:
        break
    sleep_ms(200)

print("I2C scan:", scan)

if (0x28 not in scan) and (0x29 not in scan):
    raise RuntimeError("BNO055 not found on I2C.")

imu_addr = 0x28 if (0x28 in scan) else 0x29
myIMU = IMU(i2c1, imu_addr)

try:
    myIMU.load_cal_from_file()
    print("IMU calibration loaded from file.")
except Exception:
    print("No IMU calibration file found. Calibrate manually, then save.")
    myIMU.change_mode("NDOF")
    sleep_ms(50)
    while True:
        sys, gyr, acc, mag = myIMU.get_cal_status()
        print("SYS:{} GYR:{} ACC:{} MAG:{}".format(sys, gyr, acc, mag))
        if (sys == 3) and (gyr == 3) and (acc == 3) and (mag == 3):
            print("Calibration complete. Saving.")
            break
        sleep_ms(500)
    myIMU.save_cal_to_file()

myIMU.change_mode("NDOF")
sleep_ms(50)

# ----------------------------
# Shares / Queues
# ----------------------------
leftMotorGo = Share("B", name="Left Motor Go")
rightMotorGo = Share("B", name="Right Motor Go")

gainLeft = Share("f", name="Gain Left")
gainRight = Share("f", name="Gain Right")

setpointLeft = Share("f", name="Left Setpoint")
setpointRight = Share("f", name="Right Setpoint")

baseSpeed = Share("f", name="Base Speed")
lineKp = Share("f", name="Line Kp")
lineKi = Share("f", name="Line Ki")

autoRun = Share("B", name="Auto Run")
stepResponse = Share("B", name="Step Response")
bumpMask = Share("H", name="Bump Mask")
bumpAck = Share("B", name="Bump Ack")

# step-response queues
dataValues_L = Queue("f", 50, name="Data Left")
dataValues_R = Queue("f", 50, name="Data Right")
timeValues_L = Queue("f", 50, name="Time Left")
timeValues_R = Queue("f", 50, name="Time Right")

# motor task outputs
uL = Share("f", name="uL")
uR = Share("f", name="uR")
sL = Share("f", name="sL")
sR = Share("f", name="sR")

# estimator outputs
sHat = Share("f", name="sHat")
psiHat = Share("f", name="psiHat")
xR = Share("f", name="xR")
yR = Share("f", name="yR")

leftMotorGo.put(0)
rightMotorGo.put(0)
autoRun.put(0)
stepResponse.put(0)

# symmetric to start
gainLeft.put(0.20)
gainRight.put(0.20)

# default values before user button press
baseSpeed.put(45.0)
lineKp.put(3.0)
lineKi.put(0.02)

setpointLeft.put(0.0)
setpointRight.put(0.0)

print("shares done")

# ----------------------------
# Tasks
# ----------------------------
leftMotorTask = task_motor(
    leftMotor, leftEncoder,
    leftMotorGo, dataValues_L, timeValues_L,
    gainLeft, setpointLeft, stepResponse,
    uL, sL,
    flip_velocity=True
)

rightMotorTask = task_motor(
    rightMotor, rightEncoder,
    rightMotorGo, dataValues_R, timeValues_R,
    gainRight, setpointRight, stepResponse,
    uR, sR,
    flip_velocity=True
)

bumpTask = task_bump(
    myBumpers,
    bumpMask,
    leftMotorGo=leftMotorGo,
    rightMotorGo=rightMotorGo,
    setpointLeft=setpointLeft,
    setpointRight=setpointRight,
    stepResponse=stepResponse,
    stop_on_bump=False,
    print_on_bump=True,
    bumpAckShare=bumpAck
)

observerTask = task_observer(
    uL, uR, sL, sR, myIMU,
    sHat, psiHat, xR, yR
)

navTask = task_navigator(
    lineSensor=myLineSensor,
    imu=myIMU,
    baseSpeedShare=baseSpeed,
    lineKpShare=lineKp,
    lineKiShare=lineKi,
    setpointLeft=setpointLeft,
    setpointRight=setpointRight,
    leftMotorGo=leftMotorGo,
    rightMotorGo=rightMotorGo,
    sHatShare=sHat,
    psiHatShare=psiHat,
    xRShare=xR,
    yRShare=yR,
    bumpMaskShare=bumpMask,
    autoRunShare=autoRun,
    bumpAckShare=bumpAck
)

userTask = task_user(
    leftMotorGo, rightMotorGo,
    gainLeft, gainRight,
    baseSpeed, lineKp, lineKi,
    setpointLeft, setpointRight,
    myLineSensor,
    autoRun
)

startButtonTask = task_start_button(
    lineSensor=myLineSensor,
    baseSpeedShare=baseSpeed,
    lineKpShare=lineKp,
    lineKiShare=lineKi,
    autoRunShare=autoRun,
    leftMotorGo=leftMotorGo,
    rightMotorGo=rightMotorGo
)

print("tasks created")

task_list.append(Task(
    leftMotorTask.run,
    name="Left Mot. Task",
    priority=2,
    period=20,
    profile=True
))

task_list.append(Task(
    rightMotorTask.run,
    name="Right Mot. Task",
    priority=2,
    period=20,
    profile=True
))

task_list.append(Task(
    bumpTask.run,
    name="Bump Task",
    priority=2,
    period=10,
    profile=False
))

task_list.append(Task(
    observerTask.run,
    name="Observer Task",
    priority=2,
    period=20,
    profile=False
))

task_list.append(Task(
    navTask.run,
    name="Navigator Task",
    priority=2,
    period=20,
    profile=False
))

task_list.append(Task(
    userTask.run,
    name="User Int. Task",
    priority=2,
    period=20,
    profile=False
))

task_list.append(Task(
    startButtonTask.run,
    name="Start Button Task",
    priority=3,
    period=20,
    profile=False
))

collect()
print("scheduler starting")

while True:
    try:
        task_list.rr_sched()

    except KeyboardInterrupt:
        print("Program Terminating")
        try:
            leftMotor.set_effort(0)
            rightMotor.set_effort(0)
        except Exception:
            pass
        leftMotor.disable()
        rightMotor.disable()
        break

print("\n")
print(task_list)
print(show_all())