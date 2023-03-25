This configuration sets up logging with the following features:

Log level set to `INFO`
Logs are written to both stdout and a log file
A new log file is created in the `logs` directory, which is automatically created if it doesn't exist
Log files have a maximum size of 10 MB and up to 5 backup files are kept
To use this configuration in your project, simply import it in your main application file (e.g., `main.py`) and any other modules where you want to use logging:

```
import logging
from log_config import logger

logger = logging.getLogger(__name__)

# Example usage
logger.info("This is an info message.")
logger.error("This is an error message.")
```

This will ensure that log messages from different modules are captured and formatted consistently, using the configuration defined in `log_config.py`.