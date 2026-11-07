# PeerShare – Single-Laptop Backend Verification Guide

This guide provides complete instructions to verify the PeerShare backend on a **single machine** by running two independent backend instances (Sender and Receiver) with separate API ports, UDP ports, runtime configurations, and isolated file storage directories.

---

## 1. Prerequisites

- **OS**: Linux, macOS, or Windows (WSL recommended)
- **Python**: Version 3.11, 3.12, 3.13, or 3.14
- **Virtual Environment**: Located at `backend/venv`
- **CLI Utilities for Manual Testing**:
  - `curl` (standard HTTP client)
  - `jq` (JSON processor)
  - `websocat` (optional, for CLI WebSocket monitoring: `sudo apt install websocat` or `cargo install websocat`)
  - Alternatively, the browser Developer Tools Console can be used for WebSocket verification.

---

## 2. Environment Setup

The backend utilizes environment variables to isolate two runtime instances on the same machine without code modifications:

| Environment Variable | Instance A (Receiver) | Instance B (Sender) | Description |
|---|---|---|---|
| `PEERSHARE_API_PORT` | `8000` | `8001` | FastAPI HTTP & WebSocket port |
| `PEERSHARE_UDP_PORT` | `5001` | `5002` | UDP port for binary frames & ACKs |
| `PEERSHARE_ROLE` | `RECEIVER` | `SENDER` | Operational role |
| `PEERSHARE_DEVICE_NAME`| `ReceiverLaptop` | `SenderLaptop` | Device display name |
| `PEERSHARE_STORAGE_DIR`| `/tmp/peershare_receiver` | `/tmp/peershare_sender` | Local filesystem storage path |

Create the isolated storage directories:
```bash
mkdir -p /tmp/peershare_receiver /tmp/peershare_sender
```

---

## 3. Startup Commands for Both Instances

Open two independent terminal windows.

### Terminal 1: Receiver Instance (Port 8000 / UDP 5001)
```bash
cd backend
source venv/bin/activate

export PEERSHARE_API_PORT=8000
export PEERSHARE_UDP_PORT=5001
export PEERSHARE_ROLE=RECEIVER
export PEERSHARE_STORAGE_DIR=/tmp/peershare_receiver
export PEERSHARE_DEVICE_NAME=ReceiverLaptop

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Terminal 2: Sender Instance (Port 8001 / UDP 5002)
```bash
cd backend
source venv/bin/activate

export PEERSHARE_API_PORT=8001
export PEERSHARE_UDP_PORT=5002
export PEERSHARE_ROLE=SENDER
export PEERSHARE_STORAGE_DIR=/tmp/peershare_sender
export PEERSHARE_DEVICE_NAME=SenderLaptop

