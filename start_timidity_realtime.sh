#!/bin/sh
nice -20 ionice -c 1 -n 7 timidity --realtime-priority=100 -iA -B2,8 -Os1l -s 44100
