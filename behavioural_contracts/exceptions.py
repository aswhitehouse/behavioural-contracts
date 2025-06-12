"""
Exceptions for the behavioural_contracts package.
"""


class BehaviouralContractViolationError(Exception):
    """Exception raised when a behavioural contract is violated."""

    pass


class ContractValidationError(Exception):
    """Exception raised when a contract fails validation."""

    pass


class ResponseValidationError(Exception):
    """Exception raised when a response fails validation."""

    pass