uvicorn app.main:app --host 0.0.0.0 --port 8001
```

---

## 4. Automated Testing Commands

Before running manual tests, run the comprehensive backend automated test suite (114 unit and integration tests):

```bash
cd backend
source venv/bin/activate
pytest -v
```

### Run Specific Subsystem Test Suites
- **Wire Protocol & CRC32 (Phase 2)**:
  ```bash
  pytest tests/test_frame.py tests/test_ack.py tests/test_checksum.py tests/test_sequence.py -v
  ```
- **ARQ Protocol Engines (Phase 3)**:
  ```bash
  pytest tests/test_stop_and_wait.py tests/test_go_back_n.py tests/test_selective_repeat.py tests/test_simulator.py -v
  ```
- **Real UDP Transport (Phase 4)**:
  ```bash
  pytest tests/test_udp_basic.py tests/test_udp_arq.py tests/test_udp_process.py -v
  ```
- **Discovery & Session Management (Phase 5)**:
  ```bash
  pytest tests/test_phase5_discovery_session.py -v
  ```
- **File Transfer & SHA-256 Integrity (Phase 6)**:
  ```bash
  pytest tests/test_phase6_file_transfer.py -v
  ```
- **REST APIs, WebSockets & Single-Laptop Integration (Phase 7)**:
  ```bash
  pytest tests/test_phase7_api_and_websocket.py -v
  ```

---

## 5. API Testing & Health Checks

Open a third terminal for running API tests via `curl`.

### Check Receiver Health
```bash
curl -s http://localhost:8000/peer/health | jq .
```
Expected output:
```json
{
  "success": true,
  "message": "Operation successful",
  "data": {
    "api_version": "1.0.0",
    "device_id": "...",
    "device_name": "ReceiverLaptop",
    "role": "RECEIVER"
  }
}
```

### Check Sender Network Status
```bash
curl -s http://localhost:8001/api/network/status | jq .
```
Expected output:
```json
{
  "success": true,
  "message": "Operation successful",
  "data": {
    "local_ip": "127.0.0.1",
    "api_port": 8001,
    "udp_port": 5002,
    "role": "SENDER"
  }
}
```

---

## 6. Device Discovery and Pairing Verification

### Option A: Automatic Zeroconf Discovery
1. The Receiver starts advertising automatically upon boot or when `POST /api/role` is set to `RECEIVER`.
2. On Sender (Terminal 3):
   ```bash
   # Trigger discovery
   curl -s -X POST http://localhost:8001/api/devices/discover | jq .

   # View discovered receivers
   curl -s http://localhost:8001/api/devices | jq .
   ```

### Option B: Manual IP + PIN Pairing (Recommended for Localhost)
1. **Generate 6-digit PIN on Receiver**:
   ```bash
   curl -s -X POST http://localhost:8000/api/devices/pin | jq .
   ```
   Save the returned PIN (e.g. `"482193"`).

2. **Submit Connection Request from Sender**:
   ```bash
   curl -s -X POST http://localhost:8001/api/devices/connect \
     -H "Content-Type: application/json" \
     -d '{
       "ip_address": "127.0.0.1",
       "api_port": 8000,
       "pin": "<PIN>"
     }' | jq .
   ```
   Response indicates `"status": "pending_approval"` and returns a `connection_id`.

3. **Receiver Reviews Pending Requests**:
   ```bash
   curl -s http://localhost:8000/api/connections/pending | jq .
   ```

4. **Receiver Approves Connection**:
   ```bash
   curl -s -X POST http://localhost:8000/api/connections/<CONNECTION_ID>/approve | jq .
   ```

5. **Sender Establishes Mutual Session**:
   ```bash
   curl -s -X POST http://localhost:8001/api/session/establish \
     -H "Content-Type: application/json" \
     -d '{
       "target_ip": "127.0.0.1",
       "target_port": 8000
     }' | jq .
   ```
   Both backends now share an established session with UDP ports exchanged (`5001` on Receiver, `5002` on Sender) and an active `session_token`.

6. **Verify Session on Both Sides**:
   ```bash
   curl -s http://localhost:8000/api/session | jq .
   curl -s http://localhost:8001/api/session | jq .
   ```

---

## 7. Real-Time WebSocket Event Monitoring

Open a fourth terminal to monitor live visualization events pushed by the backend.

### Monitor Receiver Events
```bash
websocat ws://localhost:8000/ws/events
```

### Monitor Sender Events
```bash
websocat ws://localhost:8001/ws/events
```

*Note: Alternatively, open your browser Console on `http://localhost:8001` and run:*
```javascript
const ws = new WebSocket("ws://localhost:8001/ws/events");
ws.onmessage = (e) => console.log("LIVE EVENT:", JSON.parse(e.data));
```

---

## 8. File Transfer & ARQ Protocol Testing

### Step 1: Prepare Test Files

Create three test files on the Sender:
```bash
# 1. Small file (under 1024 B, single chunk)
echo "Small file payload for single-laptop verification." > /tmp/peershare_sender/small.txt

# 2. Multi-chunk file (4 KB -> 4 chunks)
head -c 4096 /dev/urandom > /tmp/peershare_sender/test_4kb.bin

# 3. Empty file (0 bytes)
touch /tmp/peershare_sender/empty.txt

# 4. Maximum permitted file size (exact 5 MB limit)
head -c 5242880 /dev/urandom > /tmp/peershare_sender/exact_5mb.bin
```

