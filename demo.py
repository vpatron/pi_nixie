#!/usr/bin/python
# Demonstrates the use of the pi_nixie module

import pi_nixie
import time
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-s', default='', help='string template that describes data to display')
args = parser.parse_args()
print(args.s)

nixie = pi_nixie.PiNixie(pinDATA=25, pinSHCP=23, pinSTCP=24, pinOE=18)
nixie.set_brightness(50)

if args.s != '':
    nixie.set_nixie(args.s, debug=True)

else:
    patterns = ['4.4', 'g55.', 'r1b:2', 'm8.9', 'b3`3`', 'y63`', '  r66']
    for pattern in patterns:
        print('Definition={}'.format(pattern))
        start = time.time()
        nixie.set_nixie(pattern, debug=True)
        print('Took {:.3f} ms\n'.format(1000*(time.time() - start)))
        time.sleep(1.0)
