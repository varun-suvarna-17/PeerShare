# Network Flow – File Transfer System

## 1. Overview

The application enables file transfer between two laptops connected to the same local network. It implements three ARQ protocols (Stop-and-Wait, Go-Back-N and Selective Repeat) using UDP to demonstrate reliable data transmission.

The system uses actual UDP frames and acknowledgements for file transfer. Live visualization events are generated from real network and protocol operations rather than independent animations.

The communication is divided into five major stages:

1. Device Discovery
2. Connection and Session Establishment
3. File Transfer Request
4. UDP File Transfer using ARQ
5. File Reconstruction and Verification

---

## 2. Device Discovery

### Objective

Allow sender and receiver devices to discover each other on the same local network.

### Primary Method: Automatic Discovery

The system uses Zeroconf (mDNS/DNS-SD) for automatic device discovery.

**Flow:**

1. Both laptops start the application.
2. Each backend advertises its availability on the local network using Zeroconf.
3. The sender searches for available receiver devices.
4. Available devices are displayed in the sender's device list.
5. The sender selects the intended receiver.

### Fallback Method: Manual IP + PIN

If automatic discovery fails, the system provides a manual connection option.

**Flow:**

1. Receiver generates a temporary six-digit PIN.
2. Receiver displays the PIN along with its local IP address.
3. Sender enters the receiver's IP address and PIN.
4. Receiver backend validates the PIN.
5. If valid, the connection process proceeds.

**PIN Security:**

* PIN expires after a short duration.
* PIN becomes invalid after successful pairing.
* Invalid PIN attempts are rejected.

Note: Zeroconf is used only for device discovery. It does not establish the ARQ data-transfer connection.

---

## 3. Connection and Session Establishment

### Objective

Establish communication between the two laptops and create a transfer session.

HTTP over TCP is used for control communication.

**Flow:**

1. Sender sends a connection request to the receiver backend.
2. Receiver validates the connection request.
3. Receiver accepts the connection.
4. Both backends create a common session.
5. Session information is exchanged between the devices.
6. Receiver backend opens a UDP listening socket on an available port.
7. Receiver shares its IP address and UDP port with the sender.

### Session Information

| Parameter         | Description                       |
| ----------------- | --------------------------------- |
| Session ID        | Unique identifier for the session |
| Sender IP         | Local IP address of sender        |
| Receiver IP       | Local IP address of receiver      |
| Receiver UDP Port | Port used to receive data frames  |
| Session Status    | Current connection status         |

Each frame and acknowledgement is associated with the appropriate session.

---

## 4. File Transfer Request

### Objective

Allow the sender to select a file and obtain receiver approval before transmission.

**Flow:**

1. Sender selects a file.
2. Sender selects the ARQ protocol.
3. Sender configures transfer settings, including packet-loss simulation if required.
4. Sender sends a transfer request to the receiver through HTTP.
5. Receiver receives the request and displays file details.
6. Receiver accepts or rejects the transfer.
7. If accepted, both backends prepare their respective UDP communication components.
8. File transmission begins.

The receiver must be ready to receive UDP frames before the sender starts transmitting.

---

## 5. UDP File Transfer Using ARQ

### Objective

Transfer file data reliably using UDP and implement reliability through the three ARQ protocols.

UDP is used for actual file-data transmission. Reliability mechanisms such as acknowledgements, sequence numbers, timeouts and retransmissions are implemented at the application level.

### 5.1 File Division

1. Sender reads the selected file.
2. File is divided into smaller chunks.
3. Each chunk is placed inside a data frame.
4. Frames are assigned sequence numbers.
5. Frames are transmitted through UDP.

### 5.2 UDP Frame Structure

A common frame format is used across all three ARQ protocols.

#### Data Frame

| Field           | Purpose                            |
| --------------- | ---------------------------------- |
| Session ID      | Identifies the active transfer     |
| Frame Type      | Identifies the frame as DATA       |
| Sequence Number | Identifies the frame               |
| Payload Length  | Specifies the size of file data    |
| Checksum        | Detects accidental data corruption |
| Payload         | Actual file data                   |

#### ACK Frame

| Field      | Purpose                           |
| ---------- | --------------------------------- |
| Session ID | Identifies the active transfer    |
| Frame Type | Identifies the frame as ACK       |
| ACK Number | Identifies the acknowledged frame |
| Checksum   | Validates the ACK                 |

### 5.3 Frame Configuration

| Parameter               | Initial Value |
| ----------------------- | ------------- |
| Frame Payload Size      | 1024 bytes    |
| Sequence Number         | 16-bit        |
| Checksum                | CRC32         |
| Maximum Sequence Number | 65535         |

