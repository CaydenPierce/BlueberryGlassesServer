"""
Connect to, stream, and log a single pair of Blueberry fNIRS glasses.
"""

from bluepy.btle import DefaultDelegate, Peripheral
import time 
import sys
import signal
import muselsl
import os
import threading
import bitstring
import numpy as np

#globals
blueberry = None
bby_thread = None
stream = False #should we be pushing data out?
saveFile = None

hemo_1_l = list() #holds hemo_1 vals at downsamples value
hemo_1_l_t = list() #temp array to hold the intermediate vales before average to downsample
hemo_2_l = list()#holds hemo_2 vals at downsampled value
hemo_2_l_t = list() #temp array to hold the intermediate vales before average to downsample
sf = 5 #downsample to 5Hz
t = time.time()
c = 0

#Blueberry glasses GATT server characteristics information
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

#handle Ctrl-C, killing program
def signal_handler(signal, frame):
    global blueberry, stream, bby_thread
    stream = False
    print("Closing bluetooth connection and disconnecting...")
    blueberry.disconnect()
    bby_thread.join()
    time.sleep(3)
    print("Connections closed and garbage cleaned, exiting.")
    sys.exit(0)

#for testing sampling rate with 
def circle_buf(arr, val):
    arr = np.roll(arr, -1)
    np.put(arr, -1, val)
    return arr

#unpack fNIRS byte string
def unpack_fnirs(packet):
    aa = bitstring.Bits(bytes=packet)
    pattern = "uintbe:8,uintbe:8,intbe:32,intbe:32,intbe:32,intbe:8,intbe:8"
    res = aa.unpack(pattern)
    packet_index = res[0]
    hemo_1 = res[2]
    hemo_2 = res[3]
    return packet_index, hemo_1, hemo_2

#receive fNIRS data callback
def receive_notify(characteristic_handle, data):
    global t, sams, full, c, sf, hemo_1_l, hemo_2_l, hemo_1_l_t, hemo_2_l_t
    if stream:
        packet_index, hemo_1, hemo_2 = unpack_fnirs(data)
        hemo_1_l_t.append(hemo_1)
        hemo_2_l_t.append(hemo_2)
        if (time.time() - t) >= (1/sf): #if the amount of time since last sample average is greater than or equal to the period, then average and save
            hemo_1_l.append(np.mean(hemo_1_l_t))
            hemo_2_l.append(np.mean(hemo_2_l_t))
            #empty the temporary arrays to refill
            hemo_1_l_t = list()
            hemo_2_l_t = list()
            #saveFile.write("{}, {}, {}\n".format(time.time(), hemo_1_l[-1], hemo_2_l[-1]))
            print("fNIRS -- Index {}: 880nm: {}, 940nm: {}".format(packet_index, hemo_1_l[-1], hemo_2_l[-1]))
            t = time.time() #reset timer

#delegate for bluepy handling BLE connection
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

#subscribe to Blueberry notifications
def setupBlueberry(device): #sets characteristic so the glasses send us data
    setup_data = b"\x01\x00"
    notify = device.getCharacteristics(uuid=bbxchars["fnirsCharacteristic"]["uuid"])[0]
    notify_handle = notify.getHandle() + 1
    print(notify_handle)
    device.writeCharacteristic(notify_handle, setup_data, withResponse=True)

#main blocking loop for bluepy streaming from Blueberry
def bby_loop(device):
    global stream
    print("Streaming in from Blueberry...")
    while True:
        if not device.waitForNotifications(1):
            print('nothing received')
        time.sleep(0.0000001)
        #end thread if we are no longer streaming
        if stream == False:
            break

def main():
    global blueberry, stream, bby_thread, saveFile
    if len(sys.argv) < 2:
        print("Usage: python3 base_station.py <Blueberry MAC address> <filename of csv>")
        print("MAC args not specified, exiting...")
        sys.exit()
    
    #handle killing of program
    signal.signal(signal.SIGINT, signal_handler)

    #MAC address of the device to connect
    bby_mac = sys.argv[1]
        
    #save file name and start
    saveFile = open("./data/{}".format(sys.argv[2]), "w+")
    saveFile.write("timestamp, packet_index, hemo_1, hemo_2\n")

    #connect, setup Blueberry glasses device
    print("Connecting to Blueberry: {}...".format(bby_mac))
    blueberry = Peripheral(bby_mac)
    peripheral_delegate = PeripheralDelegate(receive_notify)
    blueberry.setDelegate(peripheral_delegate)
    setupBlueberry(blueberry)
    peripheral_delegate.listen = True
    
    #start listening loops for Blueberry and muse
    bby_thread = threading.Thread(target=bby_loop, args=(blueberry,))
    bby_thread.start()
    stream = True #starting pushing out data stream

    #block here, because we have our two threads running in the background
    while True:
        pass

if __name__ == "__main__":
    main()
