# API & WebSocket Documentation

## 1. Overview

This document defines the REST API endpoints and WebSocket events used by the File Transfer System.

The application runs independently on two laptops. Each laptop has its own React frontend and FastAPI backend.

There are two types of REST API communication:

1. **Frontend ↔ Local Backend:** Handles application operations.
2. **Sender Backend ↔ Receiver Backend:** Handles peer-to-peer control communication.

WebSockets are used to deliver real-time transfer events from each laptop's local backend to its frontend.

### Communication Summary

| Communication                     | Technology    | Purpose                         |
| --------------------------------- | ------------- | ------------------------------- |
| Frontend ↔ Local Backend          | HTTP REST     | Application operations          |
| Sender Backend ↔ Receiver Backend | HTTP over TCP | Connection and transfer control |
| Sender Backend ↔ Receiver Backend | UDP           | Actual file frames and ACKs     |
| Backend → Frontend                | WebSocket     | Live transfer visualization     |

**Important:** File data must never be transferred through REST APIs or WebSockets. Actual file frames and ACKs must travel through UDP.

---

## 2. Base URLs

Each laptop runs its own FastAPI backend.

### Local Backend

```text
http://localhost:8000
```

### Peer Backend

```text
http://<peer-ip>:8000
```

### WebSocket

```text
ws://localhost:8000/ws/transfers/{transfer_id}
```

The backend port should be configurable.

---

# 3. Frontend ↔ Local Backend APIs

These endpoints are called by the React frontend.

## 3.1 Device and Connection APIs

| Method | Endpoint                | Purpose                              |
| ------ | ----------------------- | ------------------------------------ |
| GET    | `/api/devices`          | Retrieve discovered devices          |
| POST   | `/api/devices/discover` | Start or refresh device discovery    |
| POST   | `/api/devices/pin`      | Generate a temporary receiver PIN    |
| POST   | `/api/devices/connect`  | Connect using receiver IP and PIN    |
| GET    | `/api/session`          | Retrieve current session information |
| DELETE | `/api/session`          | Disconnect and end the session       |

### Generate PIN

**POST `/api/devices/pin`**

Request:

```json
{}
```

Response:

```json
{
  "success": true,
  "message": "PIN generated successfully",
  "data": {
    "pin": "482193",
    "ip_address": "192.168.1.12",
    "expires_in": 120
  }
}
```

### Connect to Receiver

**POST `/api/devices/connect`**

Request:

```json
{
  "ip_address": "192.168.1.12",
  "pin": "482193"
}
```

Response:

```json
{
  "success": true,
  "message": "Connected successfully",
  "data": {
    "session_id": "session_123",
    "status": "connected",
    "peer": {
      "name": "Laptop B",
      "ip_address": "192.168.1.12",
      "udp_port": 5001
    }
  }
}
```

### Get Current Session

**GET `/api/session`**

Response:

```json
{
  "success": true,
  "data": {
    "session_id": "session_123",
    "status": "connected",
    "local_role": "sender",
    "peer_ip": "192.168.1.12",
    "peer_udp_port": 5001
  }
}
```

---

## 3.2 File APIs

| Method | Endpoint               | Purpose                            |
| ------ | ---------------------- | ---------------------------------- |
| POST   | `/api/files/select`    | Select a file on the sender laptop |
| GET    | `/api/files/{file_id}` | Retrieve selected file information |

### Select File

**POST `/api/files/select`**

The frontend sends the selected file through a local multipart HTTP request. This is only for selecting/registering the file with the local backend, not transferring it to the receiver.

Response:

```json
{
  "success": true,
  "message": "File selected successfully",
  "data": {
    "file_id": "file_123",
    "file_name": "sample.pdf",
    "file_size": 204800,
    "file_type": "application/pdf"
  }
}
```

---

## 3.3 Protocol Configuration APIs

| Method | Endpoint         | Purpose                                 |
| ------ | ---------------- | --------------------------------------- |
| GET    | `/api/protocols` | Retrieve supported ARQ protocols        |
| GET    | `/api/config`    | Retrieve default transfer configuration |
| PUT    | `/api/config`    | Update transfer configuration           |

### Get Available Protocols

**GET `/api/protocols`**

Response:

```json
{
  "success": true,
  "data": {
    "protocols": [
      {
        "id": "stop_and_wait",
        "name": "Stop-and-Wait (One-Bit)"
      },
      {
        "id": "go_back_n",
        "name": "Go-Back-N"
      },
      {
        "id": "selective_repeat",
        "name": "Selective Repeat"
      }
    ]
  }
}
```

### Update Configuration

**PUT `/api/config`**

Request:

```json
{
  "window_size": 4,
  "timeout_ms": 1000,
  "max_retries": 5,
  "packet_loss_percentage": 10
}
```

The backend should validate configuration values according to the selected protocol.

