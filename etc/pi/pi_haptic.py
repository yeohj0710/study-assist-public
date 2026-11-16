import argparse
import time

def main():
    parser = argparse.ArgumentParser(description='Grove 진동 모듈 시험 (GPIO18)')
    parser.add_argument('count', type=int, choices=range(1, 6))
    parser.add_argument('strength', type=int, choices=range(25, 101), metavar='25-100')
    args = parser.parse_args()

    from gpiozero import PWMOutputDevice
    from gpiozero.pins.lgpio import LGPIOFactory

    pins = LGPIOFactory()
    try:
        with PWMOutputDevice(18, initial_value=0, frequency=200, pin_factory=pins) as motor:
            try:
                for _ in range(args.count):
                    motor.value = args.strength / 100
                    time.sleep(0.18)
                    motor.off()
                    time.sleep(0.28)
            finally:
                motor.off()
    finally:
        pins.close()


if __name__ == '__main__':
    main()