Sequence numbers wrap around after reaching the maximum value.

SHA-256 is used separately for final file-integrity verification.

### 5.4 ARQ Protocol Implementation

#### A. Stop-and-Wait (One-Bit ARQ)

**Working:**

* Sender transmits one frame at a time.
* Sender waits for the corresponding ACK.
* After receiving the ACK, sender transmits the next frame.
* Sequence numbers alternate between 0 and 1.
* If ACK is not received before timeout, the same frame is retransmitted.

**Window Configuration:** 1 frame.

#### B. Go-Back-N ARQ

**Working:**

* Sender can transmit multiple frames without waiting for individual ACKs.
* Sender maintains a sliding window.
* Receiver accepts only frames arriving in the expected sequence.
* Out-of-order frames are discarded.
* Receiver sends cumulative acknowledgements.
* If a frame is lost or a timeout occurs, sender retransmits the missing frame and all subsequent outstanding frames.

**Window Configuration:** 4 frames initially.

#### C. Selective Repeat ARQ

**Working:**

* Sender can transmit multiple frames without waiting for individual ACKs.
* Sender maintains a sliding window.
* Receiver accepts and buffers out-of-order frames.
* Receiver sends individual acknowledgements for received frames.
* If a frame is lost, only that specific frame is retransmitted.
* Buffered frames are arranged in the correct order during reconstruction.

**Window Configuration:** 4 frames initially.

### 5.5 ARQ Configuration

| Parameter             |  Stop-and-Wait |                                 Go-Back-N |    Selective Repeat |
| --------------------- | -------------: | ----------------------------------------: | ------------------: |
| Sender Window Size    |              1 |                                         4 |                   4 |
| Receiver Window Size  |              1 |                                         1 |                   4 |
| ACK Type              |     Individual |                                Cumulative |          Individual |
| Out-of-Order Handling | Not applicable |                                   Discard |              Buffer |
| Retransmission        |  Current frame | Missing and subsequent outstanding frames | Only missing frames |

For Selective Repeat, the receiver window size must not exceed half the sequence-number space to avoid ambiguity when sequence numbers wrap around.

### 5.6 ACK Handling

* Receiver generates ACKs after processing valid frames.
* ACKs are sent back to the sender as actual UDP datagrams.
* Sender receives ACKs and updates its transmission window.
* Acknowledged frames are removed from the outstanding-frame tracking structure.
* ACK behaviour depends on the selected ARQ protocol.

### 5.7 Timeout and Retransmission

| Parameter               | Initial Value |
| ----------------------- | ------------- |
| Initial Timeout         | 1 second      |
| Maximum Retransmissions | 5             |

If the expected acknowledgement is not received within the timeout:

1. Timer Manager detects the timeout.
2. Retransmission Manager identifies the frame or frames requiring retransmission.
3. Sender retransmits according to the selected ARQ protocol.
4. The process continues until the required ACKs arrive or the retransmission limit is reached.

These values can be made configurable later.

---

## 6. Packet Loss Simulation

The application provides configurable packet-loss simulation to demonstrate the behaviour of ARQ protocols under different network conditions.

### Initial Configuration

| Loss Percentage | Description      |
| --------------- | ---------------- |
| 0%              | Normal transfer  |
| 10%             | Low packet loss  |
| 30%             | High packet loss |

Packet loss is introduced at the UDP transmission layer.

The simulation randomly drops selected data frames or ACK datagrams before they are transmitted. This allows the ARQ engine to experience missing datagrams and perform actual timeout and retransmission operations.

The system should distinguish between simulated packet loss and naturally occurring network loss.

---

## 7. Live Visualization

### Objective

Display the actual file-transfer process on both laptops in real time.

Every significant network or protocol operation generates a visualization event.

### Event Types

| Event               | Description                                                           |
| ------------------- | --------------------------------------------------------------------- |
| FRAME_SENT          | Sender transmits a frame                                              |
| FRAME_RECEIVED      | Receiver receives a frame                                             |
| ACK_SENT            | Receiver sends an acknowledgement                                     |
| ACK_RECEIVED        | Sender receives an acknowledgement                                    |
| FRAME_LOST          | Frame is dropped during simulated loss                                |
| ACK_LOST            | ACK is dropped during simulated loss                                  |
| TIMEOUT             | Sender detects a timeout                                              |
| FRAME_RETRANSMITTED | Sender retransmits a frame                                            |
| FRAME_BUFFERED      | Receiver buffers an out-of-order frame                                |
| FRAME_DISCARDED     | Receiver discards an invalid or unwanted duplicate/out-of-order frame |
| TRANSFER_COMPLETED  | All required frames are acknowledged and processed                    |