---

## 3.4 Transfer APIs

| Method | Endpoint                              | Purpose                             |
| ------ | ------------------------------------- | ----------------------------------- |
| POST   | `/api/transfers/request`              | Send a transfer request             |
| GET    | `/api/transfers/pending`              | Retrieve incoming transfer requests |
| POST   | `/api/transfers/{transfer_id}/accept` | Accept a transfer                   |
| POST   | `/api/transfers/{transfer_id}/reject` | Reject a transfer                   |
| POST   | `/api/transfers/{transfer_id}/start`  | Start an accepted transfer          |
| GET    | `/api/transfers/{transfer_id}`        | Retrieve transfer details           |
| POST   | `/api/transfers/{transfer_id}/cancel` | Cancel an ongoing transfer          |
| GET    | `/api/transfers/{transfer_id}/report` | Retrieve final transfer statistics  |

### Send Transfer Request

**POST `/api/transfers/request`**

Request:

```json
{
  "file_id": "file_123",
  "protocol": "selective_repeat",
  "configuration": {
    "window_size": 4,
    "timeout_ms": 1000,
    "max_retries": 5,
    "packet_loss_percentage": 10
  }
}
```

Response:

```json
{
  "success": true,
  "message": "Transfer request sent",
  "data": {
    "transfer_id": "transfer_123",
    "status": "pending_acceptance"
  }
}
```

### Get Pending Requests

**GET `/api/transfers/pending`**

Response:

```json
{
  "success": true,
  "data": {
    "transfers": [
      {
        "transfer_id": "transfer_123",
        "file_name": "sample.pdf",
        "file_size": 204800,
        "protocol": "selective_repeat",
        "status": "pending_acceptance"
      }
    ]
  }
}
```

### Accept Transfer

**POST `/api/transfers/{transfer_id}/accept`**

Request:

```json
{}
```

Response:

```json
{
  "success": true,
  "message": "Transfer accepted",
  "data": {
    "transfer_id": "transfer_123",
    "status": "accepted"
  }
}
```

### Reject Transfer

**POST `/api/transfers/{transfer_id}/reject`**

Request:

```json
{
  "reason": "Receiver rejected the transfer"
}
```

Response:

```json
{
  "success": true,
  "message": "Transfer rejected",
  "data": {
    "transfer_id": "transfer_123",
    "status": "rejected"
  }
}
```

### Start Transfer

**POST `/api/transfers/{transfer_id}/start`**

Request:

```json
{}
```

Response:

```json
{
  "success": true,
  "message": "Transfer started",
  "data": {
    "transfer_id": "transfer_123",
    "status": "transferring",
    "protocol": "selective_repeat"
  }
}
```

### Get Transfer Details

**GET `/api/transfers/{transfer_id}`**

Response:

```json
{
  "success": true,
  "data": {
    "transfer_id": "transfer_123",
    "file_name": "sample.pdf",
    "protocol": "selective_repeat",
    "status": "transferring",
    "progress_percentage": 65
  }
}
```

### Cancel Transfer

**POST `/api/transfers/{transfer_id}/cancel`**

Request:

```json
{
  "reason": "User cancelled the transfer"
}
```

Response:

```json
{
  "success": true,
  "message": "Transfer cancellation initiated",
  "data": {
    "transfer_id": "transfer_123",
    "status": "cancelled"
  }
}
```

### Get Transfer Report

**GET `/api/transfers/{transfer_id}/report`**

Response:

```json
{
  "success": true,
  "data": {
    "transfer_id": "transfer_123",
    "status": "completed",
    "protocol": "selective_repeat",
    "total_frames": 120,
    "frames_received": 120,
    "total_acks": 120,
    "total_retransmissions": 8,
    "duration_seconds": 5.4,
    "throughput_kbps": 182.5,
    "integrity_verified": true
  }
}
```

---

# 4. Sender Backend ↔ Receiver Backend APIs

These endpoints are used for direct communication between the two laptops.

They are not called directly by the React frontend.

| Method | Endpoint                               | Purpose                         |
| ------ | -------------------------------------- | ------------------------------- |
| GET    | `/peer/health`                         | Check peer backend availability |
| POST   | `/peer/connect`                        | Request a connection            |
| POST   | `/peer/session`                        | Establish a session             |
| POST   | `/peer/transfers/request`              | Send transfer request           |
| GET    | `/peer/transfers/pending`              | Retrieve pending requests       |
| POST   | `/peer/transfers/{transfer_id}/accept` | Accept transfer                 |
| POST   | `/peer/transfers/{transfer_id}/reject` | Reject transfer                 |
| POST   | `/peer/transfers/{transfer_id}/cancel` | Cancel transfer                 |

### Peer Connection Request

**POST `/peer/connect`**

Request:

