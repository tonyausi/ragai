import logging.config
import yaml
from pathlib import Path


def load_logging_config(config_path: Path):
    """
    Load logging configuration from a YAML file.
    """
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


def setup_logging(config_path: Path):
    config = load_logging_config(config_path)
    logging.config.dictConfig(config)
