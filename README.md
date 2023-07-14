# PicoWBLEMidiTest
Basic BLE Midi test for Pico W in Micropython

Requires two Pico Ws - one peripheral, one central. 

Both need ble_advertising.py.
Peripheral needs main.py
Central needsd ble_midi_central.py

main.py will send midi BLE messages one a second
ble_midi_central.py will scan for the other Pico W, connect and get notifications on each message

Proves it works!

Interesting things I may forget later on:
1. Micropython notifies without even checking the CCCD (0x2902)
2. Micropython has no subscribe function - you have to gattc write to 0x2902 to register for notifiations
3. Unless the device you are connecting to is a Micropython device - see point (1)
4. Micropython allows access to the full advertisement data payload - wooeee
5. And to the scan data payload (type 4)
