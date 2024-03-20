from django.core.management.base import BaseCommand
from supplies.models import SiteCategory


class Command(BaseCommand):
    help = 'Remove duplicate records from the database based on the "name" column'

    def handle(self, *args, **options):
        # Get all records ordered by id in ascending order
        all_records = SiteCategory.objects.order_by('id')

        # Initialize variables to keep track of unique names and ids to preserve
        unique_names = set()
        ids_to_preserve = set()

        for record in all_records:
            if record.name not in unique_names:
                # If the name is already encountered, add its id to the set to preserve
                ids_to_preserve.add(record.id)
                unique_names.add(record.name)

        SiteCategory.objects.exclude(id__in=ids_to_preserve).delete()

        self.stdout.write(self.style.SUCCESS('Duplicate records removed successfully.'))