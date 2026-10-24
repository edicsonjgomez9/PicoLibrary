"""
# MysteryGadget.py
# MicroPython engine simulation gadget integrating an LCD display, buzzer, NeoPixel light strip, and potentiometer
# Author: edicsonjgomez9
"""

import time
import sys
try:
    import os
    _parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _parent not in sys.path:
        sys.path.append(_parent)
except Exception:
    pass

for _p in ("..", "/", ""):
    if _p not in sys.path:
        sys.path.append(_p)

from Log import *


class MysteryGadget:
    """
    **MysteryGadget** is a MicroPython gadget that simulates an engine control system.
    
    It integrates an LCD display, a buzzer, a NeoPixel light strip, and a potentiometer
    to deliver audio-visual engine feedback including ignition sound, tachometer light
    visualization, and real-time RPM/speed telemetry.

    Parameters:
    ----------
    display : LCDDisplay
        An LCD display instance supporting `clear()`, `reset()`, and `showText(text, row, col)`.
    buzzer : Buzzer or PassiveBuzzer
        A buzzer instance supporting `play(tone)` and `stop()`.
    light_strip : LightStrip
        A NeoPixel light strip instance supporting `setPixel(index, color, show)`, `show()`, and `off()`.
    potentiometer : AnalogSensor or ADC
        An analog potentiometer input supporting `rawValue()` or `read_u16()`.

    Examples:
    ---------
    1. Basic hardware setup:
       ```python
       from Displays import LCDDisplay
       from Buzzer import PassiveBuzzer
       from LightStrip import LightStrip
       from Sensors import AnalogSensor
       from MysteryGadget import MysteryGadget

       lcd = LCDDisplay(sda=0, scl=1)
       buzzer = PassiveBuzzer(15)
       strip = LightStrip(pin=2, numleds=8)
       pot = AnalogSensor(26)

       gadget = MysteryGadget(lcd, buzzer, strip, pot)
       gadget.start()
       gadget.control(duration=10)
       gadget.stop()
       ```
    """

    IDLE_RPM = 800
    MAX_RPM = 7000
    MAX_SPEED = 120

    def __init__(self, display, buzzer, light_strip, potentiometer):
        """
        Initialize the MysteryGadget with hardware components.

        Parameters:
        ----------
        display : LCDDisplay
            The LCD display object used for telemetry readouts.
        buzzer : Buzzer or PassiveBuzzer
            The buzzer object used for engine sound synthesis.
        light_strip : LightStrip
            The NeoPixel strip object used for tachometer visualization.
        potentiometer : AnalogSensor or ADC
            The analog sensor used for throttle input.

        Examples:
        ---------
        1. Instantiate gadget:
           `gadget = MysteryGadget(display, buzzer, strip, pot)`
        """
        self._display = display
        self._buzzer = buzzer
        self._light_strip = light_strip
        self._potentiometer = potentiometer
        self._running = False
        self._rpm = 0
        self._speed = 0

        # Set maximum volume on buzzer if supported
        if hasattr(self._buzzer, "setVolume"):
            self._buzzer.setVolume(1.0)

        Log.i("MysteryGadget initialized with display, buzzer, light strip, and potentiometer")

    def _read_potentiometer(self):
        """
        Read the raw value from the potentiometer.

        Returns:
        --------
        int
            Raw reading between 0 and 65535.
        """
        if hasattr(self._potentiometer, "rawValue"):
            return self._potentiometer.rawValue()
        elif hasattr(self._potentiometer, "read_u16"):
            return self._potentiometer.read_u16()
        elif callable(self._potentiometer):
            return self._potentiometer()
        return 0

    def _update_tachometer(self, rpm):
        """
        Update the NeoPixel strip to visualize RPM as a tachometer.
        """
        num_leds = getattr(self._light_strip, "_numleds", 8)
        ratio = max(0.0, min(1.0, (rpm - self.IDLE_RPM) / (self.MAX_RPM - self.IDLE_RPM)))
        active_leds = int(round(ratio * num_leds))

        # Tachometer color scale: Green -> Yellow -> Red
        for i in range(num_leds):
            if i < active_leds:
                frac = i / float(num_leds)
                if frac < 0.5:
                    color = (0, 255, 0)       # Green (low RPM)
                elif frac < 0.8:
                    color = (255, 200, 0)     # Yellow (mid RPM)
                else:
                    color = (255, 0, 0)       # Red (high RPM / redline)
                self._light_strip.setPixel(i, color, show=False)
            else:
                self._light_strip.setPixel(i, (0, 0, 0), show=False)

        if hasattr(self._light_strip, "show"):
            self._light_strip.show()

    def start(self):
        """
        Simulate starting the engine.
        
        Emits low frequency cranking and idle sounds on the buzzer, clears the display,
        and presents initial simulated speed and RPM telemetry.

        Parameters:
        ----------
        None

        Examples:
        ---------
        1. Start the engine:
           `gadget.start()`
        """
        Log.i("MysteryGadget: Starting engine...")
        self._running = True
        self._rpm = self.IDLE_RPM
        self._speed = 0

        # Ensure buzzer volume is at maximum
        if hasattr(self._buzzer, "setVolume"):
            self._buzzer.setVolume(1.0)

        # Clear display and show initial values immediately
        self._display.clear()
        self._display.showText(f"RPM:   {self._rpm:<5}", 0, 0)
        self._display.showText(f"Speed: {self._speed:<3} mph", 1, 0)
        self._update_tachometer(self._rpm)

        # Simulate engine starter cranking pulses with audible low-range tones (200-350 Hz)
        crank_pulses = [200, 260, 220, 300, 350]
        for freq in crank_pulses:
            self._buzzer.play(freq)
            time.sleep(0.08)
            self._buzzer.stop()
            time.sleep(0.04)

        # Settle into idle sound (low audible rumble at 220 Hz)
        idle_freq = 220
        self._buzzer.play(idle_freq)

        Log.i(f"MysteryGadget: Engine started at idle ({self._rpm} RPM, {self._speed} mph)")

    def stop(self):
        """
        Stop the engine.
        
        Ceases all buzzer sounds, disables the light strip, and updates the display
        to show "Engine Stopped".

        Parameters:
        ----------
        None

        Examples:
        ---------
        1. Stop the engine:
           `gadget.stop()`
        """
        Log.i("MysteryGadget: Stopping engine...")
        self._running = False
        self._rpm = 0
        self._speed = 0

        # Stop buzzer sounds
        self._buzzer.stop()

        # Turn off light strip
        if hasattr(self._light_strip, "off"):
            self._light_strip.off()

        # Show stopped state on display
        self._display.clear()
        self._display.showText("Engine Stopped", 0, 0)
        Log.i("MysteryGadget: Engine stopped successfully")

    def control(self, duration=None, iterations=None, poll_delay=0.1):
        """
        Monitor the potentiometer and simulate engine throttling.
        
        Reads the potentiometer's raw value, recalculates RPM and speed, adjusts the
        buzzer frequency to match engine revs, visualizes RPM across the NeoPixel light
        strip, and updates the LCD display.

        Parameters:
        ----------
        duration : float, optional
            Duration in seconds to run the control loop (default: None).
        iterations : int, optional
            Number of monitoring cycles to execute. If None, loops continuously while running (default: None).
        poll_delay : float, optional
            Delay in seconds between monitoring cycles (default: 0.1).

        Examples:
        ---------
        1. Continuous monitoring:
           `gadget.control()`
        2. Timed monitoring for 10 seconds:
           `gadget.control(duration=10)`
        3. Finite test monitoring for 20 cycles:
           `gadget.control(iterations=20, poll_delay=0.05)`
        """
        if not self._running:
            Log.w("MysteryGadget: Engine was not started. Starting automatically...")
            self.start()

        Log.i("MysteryGadget: Entering control loop")
        count = 0
        start_time = time.time()
        last_freq = -1

        while self._running:
            raw = self._read_potentiometer()
            # Normalize raw value (typically 0-65535 in MicroPython ADC)
            clamped_raw = max(0, min(65535, raw))
            throttle_ratio = clamped_raw / 65535.0

            # Calculate simulated RPM and speed
            self._rpm = int(self.IDLE_RPM + throttle_ratio * (self.MAX_RPM - self.IDLE_RPM))
            self._speed = int(throttle_ratio * self.MAX_SPEED)

            # Adjust engine sound pitch (220 Hz at idle to 1000 Hz at redline)
            sound_freq = int(220 + throttle_ratio * 780)
            if sound_freq != last_freq:
                self._buzzer.play(sound_freq)
                last_freq = sound_freq

            # Visualize on NeoPixel strip
            self._update_tachometer(self._rpm)

            # Update telemetry on LCD display
            self._display.showText(f"RPM:   {self._rpm:<5}", 0, 0)
            self._display.showText(f"Speed: {self._speed:<3} mph", 1, 0)

            count += 1
            if iterations is not None and count >= iterations:
                break
            if duration is not None and (time.time() - start_time) >= duration:
                break

            time.sleep(poll_delay)

        Log.i("MysteryGadget: Exited control loop")


