import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class HealthMonitor:
    def __init__(self, max_strikes: int = 3, strike_window_seconds: int = 3600):
        self.strikes: int = 0
        self.max_strikes: int = max_strikes
        self.strike_window_seconds: int = strike_window_seconds
        self.last_reset: datetime = datetime.now()
        self.status: str = "healthy"
        self.unusual_behavior_count: int = 0
        self.last_unusual_behavior: Optional[Dict[str, Any]] = None
        self.last_check: datetime = datetime.now()
        self.violations: List[Dict[str, Any]] = []
        logger.info(
            f"HealthMonitor initialized with max_strikes={self.max_strikes}, window={self.strike_window_seconds}s"
        )

    def add_strike(self, reason: Optional[str] = None) -> str:
        """Add a strike for unusual behavior that might warrant agent replacement."""
        if self.strikes > 0:
            window_expiry = self.last_reset + timedelta(
                seconds=self.strike_window_seconds
            )
            if datetime.now() > window_expiry:
                logger.info("Strike window expired, resetting strikes")
                self.strikes = 0
                self.last_reset = datetime.now()

        self.strikes += 1
        self.unusual_behavior_count += 1
        logger.info(f"Adding strike for reason: {reason}")
        self.last_unusual_behavior = {
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "strike_count": self.strikes,
        }

        if self.strikes >= self.max_strikes:
            self.status = "unhealthy"
            logger.warning(
                f"Agent marked as unhealthy after {self.strikes} strikes. Last unusual behavior: {reason}"
            )
        else:
            logger.warning(
                f"Strike recorded: {reason}. Total strikes: {self.strikes}, Status: {self.status}"
            )

        return self.status

    def reset(self) -> None:
        """Reset the health monitor after agent replacement or successful recovery."""
        self.strikes = 0
        self.unusual_behavior_count = 0
        self.status = "healthy"
        self.last_reset = datetime.now()
        self.last_unusual_behavior = None
        self.violations = []
        logger.info("Health monitor reset - agent is healthy")

    def get_health_status(self) -> Dict[str, Any]:
        """Get detailed health status information."""
        return {
            "status": self.status,
            "strikes": self.strikes,
            "max_strikes": self.max_strikes,
            "unusual_behavior_count": self.unusual_behavior_count,
            "last_unusual_behavior": self.last_unusual_behavior,
            "last_reset": self.last_reset.isoformat(),
            "last_check": self.last_check.isoformat(),
            "violations": self.violations,
        }

    def record_violation(self, violation: str) -> None:
        """Record a contract violation.

        Args:
            violation: Description of the violation
        """
        self.strikes += 1
        self.violations.append({"timestamp": datetime.now(), "description": violation})

        if self.strikes >= 3:
            self.status = "unhealthy"
