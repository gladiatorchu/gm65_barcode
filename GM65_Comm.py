# ##################################################
# Control GM65 Barcode Module [http://www.hzgrow.cn/]
#    GM65:
#          Product ID: 26214
#          Vendor ID: 30583
#          Manufacturer: HZGrow
#          Default communication: 9600, 8, N, 1

import numpy as np
from time import sleep
import serial


# GM65 Parameter
# GM65 VID=26214 and PID=30583 when it is GM65 Virtual Serial
GM_VID = 26214
GM_PID = 30583

debugMsg = False
ser = serial

def gm65_scanPort():
    import serial.tools.list_ports
    ports = list(serial.tools.list_ports.comports())
    # print("Total serial port(s) in this computer: " + str(len(ports)))
    portName = ""
    for p in ports:
        print(p)
        if (p.vid, p.pid) == (GM_VID, GM_PID):
            portName = p.device
            break
    
    if portName == "":
        return None
    else:
        return portName


# def gm65_init():
# Setup the Serial
portName = gm65_scanPort()
if portName is not None:
    ser = serial.Serial(portName, 9600, timeout=0, parity=serial.PARITY_EVEN, stopbits=serial.STOPBITS_ONE)

    if ser.isOpen():
        print("Connected to " + str(ser.name))
    else:
        print("Failed to connect to the GM65 Barcode. Please check!!!")
else:
    print("Error. check port....")

def gm65_close():
    ser.close()


def getCRC_16(inData: bytes, crc_polynom=0x1021):
    '''
    CRC-16 Algorithm for GM65
    '''
    inData = bytearray(inData)
    crc = 0x0000
    for inD in inData:
        i = 0x80
        for _ in range(0, 8):
            crc *=2
            if ((crc & 0x10000) != 0):
                crc ^= crc_polynom
            if (inD & i) != 0:
                crc ^= crc_polynom
            i = (i//2)
    
    return crc & 0xFFFF

def readGM65Response(gm65_cmd):
    try:
        ser.flushInput()
        ser.write(serial.to_bytes(gm65_cmd))
        sleep(0.05)
    except Exception as e1:
        print("Error Communicating with ..." + str(e1))

    gm65_data = []
    gm65_forCRC = []

    gm65_read = ser.read()
    if gm65_read == b'\x02':
        # print("0x02 bingo")
        gm65_read = ser.read()
        if gm65_read == b'\x00':
            # print("0x00 bingo")
            # ^-----Passed the receive command HEAD 0x0200
            gm65_read = ser.read()
            if gm65_read == b'\x00':
                gm65_read = ser.read()  # 02 00 00 01 64 1F 13
                gm65_lens = int.from_bytes(gm65_read, 'little')
                if debugMsg:
                    print("Received Message Read Succeed !")
                    print("Data lenght: " + str(gm65_lens))

                # read the data byte by byte
                for getByte in np.arange(0,gm65_lens):
                    gm65_read = ord(ser.read())
                    # print(gm65_read)
                    gm65_data.append(gm65_read)

                # print("Received data: " + str(gm65_data))
                gm65_forCRC=[ord(b'\x00'), gm65_lens] + gm65_data
                # print(gm65_forCRC)
                chkCRC = getCRC_16(gm65_forCRC)
                # print("calculated CRC from recevied data is " + str(chkCRC))
                # Check CRC
                gm65_read = int.from_bytes(ser.read() + ser.read(), 'big')
                # print(gm65_read)
                if gm65_read == chkCRC:
                    if debugMsg:
                        print("Matched CRC. The recived data is:" + str(gm65_data))
                    return gm65_data
                else:
                    print("Error: Chk Sum Error")
    return -99

def form_gm65_cmd(addr: list, data: list, cmdType):
    gm65_Header = [0x7E, 0x00]
    gm65_Lens = [len(data)]
    if cmdType == "read":
        gm65_TypeWrite = [0x07]
    elif cmdType == "write":
        gm65_TypeWrite = [0x08]
    elif cmdType == "EEPROM":
        gm65_TypeWrite = [0x09]
    else:
        print("Error. Wrong cmd Type")
        return "Error"

    gm65_msgForCRC = gm65_TypeWrite + gm65_Lens + addr + data
    gm65_cmd = gm65_Header + gm65_msgForCRC + list(getCRC_16(gm65_msgForCRC).to_bytes(2, 'big'))

    return gm65_cmd

def doScanNow():
    sleep(2)
    readGM65Response(form_gm65_cmd([0x00, 0x02], [0x01], "write"))
    for cnt in np.arange(0,10):
        inData = ser.readline()
        if len(inData) > 0:
            print(inData)
            break
        sleep(0.3)

def gm65_saveConfiguration():
    ser.write(form_gm65_cmd([0x00, 0x00], [0], "EEPROM"))

def gm65_setupPrefixSuffix(setPreSuf: int):
    # Zone bit: 0x0060
    # Bit 6-5: 00 CR | 01 CRLF | 10 Tab | 11 Nane
    # Bit 4: 1 Allow add RF
    # Bit 3: 1 Allow add prefix
    # Bit 2: 1 Allow add Code ID
    # Bit 1: 1 Allow add suffix
    # Bit 0: 1 Allow add tail
    # 43d: b'0010 1011'
    readGM65Response(form_gm65_cmd([0x00, 0x60], [setPreSuf], "write"))

def gm65_readPrefix():
    return readGM65Response(form_gm65_cmd([0x00, 0x63], [15], "read"))

def gm65_readSuffix():
    return readGM65Response(form_gm65_cmd([0x00, 0x72], [15], "read"))

def gm65_updatePrefix(prefixList: list):
    ser.write(form_gm65_cmd([0x00, 0x63], prefixList, "write"))

def gm65_updateSuffix(suffixList: list):
    ser.write(form_gm65_cmd([0x00, 0x72], suffixList, "write"))

def gm65_setScanDuration(durationTime: int):
    # durationTime is 0.1s
    readGM65Response(form_gm65_cmd([0x00, 0x06], [durationTime*10], "write"))

def gm65_setSoundLvl(soundLvl: int):
    readGM65Response(form_gm65_cmd([0x00, 0x0A], [soundLvl], "write"))



## Example:
## Setup the prefix and suffix with CRLF
# gm65_setupPrefixSuffix(43)
# gm65_updatePrefix([33,33,83,35])
# gm65_updateSuffix([35,70,33,33])
# sleep(0.05)
# print("Updated Prefix: " + str(gm65_readPrefix()))
# print("Updated Suffix: " + str(gm65_readSuffix()))

doScanNow()

gm65_close()



