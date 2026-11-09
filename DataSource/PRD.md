# Product Requirements Document (PRD)

## 1. Project Overview

The project aims to develop a laptop-to-laptop file transfer application that demonstrates three reliable data transmission techniques: One-Bit (Stop-and-Wait), Go-Back-N, and Selective Repeat.

Unlike conventional protocol simulations that demonstrate transmission within a single system, this application enables two physical laptops connected to the same local network to exchange files.

The application will also provide a live visualization of the underlying networking process, allowing users to understand how data frames are transmitted, acknowledged, lost, and retransmitted using different techniques.

## 2. Problem Statement

Most academic simulations of data transmission protocols demonstrate their working through static diagrams or simulated environments on a single machine.

This limits the ability to understand how these protocols operate during an actual communication process between two devices.

There is a need for an interactive application that combines real file transfer between two laptops with a visualization of the underlying data transmission techniques.

## 3. Proposed Solution

Develop a laptop-to-laptop file transfer application where two users connected to the same local network can exchange files using three different reliable data transmission techniques.

The application will provide:

* Real-time file transfer between two physical laptops.
* Support for One-Bit (Stop-and-Wait), Go-Back-N, and Selective Repeat protocols.
* QR code or connection code-based device pairing.
* Sender and receiver interfaces.
* Live visualization of frame transmission, acknowledgements (ACKs), packet loss, and retransmissions.
* A representation of the underlying networking process on both devices.
* Transfer completion status and file integrity verification.

## 4. Target Audience

**Primary Users:**

* Computer Science and Engineering students.
* Students studying Computer Networks.
* Faculty members interested in demonstrating reliable data transmission protocols.

**Secondary Users:**

* Anyone interested in understanding networking and data transmission concepts.

## 5. MVP Scope

The Minimum Viable Product will focus on establishing a working file transfer system between two physical laptops.

### User Roles

1. **Sender:** Selects files, chooses the transmission technique, and initiates the transfer.
2. **Receiver:** Connects to the sender, reviews incoming file requests, and accepts or rejects transfers.

### Core Features

* Sender and receiver role selection.
* Local network connectivity verification.
* QR code or connection code generation and scanning.
* Device pairing and session establishment.
* File selection and transfer configuration.
* Support for all three transmission techniques:

  * One-Bit (Stop-and-Wait).
  * Go-Back-N.
  * Selective Repeat.
* Receiver-side transfer approval.
* Live visualization of the transmission process on both devices.
* Display of frames, ACKs, packet loss, and retransmissions.
* File reconstruction and integrity verification after transfer.
* Transfer status and basic performance statistics.

### User Flow

The application will follow two separate user journeys:

**Sender Flow:**

1. Open the application and select Sender.
2. Verify network connectivity.
3. discover nearby receivers (or enter IP + PIN)
4. Wait for the receiver to connect.
5. Select the file to transfer.
6. Choose the transmission technique and configuration.
7. Send the transfer request.
8. Wait for receiver approval.
9. Initiate file transfer.
10. View the live transmission visualization.

**Receiver Flow:**

1. Open the application and select Receiver.
2. Verify network connectivity.
3. wait visible to nearby senders (PIN and IP shown for fallback)
4. Establish a connection with the sender.
5. Wait for the incoming transfer request.
6. Review file details and accept or reject the request.
7. Receive the file.
8. View the live transmission visualization.

Both devices will display synchronized visualizations of the underlying transmission process.

## 6. Assumptions and Constraints

* Both laptops must be connected to the same local network.
* The application will initially support communication between two devices.
* Files will be transferred for demonstration and educational purposes.
* The three transmission techniques will be implemented and demonstrated independently.
* Packet loss and transmission errors may be simulated to demonstrate retransmission mechanisms.
* The application is intended as an academic demonstration rather than a production-grade file-sharing service.

## 7. Future Scope

Features that can be considered for future development:

* Live chat between the sender and receiver.
* Multiple-device file sharing.
* Transfer history and session management.
* Performance comparison between the three protocols.
* Advanced network statistics and analytics.
* Custom packet loss and network delay configuration.
* Support for larger files and multiple simultaneous transfers.

## 8. Expected Outcome

The final application should demonstrate successful file transfer between two physical laptops while providing an interactive representation of how different reliable data transmission techniques work.

Users should be able to observe and compare the behaviour of One-Bit, Go-Back-N, and Selective Repeat during actual file transfer scenarios, gaining a practical understanding of the concepts covered in Computer Networks.
