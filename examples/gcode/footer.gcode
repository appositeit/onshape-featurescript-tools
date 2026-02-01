; Laser Cutter - Footer Template
; Customize this file for your machine's shutdown sequence.
;
; Common additions:
; - Cooldown delay before turning off cooling
; - Turn off water cooling, air assist, ventilation
;
; FluidNC supports $HTTP= commands for IoT integration:
;   $HTTP=http://192.168.1.100/api/laser/cooling/off{"halt_on_error":false}

M5          ; Turn off laser
G0 X0 Y0    ; Return to home position
M2          ; End program
