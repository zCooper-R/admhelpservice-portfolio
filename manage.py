import os
import sys

from settings_loader import resolve_settings_module


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", resolve_settings_module())
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
