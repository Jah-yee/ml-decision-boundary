"""Allow `python3 -m benchmarks` entrypoint."""
from benchmarks.run import main
import sys
sys.exit(main())