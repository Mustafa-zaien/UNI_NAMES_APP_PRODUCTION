#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from pathlib import Path

# Add project paths
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / 'src'))

# Import main app
from main_app import main

if __name__ == "__main__":
    # Set application properties
    os.environ['PYTHONPATH'] = str(current_dir)
    
    # Run the app
    main()
