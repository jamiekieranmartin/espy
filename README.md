# esp32s3-micropython

## Setup

1. Install the CH343SER driver for the ESP32S3.

2. Install the recommended VS Code extensions.

3. Configure your environment variables in a `.env` file.

4. Install the required Python packages: `pip install -r requirements.txt`.

5. Make the `esp.sh` script executable: 
   
```bash
chmod 777 ./esp.sh
```

6. Run the `esp.sh` script to flash the ESP32S3:

```bash
./esp.sh flash
```

7.  Run the `esp.sh` script to upload the code to the ESP32S3:

```bash
./esp.sh upload
```

# References

https://docs.micropython.org/en/latest/esp32/quickref.html
