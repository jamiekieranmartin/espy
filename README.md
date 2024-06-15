# espy

## Pre-requisites

- [VS Code](https://code.visualstudio.com/)
- [Python](https://www.python.org/downloads/)

## Setup

1. Install the CH343SER driver for the ESP32S3.

2. Install the recommended VS Code extensions.

3. Configure your environment variables in a `.env` file.

4. Install the required Python packages:

```bash
pip install -r requirements.txt
pip install -U  micropython-esp32-s3-stubs --target ./typings --no-user
```

5. Make the `espy.sh` script executable: 

```bash
chmod 777 ./espy.sh
```

6. Run the `espy.sh` script to flash the ESP32S3:

```bash
./espy.sh flash
```

7.  Run the `espy.sh` script to upload the code to the ESP32S3:

```bash
./espy.sh upload
```

# References

https://docs.micropython.org/en/latest/esp32/quickref.html