```json
{
  "sender_name": "Laptop A",
  "sender_ip": "192.168.1.10"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "status": "connection_accepted",
    "receiver_name": "Laptop B"
  }
}
```

### Session Establishment

**POST `/peer/session`**

Request:

```json
{
  "session_id": "session_123",
  "sender_ip": "192.168.1.10",
  "sender_udp_port": 5002
}
```

Response:

```json
{
  "success": true,
  "data": {
    "session_id": "session_123",
    "receiver_ip": "192.168.1.12",
    "receiver_udp_port": 5001,
    "status": "connected"
  }
}
```

### Peer Transfer Request

**POST `/peer/transfers/request`**

Request:

```json
{
  "session_id": "session_123",
  "transfer_id": "transfer_123",
  "file_name": "sample.pdf",
  "file_size": 204800,
  "protocol": "selective_repeat",
  "configuration": {
    "window_size": 4,
    "timeout_ms": 1000,
    "max_retries": 5
  }
}
```

Response:

```json
{
  "success": true,
  "data": {
    "transfer_id": "transfer_123",
    "status": "pending_acceptance"
  }
}
```

**Note:** Peer endpoints must validate session ownership and transfer state. PIN validation should be part of the pairing process, not repeated for every transfer operation.

---

# 5. WebSocket Documentation

## 5.1 Purpose

WebSockets provide real-time updates from each laptop's local backend to its frontend.

They are used for:

* Connection status updates.
* Incoming transfer notifications.
* Live frame transmission visualization.
* ACK visualization.
* Timeout and retransmission events.
* Transfer progress.
* Completion and failure notifications.

## 5.2 WebSocket Endpoint

```text
ws://localhost:8000/ws/transfers/{transfer_id}
```

Each frontend connects to its own local backend.

Both laptops maintain independent WebSocket connections to their respective backends.

## 5.3 Event Structure

All WebSocket messages should follow a common structure.

```json
{
  "event": "FRAME_SENT",
  "event_id": "event_001",
  "session_id": "session_123",
  "transfer_id": "transfer_123",
  "timestamp": "2026-11-02T12:30:00",
  "data": {}
}
```

| Field       | Description                |
| ----------- | -------------------------- |
| event       | Event name                 |
| event_id    | Unique event identifier    |
| session_id  | Associated session         |
| transfer_id | Associated transfer        |
| timestamp   | Event generation time      |
| data        | Event-specific information |

---

## 5.4 WebSocket Events

### Connection Events

| Event               | Description               |
| ------------------- | ------------------------- |
| CONNECTION_STATUS   | Connection status changes |
| DEVICE_DISCOVERED   | A device is discovered    |
| SESSION_ESTABLISHED | A session is created      |
| SESSION_ENDED       | A session is disconnected |

### Transfer Events

| Event              | Description                     |
| ------------------ | ------------------------------- |
| TRANSFER_REQUEST   | Incoming transfer request       |
| TRANSFER_ACCEPTED  | Receiver accepts transfer       |
| TRANSFER_REJECTED  | Receiver rejects transfer       |
| TRANSFER_STARTED   | File transmission begins        |
| TRANSFER_PROGRESS  | Transfer progress update        |
| TRANSFER_COMPLETED | Transfer successfully completes |
| TRANSFER_FAILED    | Transfer fails                  |
| TRANSFER_CANCELLED | Transfer is cancelled           |

### ARQ and Network Events

| Event               | Description                          |
| ------------------- | ------------------------------------ |
| FRAME_SENT          | Data frame transmitted               |
| FRAME_RECEIVED      | Data frame received                  |
| ACK_SENT            | ACK transmitted                      |
| ACK_RECEIVED        | ACK received                         |
| FRAME_LOST          | Data frame dropped during simulation |
| ACK_LOST            | ACK dropped during simulation        |
| FRAME_CORRUPTED     | Invalid or corrupted frame detected  |
| TIMEOUT             | ACK timeout detected                 |
| FRAME_RETRANSMITTED | Frame retransmitted                  |
| FRAME_BUFFERED      | Out-of-order frame buffered          |
| FRAME_DISCARDED     | Frame discarded                      |
| WINDOW_UPDATED      | Sender or receiver window changes    |

### Integrity Events

| Event                         | Description                     |
| ----------------------------- | ------------------------------- |
| FILE_RECONSTRUCTION_STARTED   | File reconstruction begins      |
| FILE_RECONSTRUCTION_COMPLETED | File reconstruction completes   |
| INTEGRITY_CHECK_STARTED       | SHA-256 verification begins     |
| INTEGRITY_CHECK_COMPLETED     | Integrity verification succeeds |
| INTEGRITY_CHECK_FAILED        | Integrity verification fails    |

---

## 5.5 Example WebSocket Payloads

### FRAME_SENT

