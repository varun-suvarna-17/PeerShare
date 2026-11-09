# Technical Requirements Document (TRD)

## 1. System Architecture

The application follows a **Modular Monolithic Architecture**, where the backend is divided into independent logical modules based on their responsibilities.

The system consists of two physical laptops connected through the same local network. Both laptops run the same application, with one operating as the Sender and the other as the Receiver.

Each laptop contains:

* A React-based frontend.
* A Python-based backend.
* A protocol implementation module.
* A UDP-based network communication module.
* A real-time visualization component.

### Architecture Layers

**1. Presentation Layer**

* React frontend.
* Sender and Receiver interfaces.
* Transfer visualization.
* Application state management.

**2. Application Layer**

* API management.
* Connection and session management.
* File management.
* Visualization event management.

**3. Protocol Layer**

* Stop-and-Wait implementation.
* Go-Back-N implementation.
* Selective Repeat implementation.
* Sending and receiving window management.
* Acknowledgement handling.
* Timeout and retransmission management.

**4. Network Layer**

* UDP socket communication.
* Frame transmission and reception.
* Acknowledgement transmission.
* Network-level communication between laptops.

### Communication Architecture

| Communication               | Technology     |
| --------------------------- | -------------- |
| Frontend ↔ Backend          | HTTP REST APIs |
| Backend → Frontend          | WebSocket      |
| Laptop ↔ Laptop (Control)   | HTTP over TCP  |
| Laptop ↔ Laptop (File Data) | UDP            |

Both laptops run their own backend instances and communicate directly over the local network.

---

## 2. Technology Stack

### Frontend

| Technology    | Purpose                    |
| ------------- | -------------------------- |
| React.js      | User interface development |
| TypeScript    | Type safety                |
| Tailwind CSS  | UI styling                 |
| Zustand       | Global state management    |
| React Router  | Application navigation     |
| Axios         | REST API communication     |
| WebSocket API | Real-time event updates    |
| Motion        | Frame and ACK animations   |
| Lucide React  | Icons                      |

### Backend

| Technology | Purpose                                    |
| ---------- | ------------------------------------------ |
| Python     | Backend development                        |
| FastAPI    | REST API and WebSocket handling            |
| Uvicorn    | ASGI server                                |
| Pydantic   | Data validation                            |
| asyncio    | Asynchronous processing                    |
| socket     | UDP communication                          |
| struct     | Binary frame encoding and decoding         |
| hashlib    | SHA-256 file integrity verification        |
| uuid       | Session identification                     |
| logging    | Application logging                        |
| qrcode     | Not required in the initial implementation |

### Additional Libraries and Tools

| Technology   | Purpose                        |
| ------------ | ------------------------------ |
| Zeroconf     | Local network device discovery |
| pytest       | Backend testing                |
| Wireshark    | Network packet inspection      |
| Git & GitHub | Version control                |

---

## 3. Module Breakdown

| Module                      | Responsibility                                           |
| --------------------------- | -------------------------------------------------------- |
| Frontend Module             | Sender and Receiver interfaces                           |
| Connection Manager          | Device discovery and session management                  |
| File Manager                | File selection, reading, chunking and reconstruction     |
| Protocol Engine             | Implements the three ARQ techniques                      |
| Transmission Manager        | Controls frame transmission and sending windows          |
| ACK Handler                 | Processes acknowledgements                               |
| Timer Manager               | Handles timeouts and retransmission triggers             |
| Network Manager             | Manages UDP socket communication                         |
| Frame Handler               | Frame encoding, decoding and validation                  |
| Visualization Event Manager | Generates events based on actual transmission operations |
| WebSocket Manager           | Delivers real-time events to the frontend                |
| Integrity Manager           | Verifies file integrity using SHA-256                    |

---

## 4. Functional Requirements

### Connection Management

* FR1: Users should be able to select Sender or Receiver mode.
* FR2: The application should discover available devices on the local network using Zeroconf.
* FR3: The receiver should be able to select an available sender.
* FR4: The application should establish a communication session between the devices.
* FR5: The application should provide manual IP-based connection as a fallback.

