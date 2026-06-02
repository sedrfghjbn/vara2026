# Generated migration to update role choices (remove 'admin')

from django.db import migrations, models

def update_existing_admin_users(apps, schema_editor):
    """Обновляем всех пользователей с ролью admin на hr_manager"""
    User = apps.get_model('hr', 'User')
    User.objects.filter(role='admin').update(role='hr_manager')

def reverse_update(apps, schema_editor):
    """Обратная миграция"""
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(update_existing_admin_users, reverse_update),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[('hr_manager', 'HR-менеджер'), ('employee', 'Обычный сотрудник')],
                default='employee',
                max_length=20,
                verbose_name='Роль'
            ),
        ),
    ]

