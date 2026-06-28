#!/bin/bash
DISPLAY=:1 xinput set-prop 'QDtech MPI1001' 'Coordinate Transformation Matrix' -1 0 1 0 -1 1 0 0 1 &
sleep 1
chromium --kiosk --noerrdialogs --disable-infobars --disable-session-crashed-bubble "$1"
