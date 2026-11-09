# AMENDMENTS.md – Changes to PRD, TRD, System, Network Flow and API Docs

## 0. Precedence rule (read first)

This document **overrides** `prd.md`, `trd.md`, `system.md`, `netwrk.md` and `api.md` wherever they conflict with it.
If something here contradicts an older doc, this document wins. Do not "reconcile" by following the older text.
Items marked **[CONFIRMED]** are decided. Items marked **[PROPOSED]** are recommended defaults, to be confirmed by the project owner before implementation.

---

## 1. Locked decisions

### 1.1 Connection model [CONFIRMED]
- **QR codes and "connection codes" are removed from the project.** No `qrcode` library, no scanning.
- **Primary: Zeroconf (mDNS/DNS-SD) discovery.** The *receiver* advertises itself; the *sender* discovers nearby receivers and selects one.
- **Fallback: manual IP + 6-digit PIN.** The receiver displays its IP and a temporary PIN; the sender enters both.
- Direction is fixed: **receiver is connected to; sender initiates.** Any text saying the receiver selects a sender, or the sender generates a code, is wrong.

### 1.2 Connection authorization [PROPOSED]
- Zeroconf connections carry no PIN, so **the receiver user must approve every incoming connection** (accept/reject prompt).
- PIN path: PIN validated by the receiver backend, then the same approval step applies.
- PIN rules: 6 digits, expires in 120 s, single use, **max 5 failed attempts then lockout**, constant-time compare.
- After pairing, the receiver issues a **session token**. All later `/peer/*` calls must send it (header `X-Session-Token`). Peer IP is taken from the connection (`request.client.host`), never from the request body.

### 1.3 Network exposure [PROPOSED]
- `/api/*` (frontend-facing) must be reachable **from localhost only**.
- `/peer/*` is the only surface exposed to the LAN.
- Either use two ports (e.g. 8000 local-only, 8001 LAN) or one port with middleware rejecting non-loopback clients on `/api/*`.

### 1.4 Scope limits [PROPOSED]
- One active transfer per session. Roles are fixed per session (sender stays sender).
- **Max file size: 5 MB** for the MVP (keeps 16-bit sequence numbers from wrapping at 1024-byte payloads and keeps event volume sane). Reject larger files at file-select time.
- **Demo pacing:** add a configurable per-frame send delay (`frame_delay_ms`, default 100) so visualizations are watchable. Without it, a LAN transfer finishes before the animation can be read. This moves from "Future Scope" into the MVP.
- Supported OS and Python version must be stated in the README (suggest Python 3.11+; Windows, macOS, Linux).

---

## 2. Changes per document

### 2.1 prd.md
1. Remove all QR / connection-code wording (solution bullets, core features, both user flows).
2. Replace the user flows with:
   - **Receiver:** open app → select Receiver → verify network → appear to nearby senders (IP + PIN shown for fallback) → approve incoming connection → review transfer request → accept/reject → receive → view visualization → see report.
   - **Sender:** open app → select Sender → verify network → discover receivers (or enter IP + PIN) → wait for receiver approval → select file → choose protocol and settings → send request → wait for approval → start → view visualization → see report.
3. Add the scope limits from §1.4 and the network assumption: campus Wi-Fi may block mDNS or isolate clients; a phone hotspot or direct cable is the documented fallback.
4. Move "custom packet loss and network delay configuration" out of Future Scope (basic loss + delay are MVP).
5. Remove "performance comparison" from the TRD testing list **or** add it to MVP. Currently the PRD calls it Future Scope. **[PROPOSED: keep it Future Scope; drop from TRD testing.]**
6. Add acceptance criteria (see §4).

### 2.2 trd.md
1. **FR2/FR3:** sender discovers receivers via Zeroconf and selects one. (Previously the receiver selected a sender.)
2. **FR5:** fallback is manual IP + PIN.
3. **New FRs:** receiver approval of connections; PIN expiry and attempt limiting; session token validation; receiver-disconnect detection (heartbeat); `frame_delay_ms` pacing; file size cap.
4. **Stack table:** delete the `qrcode` row. Add `python-multipart`, `zlib` (CRC32), and a local-IP helper (e.g. `ifaddr`). Specify `AsyncZeroconf` (not sync Zeroconf) and `asyncio.DatagramProtocol` (not blocking `socket.recvfrom`) so FastAPI's event loop is never blocked.
5. **Module breakdown:** add Session Manager, Device Discovery Manager, Retransmission Manager (or fold the last into Timer Manager and remove it from `netwrk.md`).
6. **Frame structure (§6):** align with `netwrk.md` (session ID, checksum) and add a version/magic byte. Full layout lives in `WIRE_PROTOCOL.md` (§3).
7. **Error handling:** add invalid/expired PIN, unauthorized peer, final-ACK loss, unsafe filename, insufficient disk space.
8. **Non-functional:** add Security (LAN exposure, session token, PIN lockout).
9. **Testing:** add deterministic seeded-loss pytest harness; the 30% loss preset against the retry limit; mDNS-blocked scenario falling back to IP + PIN; firewall-blocked UDP scenario.

