import bluetooth
import struct
import time
import machine
#import ubinascii
from ble_advertising import advertising_payload
from micropython import const
from machine import Pin

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_INDICATE_DONE = const(20)

_FLAG_READ = const(0x0002)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)
_FLAG_INDICATE = const(0x0020)

_MIDI_SERVICE_UUID = bluetooth.UUID("03B80E5A-EDE8-4B33-A751-6CE34EC4C700")


_MIDI_CHAR = (
    bluetooth.UUID("7772E5DB-3868-4112-A1A9-F2669D106BF3"),
    _FLAG_READ | _FLAG_WRITE | _FLAG_NOTIFY | _FLAG_INDICATE,
)
_MIDI_SERVICE = (
    _MIDI_SERVICE_UUID,
    (_MIDI_CHAR,),
)


class BLEMidiSend:
    def __init__(self, ble, name=""):
        self._sensor_temp = machine.ADC(4)
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._handle,),) = self._ble.gatts_register_services((_MIDI_SERVICE,))
        self._connections = set()
        if len(name) == 0:
            name = 'MIDI BLE'
        print('Midi name: %s' % name)
        self._payload = advertising_payload(
            name=name, services=[_MIDI_SERVICE_UUID]
        )
        print(self._payload.hex())
        self._advertise()

    def _irq(self, event, data):
        # Track connections so we can send notifications.
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self._connections.remove(conn_handle)
            # Start advertising again to allow a new connection.
            self._advertise()
        elif event == _IRQ_GATTS_INDICATE_DONE:
            conn_handle, value_handle, status = data

    def update_msg(self, value, notify=False):
        # Write the local value, ready for a central to read.
        msg = bytearray(b'\x80\x80\xb0\x01')
        msg.append(value)
        print("Sending", msg);
        self._ble.gatts_write(self._handle, msg)
        #self._ble.gatts_write(self._handle, struct.pack("<h", int(temp_deg_c * 100)))
        if notify:
            for conn_handle in self._connections:
                # Notify connected centrals.
                self._ble.gatts_notify(conn_handle, self._handle)

    def _advertise(self, interval_us=500000):
        self._ble.gap_advertise(interval_us, adv_data=self._payload)
       
def demo():
    ble = bluetooth.BLE()
    midi = BLEMidiSend(ble)
    counter = 0
    led = Pin('LED', Pin.OUT)
    while True:
        midi.update_msg(counter, notify=True)
        led.toggle()
        time.sleep_ms(1000)
        counter += 1
        if counter > 127:
            counter = 0

if __name__ == "__main__":
    demo()