# WeChat UI Encryption Overlay Design

Date: 2026-05-07

## Summary

Build a Windows desktop companion tool for WeChat that encrypts outgoing chat text with a shared global key and displays decrypted text locally through a transparent overlay. The tool must not hook, inject into, patch, or read WeChat internals. It interacts with WeChat only through normal Windows UI mechanisms: UI Automation first, OCR fallback, clipboard/paste/send automation where necessary, and a topmost overlay window.

## Goals

- Provide a simple shared-key encrypted chat workflow for Windows desktop WeChat.
- Keep encrypted ciphertext as the only content actually sent through WeChat.
- Show decrypted plaintext locally in a non-invasive overlay above the WeChat message area.
- Use UI recognition/control instead of WeChat Hook, DLL injection, memory reading, database reading, or plugin behavior.
- Support an MVP with one global shared key for all chats.

## Non-Goals

- No WeChat Hook, DLL injection, memory modification, reverse engineering, or protocol-level integration.
- No reading WeChat local databases or message files.
- No attempt to bypass WeChat security controls.
- No guarantee that every WeChat version exposes readable UI Automation controls.
- No per-contact or per-group key management in the MVP.

## Recommended Architecture

The app is an independent Windows desktop program with four main modules:

1. **Window Discovery Module**
   - Finds the active WeChat window.
   - Tracks WeChat window position, size, focus state, and message area bounds.
   - Uses Windows APIs and UI Automation without entering the WeChat process.

2. **Message Recognition Module**
   - Reads visible chat content using UI Automation when controls expose text.
   - Falls back to screenshot + OCR when UI Automation cannot read message text.
   - Detects encrypted messages by a clear prefix such as `ENC[v1]:`.
   - Produces a list of visible encrypted message rectangles and ciphertext strings.

3. **Crypto Module**
   - Uses one global shared key for MVP.
   - Derives an encryption key from the user-provided passphrase with a modern KDF such as Argon2id or PBKDF2 with strong parameters.
   - Encrypts with an authenticated encryption mode such as AES-256-GCM or XChaCha20-Poly1305.
   - Encodes ciphertext as a transport-safe string: `ENC[v1]:<base64url-payload>`.
   - Rejects malformed, unauthenticated, or wrong-key messages without showing misleading plaintext.

4. **Overlay and Input Module**
   - Provides the user with the app's own plaintext input box.
   - Encrypts plaintext before it reaches WeChat.
   - Inserts ciphertext into WeChat using normal UI automation, paste, or send-key behavior.
   - Draws a transparent, click-through, topmost overlay aligned over encrypted WeChat message bubbles.
   - Displays decrypted plaintext only on the local screen; WeChat itself still contains ciphertext.

## User Flow

### Setup

1. User opens the companion tool.
2. User enters the global shared key/passphrase.
3. The tool stores the key material locally using Windows DPAPI or Windows Credential Manager, or optionally keeps it memory-only for higher security.
4. The tool detects the current WeChat desktop window.

### Sending an encrypted message

1. User types plaintext into the companion tool input box.
2. User clicks send or presses a configured hotkey.
3. The tool encrypts the plaintext and formats it as `ENC[v1]:...`.
4. The tool focuses the WeChat input box and inserts the ciphertext.
5. The tool sends the message using normal UI actions.
6. WeChat only sees and sends ciphertext.

### Reading encrypted messages

1. The tool monitors the visible WeChat chat area.
2. It identifies messages starting with `ENC[v1]:`.
3. It attempts decryption with the global shared key.
4. If decryption succeeds, it renders plaintext in the overlay at the matching message position.
5. If decryption fails, it shows nothing or a small local error indicator, without modifying WeChat.

## Data Format

Use a versioned envelope so the format can evolve later:

```text
ENC[v1]:<base64url(json-or-binary-envelope)>
```

The payload should include:

- version
- algorithm identifier
- KDF parameters or key-id metadata if needed
- nonce
- ciphertext
- authentication tag

The plaintext should not include hidden metadata unless needed. If message ordering or sender metadata is later required, it should be added in a versioned `v2` envelope.

## Security Model

This tool protects message content from casual reading inside WeChat history and on remote devices that do not have the shared key. It does not protect against endpoint compromise, screenshots, screen recording, clipboard monitoring, malware, or a malicious local user.

Important security choices:

- Plaintext input happens in the companion tool, not WeChat.
- WeChat receives only ciphertext.
- Decrypted plaintext is rendered locally in an overlay and should never be copied back into WeChat automatically.
- The app should minimize plaintext lifetime in memory where practical.
- Clipboard use should be minimized or cleaned after paste if clipboard insertion is used.
- The MVP uses one global key, which is simple but means all chats share the same compromise domain.

## UI Recognition Strategy

Primary strategy:

- Use Windows UI Automation to identify WeChat windows, input controls, chat panes, and text controls.
- Prefer stable accessibility properties when available.

Fallback strategy:

- Use screenshot capture of the WeChat message area.
- Run OCR only on relevant regions.
- Detect encrypted message strings and estimate their bounding rectangles.

The app should expose a small calibration/debug view for MVP so the user can confirm whether message recognition and overlay alignment are correct.

## Overlay Behavior

- The overlay is topmost and follows the WeChat window.
- It is transparent and click-through by default, so it does not block WeChat interaction.
- It redraws when the active chat changes, the WeChat window moves/resizes, or visible messages change.
- It should avoid covering non-encrypted messages.
- It should provide a quick toggle hotkey to hide/show decrypted text.

## Error Handling

- If WeChat is not found, show a clear status: “未检测到微信窗口”.
- If UI Automation cannot read messages, switch to OCR fallback and show that mode in status.
- If OCR confidence is low, do not decrypt guessed text silently; show a non-invasive warning.
- If decryption fails, treat the message as unreadable ciphertext rather than corrupting display.
- If overlay alignment fails, provide recalibration or temporarily disable overlay.

## Testing Plan

- Unit test encryption/decryption round trips, wrong-key failures, malformed payload rejection, and version parsing.
- Unit test message prefix detection and payload parsing.
- Integration test UI Automation adapters with mocked window/control trees.
- Integration test OCR parsing with saved screenshots containing sample encrypted messages.
- Manual QA on Windows desktop WeChat for window detection, input sending, overlay following, resizing, scrolling, and chat switching.

## MVP Scope

MVP includes:

- Windows desktop app.
- Global shared key.
- Tool-owned plaintext input box.
- Encrypt-to-WeChat send workflow.
- UI Automation message detection.
- OCR fallback for visible encrypted messages.
- Transparent overlay for decrypted visible ciphertext.
- Hotkey to toggle overlay.
- Local key storage using DPAPI/Credential Manager or memory-only mode.

MVP excludes:

- WeChat Hook or plugin support.
- Per-chat key management.
- Mobile support.
- Message search across history.
- Automatic decryption of messages not visible on screen.

## Open Implementation Decisions

- Desktop framework: .NET/WPF, WinUI 3, or Electron/Tauri with native Windows helpers.
- OCR engine: Windows OCR, PaddleOCR, or another local OCR library.
- Crypto library: platform-native crypto or a vetted cross-platform library.
- Whether the MVP stores the global key persistently or starts with memory-only key entry.

Recommended defaults for implementation planning:

- Use .NET/WPF or WinUI 3 if the project is Windows-only and UI Automation integration is central.
- Use AES-256-GCM with a strong KDF unless the selected stack has better first-class support for XChaCha20-Poly1305.
- Start with memory-only key entry plus optional DPAPI persistence, because it keeps MVP security behavior explicit.
