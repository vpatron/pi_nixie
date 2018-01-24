#!/usr/bin/python

# The MIT License (MIT)
#
# Copyright (c) 2018 Vince Patron
#
# Permission is hereby granted, free of charge, to any person obtaining 
# a copy of this software and associated documentation files (the 
# "Software"), to deal in the Software without restriction, including 
# without limitation the rights to use, copy, modify, merge, publish, 
# distribute, sublicense, and/or sell copies of the Software, and to 
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be 
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, 
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF 
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY 
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import RPi.GPIO as GPIO


class PiNixie:
    """This handles the nixie tube drivers based on the popular design
    using 74HC595 shift registers. The reference circuit used is the
    'Nixie Tube Module for Arduino v2.0' from nixieclock.org. It has this
    74HC595 shift register bit mapping:
    
    bit15 -- Blue LED, active low
    bit14 -- Red LED, active low
    bit13 -- Green LED, active low
    bit12 -- '1' digit
    bit11 -- '2' digit
    bit10 -- '3' digit
    bit9 -- '4' digit
    bit8 -- '5' digit
    bit7 -- '6' digit
    bit6 -- '7' digit
    bit5 -- '8' digit
    bit4 -- '9' digit
    bit3 -- '0' digit
    bit2 -- Upper dot
    bit1 -- Lower dot
    bit0 -- Not connected
    """
    def __init__(self, pinDATA, pinSHCP, pinSTCP, pinOE, 
            brightness=50, release_on_exit=True):
        """Assign GPIO pins to control the shift-register on the nixie
        board:
        
        pinDATA -- Data pin
        pinSCHP -- Shift clock, shifts on rising edge
        pinSTCP -- Shift store, shifted data stored to output on rising edge
        pinOE -- Output enable, modulated by PWM to control brightness"""
        
        self.pinDATA = pinDATA
        self.pinSHCP = pinSHCP
        self.pinSTCP = pinSTCP
        self.pinOE = pinOE
        self.release_on_exit = release_on_exit
        GPIO.setmode(GPIO.BCM)          # Use Broadcom pin-numbering scheme
        GPIO.setup(pinDATA, GPIO.OUT)
        GPIO.setup(pinSHCP, GPIO.OUT)
        GPIO.setup(pinSTCP, GPIO.OUT)
        GPIO.setup(pinOE, GPIO.OUT)
        self.pwm_freq = 100     # PWM frequency in Hertz
        self.pwm = GPIO.PWM(pinOE, self.pwm_freq)

        # Set Initial state
        self.pwm.start(brightness)
        #GPIO.output(pinOE, GPIO.HIGH)   # OE is active low
        GPIO.output(pinDATA, GPIO.LOW)
        GPIO.output(pinSHCP, GPIO.LOW)
        GPIO.output(pinSTCP, GPIO.LOW)
        
        # Internal tables
        self.color_table = {'b':0b011, 'r':0b101, 'g':0b110, 
           'm':0b001, 'c':0b010, 'y':0b100,
           'k':0b111, 'w':0b000}
        self.colon_table = {' ':0b00, '`':0b10, '.':0b01, ':':0b11}
        self.digit_table = {\
            ' ':0b0000000000, 
            '1':0b1000000000,
            '2':0b0100000000, 
            '3':0b0010000000, 
            '4':0b0001000000,
            '5':0b0000100000, 
            '6':0b0000010000, 
            '7':0b0000001000,
            '8':0b0000000100, 
            '9':0b0000000010,
            '0':0b0000000001 }
        
    def __del__(self):
        self.pwm.stop(0)
        GPIO.output(self.pinOE, GPIO.HIGH)   # OE is active low

        #NOTE: if there are no pull resistors on the IO pins, then
        #releasing the RPi GPIO pins will cause the LEDs and nixie to
        #flicker because random data gets shifted in.
        
        if not self.release_on_exit:
            return
        GPIO.output(self.pinDATA, GPIO.LOW)
        GPIO.output(self.pinSHCP, GPIO.LOW)
        GPIO.output(self.pinSTCP, GPIO.LOW)
        GPIO.cleanup()

    def set_brightness(self, value):
        """Set brightness from 0 to 100 (brightest)."""
        if value >= 0 and value <= 100: 
            # OE is active high so correct duty-cycle by subtracting
            # from 100%
            self.pwm.ChangeDutyCycle(100 - value)

    def _shift_bit(self, data):
        """Shift in one data bit into shift register"""
        GPIO.output(self.pinDATA, data)
        GPIO.output(self.pinSHCP, GPIO.HIGH)
        GPIO.output(self.pinSHCP, GPIO.LOW)

    def _latch_data(self):
        GPIO.output(self.pinSTCP, GPIO.HIGH)
        GPIO.output(self.pinSTCP, GPIO.LOW)

    def _set_1reg(self, data):
        """Shift in the 16 bit data into the shift register."""
        for bit_val in range(15, -1, -1):
            n = 2**bit_val
            if data >= n:
                self._shift_bit(1)
                data -= n
            else:
                self._shift_bit(0)

    def _set_1digit(self, chDigit, chColon, chColor):
        """Set the digit value and color of a nixie. Call this function
        repeatedly to set multiple digits."""
        data = (self.color_table[chColor] << 13) + \
               (self.digit_table[chDigit] << 3) + \
               (self.colon_table[chColon] << 1)
        self._set_1reg(data)
        
    def _find_colon(self, stDef, start):
        """Finds the colon character (either : or ` or .) in stDef 
        starting at the position pointed pointed to by start but before 
        a digit character. Returns ' ' if not found."""
        colon = ' '
        for ch in stDef[start:]:
            if ch in self.digit_table:
                break
            elif ch in self.colon_table:
                colon = ch
        return colon
        

    def set_nixie(self, stDef, debug=False):
        """Scan through stDef and display the string on the nixie digits.
        Example: 'r12:g57.03' will display 12: in red, 57.03 in green."""
        data = 0
        color = 'k'
        digit = ' '
        colon = ' '
        for i, ch in enumerate(stDef):
            if ch != ' ' and ch in self.colon_table:
                continue
            elif ch in self.color_table:
                color = ch
            elif ch in self.digit_table:
                digit = ch
                colon = self._find_colon(stDef, i+1)
                if debug:
                    print('digit={}, colon={}, color={}'.format(digit, colon, color))
                self._set_1digit(chDigit=digit, chColon=colon, chColor=color)
            else:
                raise ValueError('{} in stDef is not valid'.format(ch))
        self._latch_data()

