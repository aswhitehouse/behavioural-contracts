"""Behavioral Contracts - A Python package for enforcing behavioral contracts in AI agents."""

from .contract import behavioral_contract
from .generator import generate_contract, format_contract

__version__ = "0.1.0"
__all__ = ["behavioral_contract", "generate_contract", "format_contract"] 