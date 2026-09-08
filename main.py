from logger.logger import Logger

if __name__ == "__main__":
    print("Testing logger...")
    logger = Logger.get()
    logger.set_log_debug(True)
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.debug("This is a debug message")
    logger.close()