```json
{
  "event": "FRAME_SENT",
  "event_id": "event_001",
  "session_id": "session_123",
  "transfer_id": "transfer_123",
  "timestamp": "2026-11-02T12:30:00",
  "data": {
    "sequence_number": 2,
    "payload_size": 1024,
    "protocol": "selective_repeat"
  }
}
```

### FRAME_RECEIVED

```json
{
  "event": "FRAME_RECEIVED",
  "event_id": "event_002",
  "session_id": "session_123",
  "transfer_id": "transfer_123",
  "timestamp": "2026-11-02T12:30:01",
  "data": {
    "sequence_number": 2,
    "payload_size": 1024
  }
}
```

### ACK_SENT

```json
{
  "event": "ACK_SENT",
  "event_id": "event_003",
  "session_id": "session_123",
  "transfer_id": "transfer_123",
  "timestamp": "2026-11-02T12:30:02",
  "data": {
    "ack_number": 2,
    "ack_type": "individual"
  }
}
```

### TIMEOUT

```json
{
  "event": "TIMEOUT",
  "event_id": "event_004",
  "session_id": "session_123",
  "transfer_id": "transfer_123",
  "timestamp": "2026-11-02T12:30:03",
  "data": {
    "sequence_number": 2,
    "retry_count": 1
  }
}
```

### FRAME_RETRANSMITTED

```json
{
  "event": "FRAME_RETRANSMITTED",
  "event_id": "event_005",
  "session_id": "session_123",
  "transfer_id": "transfer_123",
  "timestamp": "2026-11-02T12:30:04",
  "data": {
    "sequence_number": 2,
    "retry_count": 1,
    "protocol": "selective_repeat"
  }
}
```

### TRANSFER_PROGRESS

```json
{
  "event": "TRANSFER_PROGRESS",
  "event_id": "event_006",
  "session_id": "session_123",
  "transfer_id": "transfer_123",
  "timestamp": "2026-11-02T12:30:05",
  "data": {
    "bytes_sent": 102400,
    "total_bytes": 204800,
    "progress_percentage": 50
  }
}
```

### TRANSFER_COMPLETED

```json
{
  "event": "TRANSFER_COMPLETED",
  "event_id": "event_007",
  "session_id": "session_123",
  "transfer_id": "transfer_123",
  "timestamp": "2026-11-02T12:30:06",
  "data": {
    "total_frames": 120,
    "total_retransmissions": 8,
    "integrity_verified": true
  }
}
```

---

# 6. Common API Response Format

All REST API responses should follow a consistent structure.

### Successful Response

```json
{
  "success": true,
  "message": "Operation successful",
  "data": {}
}
```

### Error Response

```json
{
  "success": false,
  "message": "Invalid PIN",
  "error_code": "INVALID_PIN"
}
```

### HTTP Status Codes

| Status Code | Meaning                      |
| ----------- | ---------------------------- |
| 200         | Successful operation         |
| 201         | Resource created             |
| 400         | Invalid request              |
| 401         | Authentication failed        |
| 403         | Operation not permitted      |
| 404         | Resource not found           |
| 409         | Session or transfer conflict |
| 422         | Validation error             |
| 500         | Internal server error        |
| 503         | Peer device unavailable      |

---

# 7. API and WebSocket Design Rules

1. All frontend-facing REST APIs must use the `/api` prefix.
2. Peer-to-peer control APIs must use the `/peer` prefix.
3. File data must never be transferred through REST APIs or WebSockets.
4. UDP must be used for actual file frames and ACKs.
5. WebSockets must be used for live transfer events.
6. Every transfer must be associated with a valid session ID.
7. Request and response structures must be validated using Pydantic.
8. Appropriate HTTP status codes must be returned.
9. Both laptops must run compatible API versions.
10. Peer endpoints must validate session and transfer state.
11. WebSocket events must be generated from actual network and protocol operations.
12. Event IDs must be unique within the application.
13. WebSocket disconnection must not stop the actual file transfer.
14. Frontend should be able to retrieve current transfer status through REST APIs after reconnecting to WebSocket.
15. API endpoint definitions should be maintained centrally to avoid inconsistent implementations.

---

# 8. Implementation Notes

* FastAPI should handle REST endpoints and WebSocket connections.
* Pydantic models should define request and response structures.
* The backend should separate frontend-facing API routes from peer-facing API routes.
* The Network Manager should handle UDP communication independently of REST endpoints.
* WebSocket events should be published through the Visualization Event Manager.
* Transfer state should remain in backend memory during the initial MVP.
* The API contracts may be refined alongside the data model before implementation.

---

# 9. Next Documentation

The next document is **DATA_MODEL.md**.

It will define the structures used internally by the backend:

1. Device Model
2. Session Model
3. Transfer Model
4. File Metadata Model
5. Frame Model
6. ACK Model
7. Sender Window and Receiver Window Models
8. Transfer Statistics Model
9. Visualization Event Model
