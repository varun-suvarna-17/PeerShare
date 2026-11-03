# PeerShare – Implementation Plan

## Development Strategy

PeerShare will be developed using a phase-by-phase approach.

The project follows a modular monolithic architecture. Networking logic, ARQ protocols, API endpoints, and visualization will be implemented as separate modules within the same backend application.

### Development Principles

* Implement and test the networking core before building the UI.
* Use actual UDP communication and ACK events.
* Never use dummy animations to represent network activity.
* Keep the implementation simple and avoid unnecessary abstractions.
* Complete and test each phase before proceeding.
* Follow the existing PRD, TRD, System Architecture, API Documentation, Data Model, and Design System.

---

## Phase 1 – Project Setup

**Objective:** Establish the frontend and backend development environments.

Tasks:

* Create the project directory structure.
* Initialise the React + TypeScript frontend.
* Initialise the Python + FastAPI backend.
* Configure Tailwind CSS.
* Configure React Router and Zustand.
* Configure Axios and WebSocket client utilities.
* Configure Python virtual environment.
* Install and verify backend dependencies.
* Configure environment variables.
* Verify frontend and backend run independently.

Deliverable:

* Working frontend and backend development environments.

---

## Phase 2 – Network Protocol Foundation

**Objective:** Implement the fundamental binary frame structure used for UDP communication.

Tasks:

* Define binary frame format.
* Implement frame encoding and decoding.
* Implement sequence number handling.
* Implement CRC32 generation and validation.
* Implement ACK encoding and decoding.
* Handle invalid and corrupted frames.
* Write unit tests for encoding, decoding and validation.

Deliverable:

* A tested networking protocol module capable of creating and interpreting frames.

---

## Phase 3 – ARQ Protocol Implementation

**Objective:** Implement all three ARQ protocols independently of actual network communication.

Tasks:

### 3.1 Stop-and-Wait ARQ

* Implement one-bit sequence numbering.
* Implement sender and receiver logic.
* Implement ACK handling.
* Implement timeout and retransmission.

### 3.2 Go-Back-N ARQ

* Implement sender sliding window.
* Implement cumulative ACK handling.
* Implement receiver logic.
* Implement timeout and retransmission of outstanding frames.

### 3.3 Selective Repeat ARQ

* Implement sender and receiver sliding windows.
* Implement individual ACK handling.
* Implement out-of-order frame buffering.
* Implement individual frame timers and retransmissions.

### 3.4 Testing

* Test all protocols using an in-memory simulated network.
* Simulate data-frame and ACK loss.
* Test corrupted frames.
* Test timeout and retransmission behaviour.
* Test different window sizes and loss percentages.

Deliverable:

* Three independently tested ARQ protocol implementations.

---

## Phase 4 – Real UDP Communication

**Objective:** Connect the ARQ implementations to actual UDP sockets.

Tasks:

* Implement asynchronous UDP communication.
* Implement sender and receiver UDP handlers.
* Connect ARQ logic to UDP frame transmission.
* Implement ACK transmission and reception.
* Implement timeout handling using actual network events.
* Implement configurable frame delay.
* Implement seeded packet-loss simulation.
* Track actual transmission and retransmission statistics.
* Test communication between two separate processes.

Deliverable:

* Working UDP file-transfer communication between two backend instances.

---

## Phase 5 – Device Discovery and Session Management

**Objective:** Allow two laptops to discover each other and establish a transfer session.

Tasks:

* Implement device discovery using Zeroconf/mDNS.
* Advertise receiver availability.
* Allow sender to discover available receivers.
* Implement manual IP and PIN fallback.
* Generate and validate temporary connection PINs.
* Implement connection approval on receiver.
* Establish a secure session using a session token.
* Exchange UDP port information.
* Implement receiver-ready signalling.
* Handle session expiry and disconnection.

Deliverable:

* Two laptops can discover each other, establish a session and prepare for file transfer.

---

## Phase 6 – File Transfer and Integrity

**Objective:** Implement complete file transfer using the selected ARQ protocol.

Tasks:

* Implement file selection and metadata extraction.
* Implement file chunking.
* Calculate SHA-256 checksum.
* Send file chunks through the selected ARQ protocol.
* Reconstruct the received file.
* Implement transfer completion using FIN/FIN-ACK.
* Verify file integrity using SHA-256.
* Handle failed and interrupted transfers.
* Enforce file size and filename validation.

Deliverable:

* Complete file transfer between two laptops with integrity verification.

---

## Phase 7 – Backend API and Visualization Events

**Objective:** Expose backend functionality to the frontend.

Tasks:

* Implement REST API endpoints according to API_DOCUMENTATION.md.
* Implement device discovery and connection endpoints.
* Implement transfer creation and control endpoints.
* Implement WebSocket communication.
* Generate visualization events from actual networking operations.
* Implement event sequence numbering and replay buffer.
* Expose frame transmission, ACK, timeout, loss and retransmission events.
* Implement transfer progress and statistics updates.
* Test REST and WebSocket communication.

Deliverable:

* Fully functional backend accessible through REST APIs and WebSockets.

---

## Phase 8 – Frontend Implementation

**Objective:** Build the complete user interface using the approved design system.

Tasks:

### 8.1 Application Foundation

* Implement application routing.
* Implement global state using Zustand.
* Configure API and WebSocket clients.
* Implement reusable UI components.
* Apply the approved Design System.

### 8.2 Dashboard

* Implement dashboard layout.
* Display device status.
* Display recent transfers.
* Provide navigation.

### 8.3 Device Discovery and Connection

* Display discovered devices.
* Implement manual IP fallback.
* Implement connection request and approval UI.
* Display session status.

### 8.4 File Transfer

* Implement file selection.
* Implement protocol selection.
* Implement transfer configuration.
* Display transfer progress.

### 8.5 Network Visualization

* Visualise sender and receiver.
* Display frame transmission.
* Display ACK reception.
* Display packet loss.
* Display timeout and retransmission.
* Display sliding-window movement.
* Update visualisation using real WebSocket events.

### 8.6 Transfer Results

* Display transfer completion.
* Display integrity verification.
* Display transfer statistics.

Deliverable:

* Complete frontend integrated with the backend.

---

## Phase 9 – Integration and Testing

**Objective:** Validate the complete application using two physical laptops.

Tasks:

* Run the application on both laptops.
* Verify device discovery.
* Verify connection approval.
* Test all three ARQ protocols.
* Test different packet-loss percentages.
* Test corrupted frames.
* Test timeout and retransmission.
* Verify sliding-window behaviour.
* Verify file reconstruction.
* Verify SHA-256 integrity.
* Test disconnection and recovery.
* Verify visualization against actual network events.
* Fix integration and performance issues.

Deliverable:

* A working and tested laptop-to-laptop file transfer application.

---

## Phase 10 – Finalisation

**Objective:** Prepare the project for demonstration and submission.

Tasks:

* Improve error handling.
* Refine the UI.
* Add useful logging.
* Clean up the codebase.
* Update project documentation.
* Prepare demonstration scenarios.
* Capture screenshots and network traces.
* Prepare the final project presentation.

Deliverable:

* Final PeerShare project ready for demonstration.

---

## Important Development Rule

Do not ask the coding agent to implement multiple phases at once.

For every phase:

1. Read the relevant project documentation.
2. Implement only the current phase.
3. Run the required tests.
4. Report completed work and test results.
5. Fix issues before proceeding.

The coding agent must not independently change the agreed architecture, protocol conventions, API contracts or data models without explaining the reason and obtaining approval.