### File Management

* FR6: The sender should be able to select a file for transfer.
* FR7: The application should divide files into smaller frames.
* FR8: The receiver should reconstruct the original file after receiving all required frames.
* FR9: The application should verify the integrity of the transferred file.

### Protocol Implementation

* FR10: The application should support Stop-and-Wait, Go-Back-N and Selective Repeat.
* FR11: The sender should be able to select the transmission technique.
* FR12: The application should implement sequence numbering and acknowledgements.
* FR13: The application should handle timeouts and retransmissions.
* FR14: The application should demonstrate packet loss and recovery mechanisms.

### Transfer Management

* FR15: The sender should be able to initiate a file transfer request.
* FR16: The receiver should be able to accept or reject incoming requests.
* FR17: Both devices should display the current transfer status.
* FR18: The application should notify users when a transfer is completed or interrupted.

### Visualization

* FR19: The application should display live frame transmission.
* FR20: The application should visualize ACK transmission and reception.
* FR21: The application should display packet loss and retransmissions.
* FR22: Both devices should display visualization events corresponding to actual network operations.

---

## 5. Non-Functional Requirements

* **Reliability:** The application should reconstruct transferred files correctly.
* **Performance:** Frame transmission and acknowledgement handling should be efficient.
* **Usability:** The interface should be simple and understandable.
* **Synchronization:** Both devices should display consistent transmission events.
* **Maintainability:** Backend components should have clearly separated responsibilities.
* **Compatibility:** The application should support communication between two laptops connected to the same local network.

---

## 6. Network Communication Design

The application will use UDP for actual file data transmission and implement reliability through the three ARQ techniques.

### Frame Structure

Each transmitted frame will contain relevant metadata:

* Frame type.
* Sequence number.
* Acknowledgement number, where applicable.
* Payload length.
* File data.

### Protocol Implementation

**Stop-and-Wait (One-Bit):**

* Transmits one frame at a time.
* Waits for an acknowledgement before sending the next frame.
* Retransmits when a timeout occurs.

**Go-Back-N:**

* Allows multiple outstanding frames within a sending window.
* Uses cumulative acknowledgements.
* Retransmits the missing frame and subsequent outstanding frames when required.

**Selective Repeat:**

* Allows multiple outstanding frames.
* Uses individual acknowledgements.
* Buffers correctly received out-of-order frames.
* Retransmits only missing or unacknowledged frames.

### Network Communication

* UDP sockets will handle frame transmission and reception.
* ACKs will travel as actual UDP datagrams between devices.
* Timeouts and retransmissions will be managed by the protocol implementation.
* Packet loss can be introduced through a configurable simulation mechanism for demonstration.

### File Integrity

After transfer completion, the application will calculate SHA-256 hashes of the original and reconstructed files to verify their integrity.

---

## 7. Error Handling

The application should account for the following situations:

* Device discovery failure.
* Connection establishment timeout.
* Receiver disconnection.
* Transfer request rejection.
* Frame loss.
* ACK loss.
* Duplicate frame reception.
* Out-of-order frame reception.
* Retransmission failure.
* File reconstruction failure.
* File integrity verification failure.

The application should provide appropriate notifications and handle recoverable errors wherever possible.

---

## 8. Testing Requirements

The application will be tested in the following scenarios:

* Connection establishment between two physical laptops.
* Successful file transfer using all three protocols.
* File integrity verification.
* Packet loss and retransmission behaviour.
* ACK loss and duplicate frame handling.
* Out-of-order frame reception.
* Performance comparison between the three techniques.
* Synchronization of visualization events on both devices.

Wireshark can additionally be used to inspect UDP packets and verify actual network communication.

---

## 9. Future Technical Enhancements

* Live chat between connected devices.
* Multiple-device communication.
* Transfer history.
* Advanced network performance analytics.
* Internet-based file transfer.
* Desktop application packaging.
