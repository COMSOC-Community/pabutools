import logging

def setup_logging(level=logging.INFO):
    """
    Set up global logging format and level for pabutools.
    Should be called once early by the main entry point.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
