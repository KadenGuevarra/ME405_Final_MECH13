# ME405_Final_MECH13
This is the Repo for Lab group MECH13's Final Source Codes, Report, and Mechanical/Electrical Maps. 
# ME405 Final Project - MECH13

## Project Overview
Romi Final Report and Codes:
This is the final report page that combines all of our source codes along with all of 
The mechanical and electrical decisions we made to make our Romi work as it does. 

## Team Members
Kaden Guevarra, John Tomas

## Project Information
- **Course**: ME405
- **Due Date**: 03/20/2026
- **Project Type**: Final Project

## Table of Contents
1. [Objectives](#objectives)
2. [Design Specifications](#design-specifications)
4. [Results](#results)
5. [Code Documentation](#code-documentation)

## Objectives
The Objective of this Final project was to put together all of the labs that we have done, 
along with some extra sensors, to complete an obstacle course with our Romi Robot. 
Our final Romi robot includes Motors & Encoders, Line sensors, IMU state estimation, and Bump Sensors.
We also have LED lights set up, which do not function in a way that is helpful for the lab. 

## Design Specifications
The mechanical map and electrical map will be described below. 
To build this Romi, we had the starting kit provided by the ME405 Lab, which included the Romi Chassis w/ Motors, Encoders, Wheels, and Casters, BNO055 IMU Breakout Board, Modified Shoe of Brian (w/o Bead or Resistors), and the Nucleo L476RG. We placed these onto our Romi exactly as described in the lab, after constructing it. We added our own QTRX-MD-07A Reflectance Sensor Array (7-Channel, 8mm Pitch, Analog Output, Low Current) and our own Right and Left Bumper Switch Assembly for Romi/TI-RSLK MAX. These were installed on the front of our Romi. The line sensor is installed with stand-offs so that it is right above the ground. The bump sensors were installed in the front of the Romi so that it could bump into the wall without damaging our line sensor. 

We then had to wire all of these into our Nucleo. For this, we created a Common Ground (GND). For the board power, we wired into VIN and GND. For our Motors, we wired the right motor into PA1 and PA0, and our left motor into PA8 and PA9. For our Encoders, we wired our right encoder into PB6, PA7, and PA6. Our left encoder is wired into PB4, PB5, and PB3. We wired our Line sensor into PC3, PC2, PC0, PC1, PB0, PA4, PC4, GND, and 3V3. We wired our IMU into (SCL)PB9, (SDA)PB8, GND, and 3V3. For our bump sensors, we wired the right side into PB15, PB14, and PB13. For the left side, we wired it into PC8, PC6, and PC5.

## Photo Of Romi

(![ROMI PHOTO](https://github.com/user-attachments/assets/59b8538a-9f08-433e-8024-1bff118f0d29)
)

## Wiring Map Excel File 
[Download Raw Data (Excel)](https://cpslo-my.sharepoint.com/:x:/r/personal/ktguevar_calpoly_edu/Documents/FINAL_ROMI_WIRINGMAP.xlsx?d=wce03223d2b894929a85aa045309b94bb&csf=1&web=1&e=eps5Vk)

## Results
During our demonstration, we completed the course 1 out of 3 times. Before the demonstration, we were able to complete it 3 times in a row, but due to some external issues, we had to make some last-minute calibration adjustments. We relied mainly on our line sensor and encoder ticks, with the state estimation only accounting for the turning angles when there was no line to follow. Our fastest course completion time was just under 2 minutes, and our fastest official time was right at the 2-minute mark, which you will see in the video provided below. Some issues we ran into while setting up the Romi for the obstacle course were the use of heading, calibrating state-estimation, and making consistent turns. Since we could not figure out how to properly use our heading, we were unable to guarantee that our Romi would hold a perfectly straight line, with one of our motors consistently running slightly faster than the other. We had trouble with our right motor running faster than our left in multiple labs as well. We account for this; we made our line following very strong, but the problem with that is that when there was no line to follow, it was hard to run perfectly every time. These are some things we would have liked to iron out a little better, provided some more time, but altogether we are proud of how our Romi performed. 

## Video of Romi
[![Watch the video](https://img.youtube.com/vi/V55OzWEsSkU/maxresdefault.jpg)](https://youtu.be/V55OzWEsSkU)

## Code Documentation
- See `/source/` directory for source code files

## Files Structure
Below are all the files you need to flash into a ROMI built to match ours to recreate our project. After flashing all of the classes and the tasks, you want to either run main and follow the user interface to set all of the values. Or to do as we have exactly, you must flash the codes and then, with the use of the user button, it will automatically set all of the premeasured calibration values to run exactly as ours has. 
