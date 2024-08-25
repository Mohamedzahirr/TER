from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0022_alter_customuser_role'),  # Remplacez XXXX par le numéro de la migration précédente
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(choices=[('schedule', 'Changement de planning'), ('leave_request', 'Demande de congé')], default='schedule', max_length=20),
        ),
    ]