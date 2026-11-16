import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch


class ConnectorHapticTests(unittest.TestCase):
    def test_runs_three_pwm_pulses_on_bcm18_and_stops(self):
        device = MagicMock()
        factory = MagicMock()
        pwm = MagicMock()
        pwm.return_value.__enter__.return_value = device
        gpiozero = SimpleNamespace(PWMOutputDevice=pwm)
        lgpio = SimpleNamespace(LGPIOFactory=factory)
        legacy_driver = SimpleNamespace(DRV2605=MagicMock())
        with patch.dict(sys.modules, {'gpiozero': gpiozero, 'gpiozero.pins.lgpio': lgpio,
                                      'drv2605': legacy_driver}), \
             patch.object(sys, 'argv', ['pi_haptic.py', '3', '55']), \
             patch('time.sleep') as delay:
            import pi_haptic
            try:
                pi_haptic.main()
            except SystemExit as error:
                self.fail(f'55 is a valid PWM percentage, got exit {error.code}')

        pwm.assert_called_once_with(18, initial_value=0, frequency=200,
                                    pin_factory=factory.return_value)
        self.assertEqual(device.method_calls, [call.off()] * 4)
        self.assertEqual(delay.call_args_list, [call(.18), call(.28)] * 3)
        legacy_driver.DRV2605.assert_not_called()


if __name__ == '__main__':
    unittest.main()
