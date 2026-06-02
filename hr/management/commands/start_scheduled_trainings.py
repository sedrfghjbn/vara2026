from django.core.management.base import BaseCommand
from django.utils import timezone
from hr.models import Training
import logging

logger = logging.getLogger('hr.management.commands')


class Command(BaseCommand):
    help = 'Start trainings scheduled for today (set status to in_progress and send notifications)'

    def add_arguments(self, parser):
        parser.add_argument('--date', help='ISO date to consider as today (YYYY-MM-DD)', required=False)
        parser.add_argument('--force', action='store_true', help='Start trainings whose start_date <= today')

    def handle(self, *args, **options):
        today = options.get('date')
        if today:
            from django.utils.dateparse import parse_date
            today = parse_date(today)
            if not today:
                self.stderr.write('Invalid date')
                return
        else:
            today = timezone.localtime(timezone.now()).date()

        qs = Training.objects.filter(status='planned')
        if options.get('force'):
            qs = qs.filter(start_date__lte=today)
        else:
            qs = qs.filter(start_date=today)

        count = qs.count()
        self.stdout.write(f'Found {count} training(s) to start for {today}')
        for training in qs:
            # mark as started
            training.status = 'in_progress'
            # if start_date is in the future but --force used, keep start_date
            # otherwise ensure start_date is at least today
            if training.start_date != today:
                training.start_date = today
            training.save()
            self.stdout.write(f'Started training: {training.title} (id={training.pk})')
            logger.info('Started training %s (%s)', training.pk, training.title)
