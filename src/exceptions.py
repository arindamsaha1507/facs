"""Module for custom exceptions."""

class InvalidLocation(ValueError):
    """Exception for invalid location"""

    def __init__(self, message):
        """Constructor for InvalidLocation"""
        self.message = message
        super().__init__(self.message)