### Event Communication

1. Backend performs an actual network or protocol operation.
2. Corresponding visualization event is generated.
3. WebSocket Manager sends the event to the local frontend.
4. Frontend updates the transfer visualization.

Both laptops receive their own backend events through WebSockets.

Events should include session IDs and frame sequence numbers to help correlate corresponding operations across devices.

The visualization must reflect actual network events rather than an independently generated animation timeline.

---

## 8. File Reconstruction and Verification

### Objective

Reconstruct the original file at the receiver and verify its integrity.

**Flow:**

1. Receiver collects successfully received file chunks.
2. Chunks are arranged in the correct sequence.
3. Receiver reconstructs the original file.
4. Receiver calculates the SHA-256 hash of the reconstructed file.
5. Sender's original file hash is compared with the reconstructed file hash.
6. If both hashes match, file integrity is confirmed.
7. Transfer is marked as completed.

### Transfer Report

The system displays:

* Original file name and size.
* Selected ARQ protocol.
* Total frames transmitted.
* Total frames received.
* Total ACKs.
* Total retransmissions.
* Total transfer duration.
* Throughput.
* File integrity status.

---

## 9. Network Error Handling

| Scenario                        | System Behaviour                                                                          |
| ------------------------------- | ----------------------------------------------------------------------------------------- |
| Device discovery fails          | Allow manual IP and PIN connection                                                        |
| Invalid or expired PIN          | Reject connection request                                                                 |
| Connection request times out    | Display connection failure and allow retry                                                |
| Receiver rejects transfer       | Cancel transfer and notify sender                                                         |
| Data frame gets lost            | Detect through missing ACK and retransmit                                                 |
| ACK gets lost                   | Sender timeout triggers retransmission; receiver identifies duplicate and sends ACK again |
| Duplicate frame received        | Avoid writing duplicate data and send appropriate ACK                                     |
| Out-of-order frame received     | Go-Back-N discards it; Selective Repeat buffers it                                        |
| Frame is corrupted              | Reject frame and do not acknowledge it as successfully received                           |
| Receiver disconnects            | Stop transmission and report connection failure                                           |
| Maximum retransmissions reached | Mark transfer as failed                                                                   |
| File hash mismatch              | Report integrity failure and do not mark transfer successful                              |

---

## 10. Overall Network Flow

```text
START APPLICATION ON BOTH LAPTOPS
                |
                v
         DEVICE DISCOVERY
                |
        +-------+-------+
        |               |
     Zeroconf       Manual IP + PIN
        |               |
        +-------+-------+
                |
                v
      SESSION ESTABLISHMENT
                |
                v
      RECEIVER OPENS UDP PORT
                |
                v
        SENDER SELECTS FILE
                |
                v
       TRANSFER REQUEST SENT
                |
                v
       RECEIVER ACCEPTS REQUEST?
             /       \
           NO         YES
           |           |
         CANCEL        v
                  SELECT ARQ
                      |
                      v
                SPLIT INTO FRAMES
                      |
                      v
               UDP TRANSMISSION
                      |
                      v
             ACK + WINDOW MANAGEMENT
                      |
                      v
              LOSS / TIMEOUT DETECTED?
                  /       \
                YES        NO
                 |          |
            RETRANSMIT   NEXT FRAMES
                 |          |
                 +----+-----+
                      |
                      v
              ALL FRAMES ACKED
                      |
                      v
             FILE RECONSTRUCTION
                      |
                      v
               SHA-256 CHECK
                      |
                      v
              TRANSFER COMPLETED
```

---

## 11. Communication Summary

| Communication            | Technology      | Purpose                                   |
| ------------------------ | --------------- | ----------------------------------------- |
| Device Discovery         | Zeroconf / mDNS | Discover devices on the local network     |
| Laptop to Laptop Control | HTTP over TCP   | Connection, pairing and transfer requests |
| Laptop to Laptop Data    | UDP             | Actual file frames and ACKs               |
| Backend to Frontend      | HTTP REST API   | Normal application operations             |
| Backend to Frontend      | WebSocket       | Live transfer visualization               |

---

## 12. Future Enhancements

The following features are outside the initial MVP scope:

* Live chat between connected devices.
* Multiple simultaneous sender and receiver devices.
* Transfer history.
* Advanced performance analytics.
* File transfer over the internet.
* Desktop application packaging.
