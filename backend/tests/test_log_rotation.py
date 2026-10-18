
import logging
from logging.handlers import RotatingFileHandler


def test_rotating_file_handler(tmp_path):
    log_file = tmp_path / "test_mcp.log"

    logger = logging.getLogger(
        "resolveops.test.rotation"
    )

    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = RotatingFileHandler(
        log_file,
        maxBytes=200,
        backupCount=2,
        encoding="utf-8",
    )

    logger.addHandler(handler)

    try:
        for index in range(30):
            logger.info(
                "Test log entry %s: %s",
                index,
                "x" * 40,
            )

        assert log_file.exists()

        backup_1 = tmp_path / "test_mcp.log.1"
        assert backup_1.exists()

        assert log_file.stat().st_size <= 200

    finally:
        logger.removeHandler(handler)
        handler.close()
