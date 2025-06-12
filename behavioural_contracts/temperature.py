import logging
from typing import List

logger = logging.getLogger(__name__)


class TemperatureController:
    def __init__(self, mode: str, range: List[float]):
        self.mode: str = mode
        self.min_temp: float
        self.max_temp: float
        self.min_temp, self.max_temp = range
        self.current_temp: float = self.min_temp
        self.consecutive_failures: int = 0
        self.consecutive_successes: int = 0
        logger.info(
            f"TemperatureController initialized with mode={mode}, range={range}"
        )

    def adjust(self, success: bool) -> float:
        if success:
            self.consecutive_successes += 1
            self.consecutive_failures = 0
            if self.mode == "adaptive":
                old_temp = self.current_temp
                self.current_temp = max(self.min_temp, self.current_temp - 0.05)
                logger.info(
                    f"Temperature decreased from {old_temp} to {self.current_temp} after success"
                )
        else:
            self.consecutive_failures += 1
            self.consecutive_successes = 0
            if self.mode == "adaptive":
                old_temp = self.current_temp
                self.current_temp = min(self.max_temp, self.current_temp + 0.2)
                logger.info(
                    f"Temperature increased from {old_temp} to {self.current_temp} after failure"
                )
        return self.current_temp

    def get_temperature(self) -> float:
        logger.debug(f"Current temperature: {self.current_temp}")
        return self.current_temp