if __name__ == "__main__":
    Log.i("Starting MysteryGadget self-contained test execution")

    # Mock components for safe verification in desktop test environments
    class MockDisplay:
        def __init__(self):
            self.lines = ["", ""]
        def clear(self, line=-1):
            if line < 0:
                self.lines = ["", ""]
            else:
                self.lines[line] = ""
            Log.i("MockDisplay: cleared")
        def showText(self, text, row=0, col=0):
            self.lines[row] = text
            Log.i(f"MockDisplay [Row {row}]: {text}")

    class MockBuzzer:
        def __init__(self):
            self.current_tone = 0
            self.is_playing = False
        def play(self, tone=500):
            self.current_tone = tone
            self.is_playing = True
            Log.i(f"MockBuzzer: playing tone {tone} Hz")
        def stop(self):
            self.is_playing = False
            Log.i("MockBuzzer: stopped")
        def setVolume(self, volume=1.0):
            Log.i(f"MockBuzzer: volume set to {volume}")

    class MockLightStrip:
        def __init__(self, numleds=8):
            self._numleds = numleds
            self.pixels = [(0, 0, 0)] * numleds
        def setPixel(self, pixelno, color, show=True):
            if 0 <= pixelno < self._numleds:
                self.pixels[pixelno] = color
        def show(self):
            active = sum(1 for p in self.pixels if p != (0, 0, 0))
            Log.i(f"MockLightStrip: updated ({active}/{self._numleds} LEDs active)")
        def off(self):
            self.pixels = [(0, 0, 0)] * self._numleds
            Log.i("MockLightStrip: turned off")

    class MockPotentiometer:
        def __init__(self, values=None):
            self.values = values or [0, 32768, 65535]
            self.index = 0
        def rawValue(self):
            val = self.values[self.index % len(self.values)]
            self.index += 1
            return val

    # 1. Instantiate mock components
    mock_display = MockDisplay()
    mock_buzzer = MockBuzzer()
    mock_strip = MockLightStrip(numleds=8)
    mock_pot = MockPotentiometer(values=[0, 32768, 65535])

    # 2. Instantiate MysteryGadget
    gadget = MysteryGadget(mock_display, mock_buzzer, mock_strip, mock_pot)

    # 3. Test start()
    gadget.start()
    assert gadget._running is True, "Engine should be running after start"
    assert mock_buzzer.is_playing is True, "Buzzer should be playing idle tone"
    assert "RPM" in mock_display.lines[0], "Display row 0 should show RPM"
    assert "Speed" in mock_display.lines[1], "Display row 1 should show Speed"

    # 4. Test control()
    gadget.control(iterations=3, poll_delay=0.01)
    assert gadget._rpm > 0, "RPM should be updated by control loop"

    # 5. Test stop()
    gadget.stop()
    assert gadget._running is False, "Engine should be stopped after stop"
    assert mock_buzzer.is_playing is False, "Buzzer should be stopped"
    assert mock_display.lines[0] == "Engine Stopped", "Display should show Engine Stopped"

    Log.i("Testing complete - all checks passed")
