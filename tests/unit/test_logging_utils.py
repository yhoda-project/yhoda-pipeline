"""Unit tests for yhovi_pipeline.utils.logging."""

from __future__ import annotations

import logging

from yhovi_pipeline.utils.logging import get_logger


class TestGetLogger:
    def test_returns_logger_instance(self, test_settings) -> None:
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)

    def test_logger_name_matches_argument(self, test_settings) -> None:
        logger = get_logger("my.custom.logger")
        assert logger.name == "my.custom.logger"

    def test_logger_level_set_from_settings(self, test_settings) -> None:
        logger = get_logger("test.level")
        assert logger.level == logging.DEBUG

    def test_different_names_return_different_loggers(self, test_settings) -> None:
        a = get_logger("logger.a")
        b = get_logger("logger.b")
        assert a.name != b.name

    def test_same_name_returns_same_logger(self, test_settings) -> None:
        a = get_logger("same.logger")
        b = get_logger("same.logger")
        assert a is b
