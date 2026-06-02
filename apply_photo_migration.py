import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_project.settings')
django.setup()

from django.core.management import call_command

call_command('migrate', 'hr', verbosity=2)

