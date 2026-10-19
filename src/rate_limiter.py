"""Thread-safe in-memory login rate limiter for brute-force prevention with dual-cap protection."""

import threading
import time
from typing import Dict, Tuple


class LoginRateLimiter:
    """Rate limiter tracking failed authentication attempts per account and IP."""

    def __init__(
        self,
        user_max_attempts: int = 5,
        ip_max_attempts: int = 20,
        lockout_duration_seconds: int = 600,
    ) -> None:
        self.user_max_attempts = user_max_attempts
        self.ip_max_attempts = ip_max_attempts
        self.lockout_duration_seconds = lockout_duration_seconds
        self._lock = threading.RLock()
        # key -> (failure_count, first_failure_timestamp, lockout_until_timestamp)
        self._attempts: Dict[str, Tuple[int, float, float]] = {}

    def is_blocked(self, key: str) -> Tuple[bool, int]:
        """Check if key is currently blocked.

        Returns (is_blocked, remaining_seconds_locked).
        """
        now = time.time()
        with self._lock:
            record = self._attempts.get(key)
            if not record:
                return (False, 0)

            count, first_attempt, lockout_until = record
            if lockout_until > now:
                remaining = int(lockout_until - now) + 1
                return (True, remaining)

            if lockout_until > 0 and lockout_until <= now:
                del self._attempts[key]
                return (False, 0)

            if now - first_attempt > self.lockout_duration_seconds:
                del self._attempts[key]
                return (False, 0)

            return (False, 0)

    def record_failure(
        self,
        key: str,
        max_attempts: int | None = None,
    ) -> Tuple[bool, int]:
        """Record a failed login attempt for key.

        Returns (is_now_blocked, remaining_seconds).
        """
        threshold = max_attempts if max_attempts is not None else self.user_max_attempts
        now = time.time()
        with self._lock:
            record = self._attempts.get(key)
            if not record or (now - record[1] > self.lockout_duration_seconds and record[2] <= now):
                count = 1
                first_attempt = now
                lockout_until = 0.0
            else:
                count = record[0] + 1
                first_attempt = record[1]
                lockout_until = record[2]

            if count >= threshold:
                lockout_until = now + self.lockout_duration_seconds

            self._attempts[key] = (count, first_attempt, lockout_until)
            blocked = lockout_until > now
            remaining = int(lockout_until - now) + 1 if blocked else 0
            return (blocked, remaining)

    def check_login_attempt(self, ip: str, username: str) -> Tuple[bool, int, str]:
        """Check if either the IP or (IP + username) is blocked.

        Returns (is_blocked, remaining_seconds, reason_scope ['ip'|'user'|'']).
        """
        clean_ip = ip.strip() if ip else "127.0.0.1"
        clean_user = username.strip().lower() if username else ""

        ip_key = f"ip:{clean_ip}"
        user_key = f"user:{clean_ip}:{clean_user}"

        # 1. Check IP-wide cap first
        ip_blocked, ip_rem = self.is_blocked(ip_key)
        if ip_blocked:
            return (True, ip_rem, "ip")

        # 2. Check user+IP pair
        user_blocked, user_rem = self.is_blocked(user_key)
        if user_blocked:
            return (True, user_rem, "user")

        return (False, 0, "")

    def register_login_failure(self, ip: str, username: str) -> Tuple[bool, int, str]:
        """Record failure for both IP and (IP + username).

        Returns (is_blocked, remaining_seconds, reason_scope).
        """
        clean_ip = ip.strip() if ip else "127.0.0.1"
        clean_user = username.strip().lower() if username else ""

        ip_key = f"ip:{clean_ip}"
        user_key = f"user:{clean_ip}:{clean_user}"

        ip_blocked, ip_rem = self.record_failure(ip_key, max_attempts=self.ip_max_attempts)
        user_blocked, user_rem = self.record_failure(user_key, max_attempts=self.user_max_attempts)

        if ip_blocked:
            return (True, ip_rem, "ip")
        if user_blocked:
            return (True, user_rem, "user")

        return (False, 0, "")

    def register_login_success(self, ip: str, username: str) -> None:
        """Clear failed user attempts upon successful authentication."""
        clean_ip = ip.strip() if ip else "127.0.0.1"
        clean_user = username.strip().lower() if username else ""
        user_key = f"user:{clean_ip}:{clean_user}"
        with self._lock:
            self._attempts.pop(user_key, None)

    def clear(self) -> None:
        """Reset all rate limiter state (used in testing)."""
        with self._lock:
            self._attempts.clear()


# Global instance with 5 attempts per (user+IP) and 20 attempts per IP
login_limiter = LoginRateLimiter(
    user_max_attempts=5,
    ip_max_attempts=20,
    lockout_duration_seconds=600,
)
