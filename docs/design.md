# Design notes

TermLoop is deliberately a *minimal system for a real habit* — no
infrastructure theater. These are the decisions that shaped it.

## One use case, two triggers

Reviews start from a manual command (`/go`) or from the scheduler. Both call
the same application service:

```
start_review(user_id, topic?, source)
```

where `source = manual | scheduled` exists only for logs. The scheduler
contains no card-selection logic of its own, walks users with notifications
enabled page by page, sends with bounded concurrency, and one user's failure
never stops the rest.

## Card selection

Top-10 cards by priority for the user (and optional topic), deterministic
tie-breaks — `last_reviewed_at ASC`, then card number — and a random pick
from that pool **in the application**. No `ORDER BY RANDOM()` over the table.

## Review state machine

```
IDLE → QUESTION_SHOWN → ANSWER_SHOWN → IDLE
```

The pending attempt lives in the `users` row (at most one per user) together
with a single-use random `review_token`. A callback is accepted only when the
Telegram user, card owner, pending card id, token, and state all match;
after grading, the pending state is cleared atomically. A replayed or stale
callback is a safe no-op, and abandoned attempts expire by TTL.

## Priority policy v1

| Consecutive "Remember" | Priority decrement |
|---:|---:|
| 1 | −1 |
| 2 | −10 |
| 3 | −25 |
| 4+ | −50 |

"Forgot" resets priority to 100 and the streak to 0. Priority is clamped to
0–100. The coefficients are intentionally naive: they only change based on
actual usage experience, and changing them never requires a schema change.

## Authorization

Telegram handles identification; the application handles authorization at
row level, inside the queries themselves:

```sql
UPDATE words SET ... WHERE number = :number AND user_id = :current_user_id;
```

Zero affected rows means "not found or not yours" — a foreign card is
indistinguishable from a missing one. Usernames never participate; callback
data is treated as untrusted input.

## Data model

Two tables. `users` holds the Telegram identity mapping, notification flag,
and the pending review. `words` holds the cards with per-user visible
numbers (`UNIQUE(user_id, number)`), priority/streak/counters, and a
composite selection index. That is sufficient while one card belongs to one
user and at most one review is pending per user.

## The stop rule

The spec ends with a stop rule: once a user can maintain a dictionary,
review manually and on schedule, and state survives restarts — development
stops. No AI answer grading, no web UI, no multi-tag system, no analytics,
no distributed infrastructure until real usage demonstrates a concrete need.