### 2.3 system.md
1. **Diagram:** add Device Discovery Manager and Integrity Manager (present in text, missing from chart). Split sender and receiver engines. The receiver currently shows a Transmission Manager with outstanding-frame tracking, which only the sender has.
2. **§5.1:** add connection approval alongside PIN validation.
3. **Roles:** Zeroconf advertising starts only in Receiver mode.
4. **Constraints (§10) — add:**
   - `/api/*` localhost-only, `/peer/*` LAN-exposed (§1.3).
   - One active transfer per session.
   - UDP I/O must use asyncio (`DatagramProtocol`); no blocking socket calls on the event loop.
   - 5 MB file cap.
5. **Frontend serving:** state whether FastAPI serves the built React app (recommended: one command, no CORS) or Vite runs separately.
6. **§11 (docs to prepare):** add `WIRE_PROTOCOL.md`, `STATE_MACHINES.md`, and an agent instructions file (§3).

### 2.4 netwrk.md
1. **§2 Discovery:** define the Zeroconf service type and TXT records (device name, API port, API version, role). State that Zeroconf path requires receiver approval. Add PIN lockout.
2. **§3 Session:** the **sender generates `session_id`**. Define call order: `/peer/connect` (with PIN if fallback) → receiver approval → `/peer/session` (UDP ports exchanged) → session token returned.
3. **§4 Transfer request:** add the receiver-ready signal (receiver's UDP socket open) before the sender may start. Add SHA-256 of the original file to the request. In the flow diagram, **remove "SELECT ARQ" after "accept"** — protocol is chosen before the request.
4. **§5 Frames:** see §3 (wire protocol requirements). Additionally:
   - Stop-and-Wait uses 1-bit sequence (0/1) inside the 16-bit field; progress/events use absolute `frame_index`.
   - Define GBN ACK meaning (suggest: ACK number = highest in-order sequence received).
   - Add FIN / FIN-ACK handshake; receiver **lingers** (~2× timeout) after completion to re-ACK retransmitted frames.
5. **§5.5:** Selective Repeat requires sender window + receiver window ≤ half the sequence space (not only the receiver window).
6. **§5.7 Retries:** define `max_retries` as *retransmissions per frame* (attempts = retries + 1). The 30% loss preset with 5 retries fails almost every transfer (per-attempt success is 0.7 × 0.7 = 49% when both frames and ACKs are dropped; per-frame failure ≈ 1.8%, ≈ 97% chance of at least one failure over 200 frames). **[PROPOSED: preset retries = 15 for 30% loss; default 5 for 0% and 10%.]** Also: GBN uses one timer for the oldest unACKed frame; SR uses a timer per outstanding frame.
7. **§6 Loss simulation:** loss applies to both data frames and ACKs; use a **seeded RNG** (seed shared in the request) for reproducible demos. Simulated loss emits `FRAME_LOST` / `ACK_LOST`; natural loss is only ever visible as `TIMEOUT`. Each device displays only what it actually observed (e.g. a frame dropped before sending is never seen by the receiver).
8. **§7 Events:** sync with `api.md` (`FRAME_CORRUPTED`, `WINDOW_UPDATED`, integrity events, `CONNECTION_REQUEST`).
9. **§8 Verification:** state how the hash travels (in the transfer request) and how the result returns to the sender (`/peer/transfers/{id}/complete`). Add filename sanitization (strip path components, reject `..`, handle name collisions, check free disk space).
10. **§9 Errors:** add unauthorized peer, heartbeat-based disconnect detection, final ACK lost.
11. **§11 table typo:** "Backend to Frontend – HTTP REST" should read **Frontend → Backend**.

### 2.5 api.md
**Local (`/api`) additions**
- `POST /api/role` — set Sender or Receiver.
- `GET /api/network/status` — connectivity check and local IP (PRD requires "verify connectivity").
- `POST /api/devices/connect` — accept either `{device_id}` (discovered) or `{ip_address, pin}`; returns status `pending_approval` until the receiver decides.
- `GET /api/connections/pending`, `POST /api/connections/{id}/approve`, `POST /api/connections/{id}/reject` — receiver-side connection approval.
- `POST /api/files/select` — enforce the 5 MB cap, stream to a temp file (do not hold in memory), return `file_sha256`, clean up after transfer.
- Extend config with `frame_delay_ms` and `loss_seed`; define that **the `configuration` in the transfer request wins over `PUT /api/config`**; validate per protocol (window = 1 for Stop-and-Wait).
- Role enforcement: wrong-role calls return **403**.

**Peer (`/peer`) changes**
- `/peer/connect` — add `pin` (fallback path) and `api_version`; response returns `session_token`.
- All other peer endpoints require the session token.
- `/peer/transfers/request` — add `packet_loss_percentage`, `frame_delay_ms`, `loss_seed`, `file_sha256`, `chunk_size`, `total_frames` (receiver currently cannot simulate ACK loss).
- Add `/peer/transfers/{id}/ready` (receiver UDP socket open), `/peer/transfers/{id}/start`, `/peer/transfers/{id}/complete` (integrity result back to sender), `DELETE /peer/session`, and a heartbeat (`/peer/health` returning `api_version`, polled).
- Remove `/peer/transfers/pending` (no peer-side use).
- State which side hosts each endpoint. Accept/reject: the receiver backend **calls the sender's** `/peer/transfers/{id}/accept|reject`, so the sender must expose these callbacks.

**WebSocket changes**
- Add a global channel `ws://localhost:{port}/ws/events` for events without a transfer yet (`DEVICE_DISCOVERED`, `CONNECTION_REQUEST`, `SESSION_ESTABLISHED`, `TRANSFER_REQUEST`). Per-transfer channel remains for ARQ events.
- Envelope: `transfer_id` becomes nullable.
- Ordering: use a **per-device monotonic `event_seq`**; do not order by timestamp (the two laptops' clocks differ). Event IDs are unique per device (`{device_id}-{n}`).
- Replay: on reconnect the client sends `last_event_seq`; the backend replays buffered events after it (bounded ring buffer).
- Frame events include both `sequence_number` (wire value) and `frame_index` (absolute).
- Throttle/coalesce high-rate events if the buffer backs up (progress events at most ~10/s).

**Contracts**
- Define enums for session status and transfer status, and the allowed transitions.
- Add an error-code table beyond `INVALID_PIN` (e.g. `PIN_EXPIRED`, `PIN_LOCKED`, `CONNECTION_REJECTED`, `UNAUTHORIZED_PEER`, `FILE_TOO_LARGE`, `INVALID_CONFIG`, `TRANSFER_CONFLICT`, `PEER_UNAVAILABLE`, `INTEGRITY_FAILED`).

**Example fixes**
- 204,800 bytes at 1024 B per frame = **200 frames**, not 120.
- 204,800 bytes in 5.4 s ≈ **303 kbps**, not 182.5.
- Define `total_frames` as unique frames; add `total_transmissions` separately. Report fields differ by role (sender: frames sent/retransmitted; receiver: frames received/discarded/buffered).
- `bytes_sent` in progress events means **acknowledged bytes**.

---

## 3. New documents required

| Doc | Purpose |
|---|---|
| `WIRE_PROTOCOL.md` | Byte-exact frame layouts (big-endian, `struct` format strings). Required fields: magic, version, frame type (DATA, ACK, FIN, FIN_ACK), session ID (fixed-size, e.g. uint32), sequence number (16-bit), absolute frame index, payload length, CRC32, payload. ACK fields and GBN ACK semantics. |
| `STATE_MACHINES.md` | Session states, transfer states, and per-protocol sender/receiver state, with allowed transitions and timeouts. |
| `DATA_MODEL.md` | Already planned in `api.md` §9. |
| `IMPLEMENTATION_PLAN.md` | Phases below, with acceptance checks per phase. |
| `AGENTS.md` (or equivalent) | Repo layout, run/test commands, coding rules (async UDP, no TCP file transfer, no DB), definition of done. |
| Design system | Already planned; frontend work waits for it. |

### Recommended build order
1. Frame handler (encode/decode/CRC) + unit tests.
2. The three ARQ engines against an **in-memory lossy channel** with a seeded RNG (pytest, no sockets). Must pass 0%, 10%, 30% loss, ACK loss, duplicate and out-of-order cases.
3. Real UDP via `asyncio.DatagramProtocol`; two processes on one machine.
4. Peer + local REST API, session/PIN/approval flow, Zeroconf.
5. WebSocket event pipeline (global + per-transfer, replay).
6. Frontend (after the design system exists).
7. Two-laptop test, firewall and hotspot checks.

---

## 4. Acceptance criteria [PROPOSED]
- Two laptops pair via Zeroconf with receiver approval; when mDNS is blocked, IP + PIN works.
- 1 MB file transfers with all three protocols at 0%, 10% and 30% loss; **SHA-256 matches every time**.
- With a fixed seed, the same loss pattern reproduces the same retransmission count.
- Lost final ACK does not fail a completed transfer.
- Killing the receiver mid-transfer yields `TRANSFER_FAILED` on the sender within the retry/heartbeat limit.
- Closing and reopening the browser tab mid-transfer restores state via REST and replays events via WebSocket; the transfer is unaffected.
- A non-localhost client cannot call `/api/*`. A peer without a valid token cannot call `/peer/*` transfer endpoints.
- A malicious filename (`../../x`) is sanitized.

---

## 5. Open decisions for the project owner
1. Confirm the 5 MB cap and 100 ms default frame delay.
2. Confirm retry counts per loss preset (§2.4 item 6).
3. One port with middleware vs two ports (§1.3).
4. Keep "performance comparison" in Future Scope? (§2.1 item 5)
5. Target OS list and Python version.