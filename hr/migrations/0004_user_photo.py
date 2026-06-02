from django.db import migrations, models
import hr.models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0003_user_extra_fields_employee_note'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='photo',
            field=models.ImageField(blank=True, null=True, upload_to=hr.models.user_photo_path, verbose_name='Фото'),
        ),
    ]

