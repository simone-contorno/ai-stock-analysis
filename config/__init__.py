# Initialization of the config package
# This file makes the config folder an importable Python package

from .config import get_config_value

__all__ = ['get_config_value']