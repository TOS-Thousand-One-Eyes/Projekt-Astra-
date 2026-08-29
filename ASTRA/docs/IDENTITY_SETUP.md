# Local identity setup

ASTRA uses an explicit local login instead of guessing identity from IP addresses,
webcams, or network metadata. The built-in profiles are `Erik` and `Petr`.

## First start

1. Start `run_astra_gui.bat`.
2. Enter `Erik` or `Petr` in the profile dialog.
3. On that profile's first login, create and confirm a 4-12 digit PIN.
4. Repeat once for the other profile when Petr first uses ASTRA.

Each PIN is stored as a salted PBKDF2-SHA256 hash in the per-user application
data directory, outside the source checkout. The original PIN is not stored.
PINs must be entered only in the login or Change PIN dialog, never as a chat
message.

## Separation

Each profile has a private directory under the update-safe user data root. On
Windows the default is `%LOCALAPPDATA%\ASTRA\users\<user_id>`; set
`ASTRA_DATA_DIR` to choose another location. Long memory,
facts, source-backed learning, self-learning candidates/guidance, structured
experience, reflections, tasks, system actions, and reminders are constructed from
that private directory. Optional file logs are private too. The active profile ID is also written into structured
experience records and the local-model prompt.

Existing Erik/Petr profile trees from the old source-relative `ASTRA/data`
location are copied to the durable root. Existing pre-profile data is copied
into Erik's profile only. Legacy originals are retained so migration is
recoverable and no existing destination file is overwritten.

## Version awareness

The same profile record stores `last_seen_version` and `last_seen_at`. After a
successful login on a newer build, ASTRA shows the profile a concise summary of
the available versioned changelogs and then records the current version. The PIN
hash is not modified. Reopening the same version does not repeat the update, and
running an older checkout does not roll the marker backward.

## Locking and switching

- Use **Lock / switch** to stop Brain and Eyes, clear the visible chat, and return
  to the login dialog.
- The GUI locks automatically after `identity_auto_lock_minutes` (15 by default).
- Set that configuration value to `0` only if automatic lock is intentionally
  disabled.
- Use **Change PIN** while logged in to replace the current profile's PIN.
- Use `who am i` or `identity status` to verify the active profile.

The PIN is intended to prevent accidental attribution and casual profile switching.
It does not encrypt runtime data against someone who already has operating-system
administrator or direct filesystem access.
