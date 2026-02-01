; Laser Cutter - Header Template
; Customize this file for your machine's startup sequence.
;
; Common additions:
; - Turn on water cooling, air assist, ventilation
; - Home the machine
; - Set safe starting parameters
;
; FluidNC supports $HTTP= commands for IoT integration (e.g. Home Assistant):
;   $HTTP=http://192.168.1.100/api/laser/cooling/on

G21         ; Set units to millimeters
G90         ; Absolute positioning
M5 S0       ; Ensure laser is off
G0 F6000    ; Set rapid travel speed (mm/min)
G1 F1000    ; Set default cutting speed (mm/min)
