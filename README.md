# PicoWBLEMidiTest
Basic BLE Midi test for Pico W in Micropython

Requires two Pico Ws - one peripheral, one central. 

Both need ble_advertising.py.
Peripheral needs main.py
Central needsd ble_midi_central.py

main.py will send midi BLE messages one a second
ble_midi_central.py will scan for the other Pico W, connect and get notifications on each message

Proves it works!
