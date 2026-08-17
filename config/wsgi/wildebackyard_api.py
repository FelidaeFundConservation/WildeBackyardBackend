# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
"""WSGI config for wildebackyard-api environment"""

import os
import sys
from pathlib import Path

# Add siteapps to Python path for app imports
# This is necessary because GCP deployment doesn't use manage.py
current_path = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(current_path / "siteapps"))

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.wildebackyard_api")

application = get_wsgi_application()
