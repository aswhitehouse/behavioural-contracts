"""Behavioural Contracts - A Python package for enforcing behavioural contracts in AI agents."""

from .contract import behavioural_contract
from .generator import generate_contract, format_contract
from .models import BehaviouralContractSpec, BehaviouralFlags
from .exceptions import BehaviouralContractViolation

__version__ = "0.1.0"
__all__ = [
    "behavioural_contract",
    "generate_contract",
    "format_contract",
    "BehaviouralContractSpec",
    "BehaviouralFlags",
    "BehaviouralContractViolation"
] 