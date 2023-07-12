import bluetooth
import time
from ble_advertising import decode_services, decode_name
from micropython import const

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4)
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_DESCRIPTOR_RESULT = const(13)
_IRQ_GATTC_DESCRIPTOR_DONE = const(14)
_IRQ_GATTC_READ_RESULT = const(15)
_IRQ_GATTC_READ_DONE = const(16)
_IRQ_GATTC_WRITE_DONE = const(17)
_IRQ_GATTC_NOTIFY = const(18)
_IRQ_GATTC_INDICATE = const(19)

_ADV_IND = const(0x00)
_ADV_DIRECT_IND = const(0x01)
_ADV_SCAN_IND = const(0x02)
_ADV_NONCONN_IND = const(0x03)

MIDI_SERVICE_UUID = bluetooth.UUID("03B80E5A-EDE8-4B33-A751-6CE34EC4C700")
MIDI_CHAR_UUID =    bluetooth.UUID("7772E5DB-3868-4112-A1A9-F2669D106BF3")

class BLEMidiCentral:
    def __init__(self, ble):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        self._reset()

    def _reset(self):
        # Cached name and address from a successful scan.
        self._name = None
        self._addr_type = None
        self._addr = None

        # In a current scan
        self._in_scan = False
        
        # Cached value (if we have one)
        self._value = None

        # Callbacks for completion of various operations.
        # These reset back to None after being invoked.
        self._scan_callback = None
        self._conn_callback = None
        self._read_callback = None

        # Persistent callback for when new data is notified from the device.
        self._notify_callback = None

        # Connected device.
        self._conn_handle = None
        self._start_handle = None
        self._end_handle = None
        self._value_handle = None
        self._notify_dsc_handle  = None

    def _irq(self, event, data):
        if event == _IRQ_SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
            
            print(event, addr_type, bytes(addr).hex(), adv_type, rssi, bytes(adv_data).hex())
            if adv_type in (_ADV_IND, _ADV_DIRECT_IND):
                type_list = decode_services(adv_data)
                if MIDI_SERVICE_UUID in type_list:
                    self._addr_type = addr_type
                    self._addr = bytes(addr)  # Note: addr buffer is owned by caller so need to copy it.
                    self._name = decode_name(adv_data) or "?"
                    self._ble.gap_scan(None)  # Stop scan

        elif event == _IRQ_SCAN_DONE:
            # Scan is finished
            self._in_scan = False


        elif event == _IRQ_PERIPHERAL_CONNECT:
            # Connect successful so start dscovering services
            conn_handle, addr_type, addr = data
            
            if addr_type == self._addr_type and addr == self._addr:
                self._conn_handle = conn_handle
                self._ble.gattc_discover_services(self._conn_handle)

        elif event == _IRQ_PERIPHERAL_DISCONNECT:
            # Disconnect (either initiated by us or the remote end).
            conn_handle, _, _ = data
            
            if conn_handle == self._conn_handle:
                # If it was initiated by us, it'll already be reset.
                self._reset()


        elif event == _IRQ_GATTC_SERVICE_RESULT:
            # Connected device returned a service.
            conn_handle, start_handle, end_handle, uuid = data
            
            print("Service", conn_handle, start_handle, end_handle, uuid)
            if conn_handle == self._conn_handle and uuid == MIDI_SERVICE_UUID:
                self._start_handle, self._end_handle = start_handle, end_handle

        elif event == _IRQ_GATTC_SERVICE_DONE:
            # Service query complete.
            if self._start_handle and self._end_handle:
                self._ble.gattc_discover_characteristics(self._conn_handle, self._start_handle, self._end_handle)
            else:
                print("Failed to find service")


        elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
            # Connected device returned a characteristic.
            conn_handle, def_handle, value_handle, properties, uuid = data

            print("Characteristic", conn_handle, def_handle, value_handle, properties, uuid)
            if conn_handle == self._conn_handle and uuid == MIDI_CHAR_UUID:
                self._value_handle = value_handle

        elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
            # Characteristic query complete.
            if self._value_handle:
                self._ble.gattc_discover_descriptors(self._conn_handle, self._start_handle, self._end_handle)
            else:
                print("Failed to find characteristic")


        elif event == _IRQ_GATTC_DESCRIPTOR_RESULT:
            # Called for each descriptor found by gattc_discover_descriptors().
            conn_handle, dsc_handle, uuid = data
            
            print("Descriptor", conn_handle, dsc_handle, uuid)
            if uuid == bluetooth.UUID(0x2902):
                self._notify_dsc_handle = dsc_handle
 
        elif event == _IRQ_GATTC_DESCRIPTOR_DONE:
            # Called once service discovery is complete.
            # Note: Status will be zero on success, implementation-specific value otherwise.
            conn_handle, status = data
            
            if self._notify_dsc_handle:
                self._ble.gattc_write(self._conn_handle, self._notify_dsc_handle, b'\x01\x00' )
            else:
                print("Failed to find descriptor")
                

        elif event == _IRQ_GATTC_READ_RESULT:
            # A read completed successfully.
            conn_handle, value_handle, char_data = data
            
            if conn_handle == self._conn_handle and value_handle == self._value_handle:
                self._update_value(char_data)
                if self._read_callback:
                    self._read_callback(self._value)
                    self._read_callback = None

        elif event == _IRQ_GATTC_READ_DONE:
            # Read completed (no-op).
            conn_handle, value_handle, status = data


        elif event == _IRQ_GATTC_NOTIFY:
            conn_handle, value_handle, notify_data = data
            if conn_handle == self._conn_handle and value_handle == self._value_handle:
                self._update_value(notify_data)
                if self._notify_callback:
                    self._notify_callback(self._value)
                    
    # Returns true if the scan was successful
    def scan_success(self):
        return self._addr_type is not None

    def in_scan(self):
        return self._in_scan
    
    # Returns true if we've successfully connected and discovered characteristics.
    def is_connected(self):
        return self._conn_handle is not None and self._value_handle is not None

    # Find a device advertising the environmental sensor service.
    def scan(self, callback=None):
        self._addr_type = None
        self._addr = None
        self._in_scan = True
        self._ble.gap_scan(2000, 30000, 30000)

    # Connect to the specified device (otherwise use cached address from a scan).
    def connect(self, addr_type=None, addr=None):
        self._addr_type = addr_type or self._addr_type
        self._addr = addr or self._addr
        if self._addr_type is None or self._addr is None:
            return False
        self._ble.gap_connect(self._addr_type, self._addr)
        return True

    # Disconnect from current device.
    def disconnect(self):
        if not self._conn_handle:
            return
        self._ble.gap_disconnect(self._conn_handle)
        self._reset()

    # Issues an (asynchronous) read, will invoke callback with data.
    def read(self, callback):
        if not self.is_connected():
            return
        self._read_callback = callback
        try:
            self._ble.gattc_read(self._conn_handle, self._value_handle)
        except OSError as error:
            print(error)

    # Sets a callback to be invoked when the device notifies us.
    def on_notify(self, callback):
        self._notify_callback = callback

    def _update_value(self, data):
        self._value = bytes(data)

    def value(self):
        return self._value


def read_callback(result):
    print("Read value: {}".format(result.hex()))
    
def notified_callback(result):
    print("Notified: {}".format(result.hex()))

def demo(ble, central):

    while not central.scan_success():
        if not central.in_scan():
            central.scan()
        
    central.connect()
    while not central.is_connected():
        time.sleep_ms(100)

    print("Connected")
    central.on_notify(notified_callback)
    
    while central.is_connected():
        time.sleep_ms(100)
        #central.read(callback=read_callback)

    print("Disconnected")

if __name__ == "__main__":
    ble = bluetooth.BLE()
    central = BLEMidiCentral(ble)
    demo(ble, central)

