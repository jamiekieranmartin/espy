from machine import Pin, SoftSPI


class MFRC522:
    """Driver for MFRC522 RFID/NFC reader module."""

    # Status codes
    STATUS_OK = 0
    STATUS_NO_TAG = 1
    STATUS_ERROR = 2

    # Request modes
    REQUEST_IDLE = 0x26  # Detect cards in idle mode
    REQUEST_ALL = 0x52  # Detect all cards

    # Authentication modes
    AUTH_KEY_A = 0x60
    AUTH_KEY_B = 0x61

    # Commands
    CMD_TRANSCEIVE = 0x0C
    CMD_AUTHENTICATE = 0x0E
    CMD_CALC_CRC = 0x03
    CMD_SOFT_RESET = 0x0F

    # Registers
    REG_COMMAND = 0x01
    REG_INT_EN = 0x02
    REG_INT_REQ = 0x04
    REG_ERROR = 0x06
    REG_STATUS = 0x08
    REG_FIFO_DATA = 0x09
    REG_FIFO_LEVEL = 0x0A
    REG_CONTROL = 0x0C
    REG_BIT_FRAMING = 0x0D
    REG_TX_CONTROL = 0x14
    REG_TX_ASK = 0x15
    REG_MODE = 0x11
    REG_CRC_RESULT_LSB = 0x21
    REG_CRC_RESULT_MSB = 0x22
    REG_TIMER_MODE = 0x2A
    REG_TIMER_PRESCALER = 0x2B
    REG_TIMER_RELOAD_HIGH = 0x2C
    REG_TIMER_RELOAD_LOW = 0x2D

    def __init__(self, spi: SoftSPI, chip_select: Pin):
        """
        Initialize MFRC522 reader.

        Args:
            spi: SPI bus instance
            chip_select: Chip select pin
        """
        self.spi = spi
        self.cs = chip_select
        self.cs.value(1)  # CS idle high
        self.spi.init()
        self.initialize()

    # ==================== Low-level Register Access ====================

    def write_register(self, register: int, value: int) -> None:
        """Write a byte to a register."""
        self.cs.value(0)
        # Address byte: (register << 1) & 0x7E for write
        self.spi.write(bytes([(register << 1) & 0x7E]))
        self.spi.write(bytes([value & 0xFF]))
        self.cs.value(1)

    def read_register(self, register: int) -> int:
        """Read a byte from a register."""
        self.cs.value(0)
        # Address byte: ((register << 1) & 0x7E) | 0x80 for read
        self.spi.write(bytes([((register << 1) & 0x7E) | 0x80]))
        value = self.spi.read(1)
        self.cs.value(1)
        return value[0]

    def set_register_bits(self, register: int, mask: int) -> None:
        """Set specific bits in a register (bitwise OR)."""
        current_value = self.read_register(register)
        self.write_register(register, current_value | mask)

    def clear_register_bits(self, register: int, mask: int) -> None:
        """Clear specific bits in a register (bitwise AND NOT)."""
        current_value = self.read_register(register)
        self.write_register(register, current_value & (~mask))

    # ==================== Communication with Card ====================

    def communicate_with_card(
        self, command: int, data_to_send: list[int]
    ) -> tuple[int, list[int], int]:
        """
        Send command and data to card, receive response.

        Args:
            command: Command byte (CMD_TRANSCEIVE or CMD_AUTHENTICATE)
            data_to_send: List of bytes to send

        Returns:
            tuple: (status, received_data, bits_received)
        """
        received_data = []
        bits_received = 0
        irq_enable = 0
        wait_irq = 0
        status = self.STATUS_ERROR

        # Configure interrupts based on command
        if command == self.CMD_AUTHENTICATE:
            irq_enable = 0x12
            wait_irq = 0x10
        elif command == self.CMD_TRANSCEIVE:
            irq_enable = 0x77
            wait_irq = 0x30

        # Setup for communication
        self.write_register(self.REG_INT_EN, irq_enable | 0x80)
        self.clear_register_bits(self.REG_INT_REQ, 0x80)
        self.set_register_bits(self.REG_FIFO_LEVEL, 0x80)  # Flush FIFO
        self.write_register(self.REG_COMMAND, 0x00)  # No action

        # Write data to FIFO
        for byte in data_to_send:
            self.write_register(self.REG_FIFO_DATA, byte)

        # Execute command
        self.write_register(self.REG_COMMAND, command)

        # Start transmission for transceive command
        if command == self.CMD_TRANSCEIVE:
            self.set_register_bits(self.REG_BIT_FRAMING, 0x80)

        # Wait for command completion (timeout after 2000 iterations)
        timeout = 2000
        while timeout > 0:
            irq_flags = self.read_register(self.REG_INT_REQ)
            timeout -= 1

            # Check if timer interrupt or command complete
            if irq_flags & 0x01:  # Timer interrupt
                break
            if irq_flags & wait_irq:  # Command complete
                break

        # Stop transmission
        self.clear_register_bits(self.REG_BIT_FRAMING, 0x80)

        if timeout > 0:
            error_flags = self.read_register(self.REG_ERROR)

            # Check for errors (ignore collision and protocol errors for now)
            if (error_flags & 0x1B) == 0x00:
                status = self.STATUS_OK

                irq_flags = self.read_register(self.REG_INT_REQ)

                # Check for no tag error
                if irq_flags & irq_enable & 0x01:
                    status = self.STATUS_NO_TAG
                elif command == self.CMD_TRANSCEIVE:
                    # Get received data from FIFO
                    fifo_level = self.read_register(self.REG_FIFO_LEVEL)
                    last_bits = self.read_register(self.REG_CONTROL) & 0x07

                    # Calculate total bits received
                    if last_bits != 0:
                        bits_received = (fifo_level - 1) * 8 + last_bits
                    else:
                        bits_received = fifo_level * 8

                    # Read data from FIFO (max 16 bytes)
                    num_bytes = min(fifo_level if fifo_level > 0 else 1, 16)
                    for _ in range(num_bytes):
                        received_data.append(self.read_register(self.REG_FIFO_DATA))
            else:
                status = self.STATUS_ERROR

        return status, received_data, bits_received

    def calculate_crc(self, data: list[int]) -> list[int]:
        """
        Calculate CRC for data.

        Args:
            data: List of bytes

        Returns:
            list: [CRC_LSB, CRC_MSB]
        """
        self.clear_register_bits(0x05, 0x04)  # Clear CRC IRQ
        self.set_register_bits(self.REG_FIFO_LEVEL, 0x80)  # Flush FIFO

        # Write data to FIFO
        for byte in data:
            self.write_register(self.REG_FIFO_DATA, byte)

        # Start CRC calculation
        self.write_register(self.REG_COMMAND, self.CMD_CALC_CRC)

        # Wait for CRC calculation to complete
        timeout = 0xFF
        while timeout > 0:
            status = self.read_register(0x05)
            timeout -= 1
            if status & 0x04:  # CRC ready
                break

        # Read CRC result (LSB first, then MSB)
        return [
            self.read_register(self.REG_CRC_RESULT_MSB),
            self.read_register(self.REG_CRC_RESULT_LSB),
        ]

    # ==================== Initialization ====================

    def initialize(self) -> None:
        """Initialize the MFRC522 reader with default settings."""
        self.reset()

        # Configure timer and mode registers
        self.write_register(self.REG_TIMER_MODE, 0x8D)
        self.write_register(self.REG_TIMER_PRESCALER, 0x3E)
        self.write_register(self.REG_TIMER_RELOAD_LOW, 30)
        self.write_register(self.REG_TIMER_RELOAD_HIGH, 0)

        # Configure transmission
        self.write_register(self.REG_TX_ASK, 0x40)  # Force 100% ASK modulation
        self.write_register(self.REG_MODE, 0x3D)  # CRC preset 0x6363

        self.enable_antenna()

    def reset(self) -> None:
        """Perform soft reset of the MFRC522."""
        self.write_register(self.REG_COMMAND, self.CMD_SOFT_RESET)

    def enable_antenna(self, enable: bool = True) -> None:
        """
        Enable or disable the antenna.

        Args:
            enable: True to enable, False to disable
        """
        current_state = self.read_register(self.REG_TX_CONTROL)

        if enable and not (current_state & 0x03):
            self.set_register_bits(self.REG_TX_CONTROL, 0x03)
        elif not enable:
            self.clear_register_bits(self.REG_TX_CONTROL, 0x03)

    # ==================== Card Detection and Selection ====================

    def detect_card(self, mode: int = REQUEST_IDLE) -> tuple[int, int]:
        """
        Detect if a card is present.

        Args:
            mode: REQUEST_IDLE (default) or REQUEST_ALL

        Returns:
            tuple: (status, bits_received)
        """
        self.write_register(self.REG_BIT_FRAMING, 0x07)
        status, _, bits = self.communicate_with_card(self.CMD_TRANSCEIVE, [mode])

        # Valid card response should be 16 bits (2 bytes: ATQA)
        if status != self.STATUS_OK or bits != 0x10:
            status = self.STATUS_ERROR

        return status, bits

    def get_card_uid(self) -> tuple[int, list[int]]:
        """
        Get the unique ID (UID) of the card using anti-collision.
        Supports both 4-byte and 7-byte UIDs (cascade levels 1 and 2).

        Returns:
            tuple: (status, uid_bytes)
        """
        # Cascade Level 1: Anti-collision command
        command = [0x93, 0x20]

        self.write_register(self.REG_BIT_FRAMING, 0x00)
        status, uid_part1, bits = self.communicate_with_card(
            self.CMD_TRANSCEIVE, command
        )

        if status != self.STATUS_OK:
            return status, []

        if len(uid_part1) != 5:
            return self.STATUS_ERROR, []

        # Verify checksum (XOR of first 4 bytes should equal 5th byte)
        checksum = 0
        for i in range(4):
            checksum ^= uid_part1[i]

        if checksum != uid_part1[4]:
            return self.STATUS_ERROR, []

        # Check if this is a 7-byte UID (indicated by first byte = 0x88)
        if uid_part1[0] == 0x88:
            # This is a 7-byte UID - need cascade level 2
            # First 3 bytes of actual UID are in positions 1-3
            uid = uid_part1[1:4]

            # Select cascade level 1
            select_cmd = [0x93, 0x70] + uid_part1[:5]
            select_cmd += self.calculate_crc(select_cmd)
            status, response, bits = self.communicate_with_card(
                self.CMD_TRANSCEIVE, select_cmd
            )

            if status != self.STATUS_OK:
                return self.STATUS_ERROR, []

            # Cascade Level 2: Get remaining 4 bytes of UID
            command = [0x95, 0x20]
            self.write_register(self.REG_BIT_FRAMING, 0x00)
            status, uid_part2, bits = self.communicate_with_card(
                self.CMD_TRANSCEIVE, command
            )

            if status != self.STATUS_OK:
                return status, []

            if len(uid_part2) != 5:
                return self.STATUS_ERROR, []

            # Verify checksum for second part
            checksum = 0
            for i in range(4):
                checksum ^= uid_part2[i]

            if checksum != uid_part2[4]:
                return self.STATUS_ERROR, []

            # Combine to get full 7-byte UID
            uid = uid + uid_part2[:4]
            return self.STATUS_OK, uid
        else:
            # This is a 4-byte UID
            return self.STATUS_OK, uid_part1[:4]

    def select_card(self, uid: list[int]) -> int:
        """
        Select a card using its UID.
        Automatically handles 4-byte and 7-byte UIDs.

        Args:
            uid: Card UID (list of bytes) - 4 or 7 bytes

        Returns:
            int: STATUS_OK or STATUS_ERROR
        """
        if len(uid) == 7:
            # 7-byte UID requires cascade level 2 selection
            # First select cascade level 1 with CT (0x88) + first 3 bytes
            buffer1 = [0x93, 0x70, 0x88] + uid[:3]
            # Calculate BCC (checksum) for cascade level 1
            bcc1 = 0x88 ^ uid[0] ^ uid[1] ^ uid[2]
            buffer1.append(bcc1)
            buffer1 += self.calculate_crc(buffer1)

            status, data, bits = self.communicate_with_card(
                self.CMD_TRANSCEIVE, buffer1
            )
            if status != self.STATUS_OK:
                return self.STATUS_ERROR

            # Now select cascade level 2 with remaining 4 bytes
            buffer2 = [0x95, 0x70] + uid[3:7]
            # Calculate BCC for cascade level 2
            bcc2 = uid[3] ^ uid[4] ^ uid[5] ^ uid[6]
            buffer2.append(bcc2)
            buffer2 += self.calculate_crc(buffer2)

            status, data, bits = self.communicate_with_card(
                self.CMD_TRANSCEIVE, buffer2
            )
            return (
                self.STATUS_OK
                if (status == self.STATUS_OK and bits == 0x18)
                else self.STATUS_ERROR
            )

        elif len(uid) == 4:
            # 4-byte UID - original implementation
            buffer = [0x93, 0x70] + uid[:4]
            # Calculate BCC
            bcc = uid[0] ^ uid[1] ^ uid[2] ^ uid[3]
            buffer.append(bcc)
            buffer += self.calculate_crc(buffer)

            status, data, bits = self.communicate_with_card(self.CMD_TRANSCEIVE, buffer)
            return (
                self.STATUS_OK
                if (status == self.STATUS_OK and bits == 0x18)
                else self.STATUS_ERROR
            )

        else:
            return self.STATUS_ERROR

    # ==================== Authentication and Data Access ====================

    def authenticate(
        self, auth_mode: int, block_address: int, key: list[int], uid: list[int]
    ) -> int:
        """
        Authenticate access to a card sector.

        Args:
            auth_mode: AUTH_KEY_A or AUTH_KEY_B
            block_address: Block address to authenticate
            key: 6-byte authentication key
            uid: First 4 bytes of card UID

        Returns:
            int: Status code
        """
        command = [auth_mode, block_address] + key + uid[:4]
        status, _, _ = self.communicate_with_card(self.CMD_AUTHENTICATE, command)
        return status

    def stop_authentication(self) -> None:
        """Stop encrypted communication with the card."""
        self.clear_register_bits(self.REG_STATUS, 0x08)

    def read_block(self, block_address: int) -> list[int] | None:
        """
        Read 16 bytes from a card block.

        Args:
            block_address: Block address (0-63 for 1K cards)

        Returns:
            list: 16 bytes of data, or None if error
        """
        command = [0x30, block_address]
        command += self.calculate_crc(command)

        status, data, _ = self.communicate_with_card(self.CMD_TRANSCEIVE, command)

        return data if status == self.STATUS_OK else None

    def write_block(self, block_address: int, data: list[int]) -> int:
        """
        Write 16 bytes to a card block.

        Args:
            block_address: Block address (0-63 for 1K cards)
            data: 16 bytes to write

        Returns:
            int: Status code
        """
        # Send write command
        buffer = [0xA0, block_address]
        buffer += self.calculate_crc(buffer)

        status, response, bits = self.communicate_with_card(self.CMD_TRANSCEIVE, buffer)

        # Check ACK (4 bits, response 0x0A)
        if status != self.STATUS_OK or bits != 4 or (response[0] & 0x0F) != 0x0A:
            return self.STATUS_ERROR

        # Send data
        buffer = list(data[:16])  # Ensure exactly 16 bytes
        if len(buffer) < 16:
            buffer += [0] * (16 - len(buffer))  # Pad with zeros

        buffer += self.calculate_crc(buffer)

        status, response, bits = self.communicate_with_card(self.CMD_TRANSCEIVE, buffer)

        # Check ACK again
        if status != self.STATUS_OK or bits != 4 or (response[0] & 0x0F) != 0x0A:
            return self.STATUS_ERROR

        return self.STATUS_OK
