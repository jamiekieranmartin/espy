# espy

## Prerequisites

- [VS Code](https://code.visualstudio.com/)
- [Python](https://www.python.org/downloads/)
- CH34XSER driver
  - [MacOS](https://www.wch-ic.com/downloads/CH34XSER_MAC_ZIP.html)
  - [Windows](https://www.wch-ic.com/downloads/CH343SER_EXE.html)

## Setup

1. Install the required Python packages + MicroPython type stubs:

```bash
pip install -U -r requirements.txt 
pip install -U -r micropython_esp32_s3_stubs --target ./.vscode/typings --no-user
```

2. Make the `espy.sh` script executable: 

```bash
chmod +x ./espy.sh
```

3. Run the `espy.sh` script to flash the chip:

```bash
./espy.sh flash
```

4.  Run the `espy.sh` script to upload the code to the chip:

```bash
./espy.sh upload
```

OR, watch the code for changes and upload them automatically:

```bash
./espy.sh watch
```

# References

## esp32

https://docs.micropython.org/en/latest/esp32/quickref.html

### MicroPython downloads

https://micropython.org/download/ESP32_GENERIC_S3/
