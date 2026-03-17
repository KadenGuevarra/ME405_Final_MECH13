import pyb

class linesensor:
    def __init__(self, pins: tuple, spacing: float):
        self.pinObjects = []
        self.pinPositions = []
        self.whiteCal = []
        self.blackCal = []
        self.centroid = 0.0
        self.spacing = spacing

        # smoothing buffer
        self._centroid_buffer = []
        self._centroid_bufsize = 5   # tweak between 3..9 for smoother/less-lag

        n = -((len(pins) - 1) / 2)
        for pin in pins:
            currentADC = pyb.ADC(pin)
            self.pinObjects.append(currentADC)
            self.pinPositions.append(self.spacing * n)
            self.whiteCal.append(0)
            self.blackCal.append(1)
            n += 1

    # calibration helpers
    def calwhite(self):
        for i in range(len(self.whiteCal)):
            self.whiteCal[i] = self.pinObjects[i].read()
        print("White cal:", self.whiteCal)

    def calblack(self):
        for i in range(len(self.blackCal)):
            self.blackCal[i] = self.pinObjects[i].read()
        print("Black cal:", self.blackCal)

    def set_calibration(self, white_vals, black_vals):
        self.whiteCal = list(white_vals)
        self.blackCal = list(black_vals)
        print("Line sensor calibration loaded")
        print("White cal:", self.whiteCal)
        print("Black cal:", self.blackCal)

    # raw / calibrated access
    def read_raw(self):
        vals = []
        for adc in self.pinObjects:
            vals.append(adc.read())
        return vals

    def read_calibrated(self):
        vals = []
        for i, pinObject in enumerate(self.pinObjects):
            denom = self.blackCal[i] - self.whiteCal[i]
            if denom == 0:
                currentValue = 0.0
            else:
                currentValue = (pinObject.read() - self.whiteCal[i]) / denom

            if currentValue < 0.0:
                currentValue = 0.0
            elif currentValue > 1.0:
                currentValue = 1.0

            vals.append(currentValue)
        return vals

    # convenience accessor (nice in REPL)
    def get_calibrated(self):
        return self.read_calibrated()

    # strengths / detection
    def line_strength(self):
        vals = self.read_calibrated()
        return max(vals)

    def line_seen(self, thresh=0.12):
        return self.line_strength() >= thresh

    def dark_count(self, thresh=0.55):
        vals = self.read_calibrated()
        count = 0
        for v in vals:
            if v >= thresh:
                count += 1
        return count

    # centroid calculation (returns and stores self.centroid)
    def findCentroid(self):
        pos_times_val = 0.0
        total_val = 0.0

        vals = self.read_calibrated()

        for i, currentValue in enumerate(vals):
            pos_times_val += self.pinPositions[i] * currentValue
            total_val += currentValue

        if total_val != 0:
            # adaptive clamp using spacing and number of sensors
            maxpos = self.spacing * (len(self.pinPositions) - 1) / 2.0
            self.centroid = max(-maxpos, min(pos_times_val / total_val, maxpos))

        return self.centroid

    # smoothed centroid (moving average)
    def findCentroidSmoothed(self):
        c = self.findCentroid()
        buf = self._centroid_buffer
        buf.append(c)
        if len(buf) > self._centroid_bufsize:
            buf.pop(0)
        # average buffer
        avg = sum(buf) / len(buf)
        # store smoothed centroid for external reads
        self.centroid = avg
        return avg

    # convenience: change smoothing buffer size at runtime
    def set_centroid_bufsize(self, n):
        if n < 1:
            n = 1
        self._centroid_bufsize = int(n)
        self._centroid_buffer = self._centroid_buffer[-self._centroid_bufsize:]