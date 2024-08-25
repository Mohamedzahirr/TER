# Generated by Django 5.0.6 on 2024-06-03 20:18

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_rename_end_time_serviceconstraints_friday_end_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmployeeRequirement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day_of_week', models.CharField(choices=[('Monday', 'Lundi'), ('Tuesday', 'Mardi'), ('Wednesday', 'Mercredi'), ('Thursday', 'Jeudi'), ('Friday', 'Vendredi'), ('Saturday', 'Samedi'), ('Sunday', 'Dimanche')], max_length=10)),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('employees_required', models.IntegerField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
