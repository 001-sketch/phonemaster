"""Entry point for running PhoneMaster as a module: python -m phonemaster"""

import sys
from phonemaster.main import main

if __name__ == "__main__":
    sys.exit(main())
