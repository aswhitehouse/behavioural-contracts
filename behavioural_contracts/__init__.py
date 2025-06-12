"""Behavioural Contracts - A Python package for enforcing behavioural contracts in AI agents."""

from .contract import behavioural_contract
from .exceptions import BehaviouralContractViolationError
from .generator import format_contract, generate_contract
from .models import BehaviouralContractSpec, BehaviouralFlags

__version__ = "0.1.2"
__all__ = [
    "behavioural_contract",
    "generate_contract",
    "format_contract",
    "BehaviouralContractSpec",
    "BehaviouralFlags",
    "BehaviouralContractViolationError",
]