### Step 2: Upload File to Sender Instance
Upload the multi-chunk file (`test_4kb.bin`):
```bash
curl -s -X POST http://localhost:8001/api/files/select \
  -F "file=@/tmp/peershare_sender/test_4kb.bin" | jq .
```
Save the returned `"file_id"` and `"file_sha256"`.

### Step 3: Test ARQ Protocols & Loss Configurations

You can test any of the three ARQ protocols and inject simulated packet loss:

#### A. Stop-and-Wait ARQ (Lossless)
```bash
curl -s -X POST http://localhost:8001/api/transfers/request \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "<FILE_ID>",
    "protocol": "stop_and_wait",
    "configuration": {
      "window_size": 1,
      "timeout_ms": 150,
      "max_retries": 5,
      "packet_loss_percentage": 0,
      "frame_delay_ms": 30
    }
  }' | jq .
```
Save the returned `"transfer_id"`.

#### B. Go-Back-N ARQ (With 10% Simulated Loss)
```bash
curl -s -X POST http://localhost:8001/api/transfers/request \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "<FILE_ID>",
    "protocol": "go_back_n",
    "configuration": {
      "window_size": 4,
      "timeout_ms": 200,
      "max_retries": 10,
      "packet_loss_percentage": 10.0,
      "frame_delay_ms": 50
    }
  }' | jq .
```

#### C. Selective Repeat ARQ (With 20% Simulated Loss)
```bash
curl -s -X POST http://localhost:8001/api/transfers/request \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "<FILE_ID>",
    "protocol": "selective_repeat",
    "configuration": {
      "window_size": 8,
      "timeout_ms": 150,
      "max_retries": 10,
      "packet_loss_percentage": 20.0,
      "frame_delay_ms": 40
    }
  }' | jq .
```

### Step 4: Accept and Start Transfer

1. **Receiver Accepts Transfer**:
   ```bash
   curl -s -X POST http://localhost:8000/api/transfers/<TRANSFER_ID>/accept | jq .
   ```
   The Receiver binds to UDP port 5001 and signals ready to the Sender.

2. **Sender Starts Transmission**:
   ```bash
   curl -s -X POST http://localhost:8001/api/transfers/<TRANSFER_ID>/start | jq .
   ```
   Binary frames are transmitted from UDP port 5002 to UDP port 5001.

3. **Observe Live Events in Terminal 4**:
   - `FRAME_SENT` with `sequence_number` and `frame_index`
   - `FRAME_RECEIVED` upon arrival
   - `ACK_SENT` and `ACK_RECEIVED`
   - `FRAME_LOST` and `TIMEOUT` when simulated loss drops frames
   - `FRAME_RETRANSMITTED` as ARQ recovers missing packets
   - `FRAME_BUFFERED` in Selective Repeat out-of-order buffering
   - `WINDOW_UPDATED` and `TRANSFER_PROGRESS` percentage
   - `INTEGRITY_CHECK_COMPLETED`
   - `TRANSFER_COMPLETED`

### Step 5: Verify File Reconstruction & SHA-256 Hash

1. **Query Final Transfer Report**:
   ```bash
   curl -s http://localhost:8001/api/transfers/<TRANSFER_ID>/report | jq .
   ```
   Verify `"integrity_verified": true` and inspect throughput statistics.

2. **Verify Bit-for-Bit Identity on Disk**:
   ```bash
   sha256sum /tmp/peershare_sender/test_4kb.bin
   sha256sum /tmp/peershare_receiver/test_4kb.bin
   ```
   Both hexadecimal SHA-256 hashes must be completely identical.

---

## 9. Edge-Case Verification

