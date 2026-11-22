import sys
from pathlib import Path

# a src/ mappában lévő modulok importálhatók legyenek a tesztekből
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
