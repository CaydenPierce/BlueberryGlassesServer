"""
Put the two blueberry glasses MAC addresses that you want to connect in MACs.txt
"""
from bluepy.btle import DefaultDelegate, Peripheral
import time 
import threading
import struct

bbxService={"name": 'fnirs service',
            "uuid": '0f0e0d0c-0b0a-0908-0706-050403020100' }
bbxchars={
          "commandCharacteristic": {
              "name": 'write characteristic',
                  "uuid": '1f1e1d1c-1b1a-1918-1716-151413121110'
                    },
            "fnirsCharacteristic": {
                    "name": 'read fnirs data characteristic',
                        "uuid": '3f3e3d3c-3b3a-3938-3736-353433323130'
                          }
            }

class PeripheralDelegate(DefaultDelegate):
    """
    Used by bluepy to receive notifys from BLE GATT Server.
    """
    def __init__(self, callback):
        DefaultDelegate.__init__(self)
        self.callback = callback
        self.listen = False
       
    def handleNotification(self, characteristic_handle, data):
        if self.listen:
            self.callback(characteristic_handle, data)

#hack to have two glasses stream in, should make this one func for all glasses
def receive_notify_1(characteristic_handle, data):
    """
    This is where all the data streams come in.
    """
    print("Device #1 data: ", end="")
    print(data)

def receive_notify_2(characteristic_handle, data):
    """
    This is where all the data streams come in.
    """
    print("Device #2 data: ", end="")
    print(data)

def setupBlueberry(device): #sets characteristic so the glasses send us data
    setup_data = b"\x01\x00"
    notify = device.getCharacteristics(uuid=bbxchars["fnirsCharacteristic"]["uuid"])[0]
    notify_handle = notify.getHandle() + 1
    print(notify_handle)
    device.writeCharacteristic(notify_handle, setup_data, withResponse=True)

def mainLoop(myId,device):
    while True:
        if not device.waitForNotifications(1):
            print('nothing received')
        time.sleep(0.001)

def main():
    macs = list()
    devs = list()
    delgs = list()
    with open("./MACs.txt", "r") as f:
        for line in f:
            macs.append(line.strip())

    #connect and setup two devices... kinda ugly here for now
    peripheral = Peripheral(macs[0])
    devs.append(peripheral)
    peripheral_delegate = PeripheralDelegate(receive_notify_1)
    delgs.append(peripheral_delegate)
    peripheral.setDelegate(peripheral_delegate)

    peripheral = Peripheral(macs[1])
    devs.append(peripheral)
    peripheral_delegate = PeripheralDelegate(receive_notify_2)
    delgs.append(peripheral_delegate)
    peripheral.setDelegate(peripheral_delegate)

    # start streaming data
    time.sleep(1)
    for dev in devs:
        setupBlueberry(dev)
    for delg in delgs:
        delg.listen = True
    ts = list()
    for i, dev in enumerate(devs):
        ts.append(threading.Thread(target=mainLoop, args=[i, dev]))
    for t in ts:
        t.start()

    
if __name__ == "__main__":
    main()