### 1. Small File Transfer (< 1024 Bytes)
Repeat Steps 2–5 with `/tmp/peershare_sender/small.txt`. Verifies single-frame transmission and reconstruction.

### 2. Maximum Permitted File Size (5 MB Limit)
Upload `/tmp/peershare_sender/exact_5mb.bin`. Verifies 5120 frames transfer across UDP sockets, sliding window wraparound past sequence number 65535, and SHA-256 matching.

### 3. File Size Cap Rejection (> 5 MB)
Attempt to select a file of 5.1 MB:
```bash
head -c 5342880 /dev/urandom > /tmp/peershare_sender/oversized.bin
curl -s -X POST http://localhost:8001/api/files/select \
  -F "file=@/tmp/peershare_sender/oversized.bin" | jq .
```
Expected HTTP response: `413 Payload Too Large` with `"File too large (exceeds 5 MB limit)"`.

### 4. Empty File Transfer (0 Bytes)
Upload `/tmp/peershare_sender/empty.txt` and transfer. Verifies 0-frame FIN / FIN-ACK exchange and creation of a verified 0-byte file on Receiver.

### 5. Path Traversal Rejection
```bash
curl -s -X POST http://localhost:8000/peer/transfers/request \
  -H "Content-Type: application/json" \
  -d '{"session_id":"...", "file_name":"../../etc/passwd", ...}' | jq .
```
Filename is sanitized and path traversal sequences are rejected.

---

## 10. Troubleshooting

| Issue | Cause | Resolution |
|---|---|---|
| `Address already in use` | Another process is using port 8000 or 8001 | Check with `lsof -i :8000 -i :8001` and terminate existing processes. |
| `Access forbidden: /api/* is local only` | Calling `/api/*` from a remote IP | `/api/*` endpoints are strictly local to loopback (`127.0.0.1`). |
| `PIN validation failed: PIN expired` | More than 120 seconds elapsed | Generate a new PIN on the Receiver using `POST /api/devices/pin`. |
| `PIN validation failed: Max failed attempts reached` | 5 failed attempts triggered lockout | Restart the Receiver backend or wait for lockout cooldown. |
| `Missing X-Session-Token header` | Calling protected `/peer/*` without token | Include `-H "X-Session-Token: <token>"` obtained during session establishment. |
| `Sender timeout or retry limit exceeded` | Receiver was not accepted before sender start | Always call `POST /api/transfers/<ID>/accept` on the Receiver before starting the Sender. |

---

## 11. Verification Summary: Single Laptop vs. Two Physical Laptops

### Fully Verified on a Single Laptop
- Independent Sender and Receiver processes on separate API and UDP ports.
- Manual IP and 6-digit PIN pairing with constant-time validation and lockout.
- Mutual session creation, UDP port exchange, and cryptographic session token authentication.
- All three ARQ protocols (Stop-and-Wait, Go-Back-N, Selective Repeat) over real UDP sockets.
- Configurable per-frame delay pacing (`frame_delay_ms`).
- Deterministic and seeded packet-loss simulation (data frame and ACK drops).
- Sequence number circular wraparound (modulo 65536) and out-of-order buffering.
- CRC32 frame checksumming and bit-flip detection.
- Complete file chunking (1024 B), reconstruction, and SHA-256 integrity verification.
- Edge cases: 0-byte empty files, < 1024 B files, and exact 5 MB files.
- Real-time WebSocket event emission (`FRAME_SENT`, `ACK_RECEIVED`, `PROGRESS`, etc.).
- Monotonic sequence numbering and ring-buffer event replay.

### Requires Two Physical Laptops
- Actual LAN Wi-Fi Zeroconf/mDNS advertisement across two separate physical network interfaces (some OS firewalls or campus Wi-Fi networks block multicast DNS).
- Physical network latency and natural packet jitter over Wi-Fi.
- Campus Wi-Fi client isolation fallback testing (demonstrating manual IP + PIN fallback when client-to-client communication is restricted by router policies).
